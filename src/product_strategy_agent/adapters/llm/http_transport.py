"""Bound response bytes before SDK parsing; preserve raw optional usage fields."""
import json
import httpx

from product_strategy_agent.domain.agent.models import ProviderError


class BoundedTransport(httpx.BaseTransport):
    def __init__(self, inner: httpx.BaseTransport):
        self.inner = inner
        self.envelope = None

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        response = self.inner.handle_request(request)
        try:
            chunks, size = [], 0
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > 2 * 1024 * 1024:
                    raise ProviderError("model response exceeded the byte limit")
                chunks.append(chunk)
            body = b"".join(chunks)
            if response.status_code == 200:
                self.envelope = json.loads(body)
                choices = self.envelope.get("choices") if isinstance(self.envelope, dict) else None
                if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
                    raise ProviderError("model response choices are invalid")
                choice = choices[0]
                message = choice.get("message")
                if (choice.get("finish_reason") != "stop" or not isinstance(message, dict)
                        or not isinstance(message.get("content"), str) or not message["content"].strip()):
                    raise ProviderError("model response content is invalid or incomplete")
            headers = dict(response.headers)
            headers.pop("content-encoding", None)
            headers.pop("content-length", None)
            return httpx.Response(response.status_code, headers=headers,
                                  content=body, request=request)
        finally:
            response.close()

    def close(self):
        self.inner.close()
