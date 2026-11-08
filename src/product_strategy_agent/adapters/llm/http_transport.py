"""Bound response bytes before SDK parsing; preserve raw optional usage fields."""
import json
import ssl
import httpx

from product_strategy_agent.domain.agent.models import ProviderError
from product_strategy_agent.adapters.llm.response_envelope import sdk_response_body


class BoundedTransport(httpx.BaseTransport):
    def __init__(self, inner: httpx.BaseTransport):
        self.inner = inner
        self.envelope = None
        self.failure = None

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        response = None
        try:
            response = self.inner.handle_request(request)
            if response.status_code != 200:
                raise ProviderError("model endpoint rejected the request", code=f"provider_http_{response.status_code}")
            chunks, size = [], 0
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > 2 * 1024 * 1024:
                    raise ProviderError("model response exceeded the byte limit", code="provider_response_too_large")
                chunks.append(chunk)
            body = b"".join(chunks)
            if response.status_code == 200:
                try:
                    self.envelope = json.loads(body)
                except (ValueError, UnicodeError):
                    raise ProviderError("model returned invalid JSON", code="provider_invalid_json") from None
                choices = self.envelope.get("choices") if isinstance(self.envelope, dict) else None
                if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
                    raise ProviderError("model response choices are invalid", code="provider_invalid_envelope")
                choice = choices[0]
                message = choice.get("message")
                if choice.get("finish_reason") != "stop":
                    raise ProviderError("model completion did not finish normally", code="provider_incomplete_completion")
                if not isinstance(message, dict) or not isinstance(message.get("content"), str):
                    raise ProviderError("model message is invalid", code="provider_invalid_envelope")
                if not message["content"].strip():
                    raise ProviderError("model response content is empty", code="provider_empty_content")
                # Provider metadata can have incompatible SDK types and warnings
                # can echo their values. Keep the raw envelope only in memory;
                # give the SDK just the supported text/usage contract.
                body = sdk_response_body(self.envelope)
            headers = dict(response.headers)
            headers.pop("content-encoding", None)
            headers.pop("content-length", None)
            return httpx.Response(response.status_code, headers=headers,
                                  content=body, request=request)
        except ProviderError as exc:
            self.failure = exc
            raise
        except httpx.TimeoutException:
            self.failure = ProviderError(code="provider_timeout")
            raise self.failure from None
        except (httpx.HTTPError, OSError) as exc:
            chain, seen = exc, set()
            tls = False
            while chain is not None and id(chain) not in seen:
                seen.add(id(chain))
                tls = tls or isinstance(chain, ssl.SSLError)
                chain = chain.__cause__ or chain.__context__
            self.failure = ProviderError(code="provider_tls_error" if tls else "provider_connection_error")
            raise self.failure from None
        finally:
            if response is not None:
                response.close()

    def close(self):
        self.inner.close()
