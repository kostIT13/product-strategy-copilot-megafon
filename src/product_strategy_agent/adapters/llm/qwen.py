"""Single-attempt Qwen-compatible JSON chat completion over HTTP."""
import json
import time
from urllib.parse import urlsplit

from product_strategy_agent.config import Settings
from product_strategy_agent.domain.agent.models import ModelReply, ProviderError


class QwenChatProvider:
    def __init__(self, settings: Settings, transport=None):
        self.settings, self.transport = settings, transport
        self.model = settings.qwen_model

    def generate(self, messages: list[dict[str, str]]) -> ModelReply:
        try:
            import httpx
        except ImportError:
            raise ProviderError('install agent support: pip install -e ".[agent]"') from None
        settings = self.settings
        base = settings.qwen_base_url.rstrip("/")
        try:
            parts = urlsplit(base)
            _ = parts.port
            if any(ord(char) < 33 for char in base):
                raise ValueError()
            local = parts.hostname in {"localhost", "127.0.0.1", "::1", "host.docker.internal"}
            if (parts.scheme != "https" and not (parts.scheme == "http" and local)) or not parts.hostname:
                raise ValueError()
            if parts.username is not None or parts.password is not None or parts.query or parts.fragment:
                raise ValueError()
        except ValueError:
            raise ProviderError("invalid model endpoint; use HTTPS or an explicit local HTTP endpoint without URL credentials/query") from None
        key = settings.qwen_api_key.get_secret_value()
        if not key and not local:
            raise ProviderError("QWEN_API_KEY is not configured")
        payload = {"model": self.model, "messages": messages, "stream": False,
                   "max_tokens": settings.qwen_max_output_tokens,
                   "response_format": {"type": "json_object"}}
        if settings.qwen_enable_thinking is not None:
            payload["enable_thinking"] = settings.qwen_enable_thinking
        headers = {"Authorization": f"Bearer {key}"} if key else {}
        started = time.monotonic()
        try:
            with httpx.Client(transport=self.transport, timeout=settings.qwen_timeout_seconds,
                              follow_redirects=False, trust_env=False) as client:
                with client.stream("POST", base + "/chat/completions", json=payload, headers=headers) as response:
                    if response.status_code != 200:
                        raise ProviderError(f"model endpoint returned HTTP {response.status_code}")
                    chunks, size = [], 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > 2 * 1024 * 1024:
                            raise ProviderError("model response exceeded the byte limit")
                        chunks.append(chunk)
                    envelope = json.loads(b"".join(chunks))
            choice = envelope["choices"][0]
            if not isinstance(choice, dict):
                raise ProviderError("model response choice is invalid")
            if choice.get("finish_reason") != "stop":
                raise ProviderError("model completion was truncated or did not finish normally")
            content = choice["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ProviderError("model returned no text content")
            raw_usage = envelope.get("usage") or {}
            if not isinstance(raw_usage, dict):
                raw_usage = {}
            def tokens(name):
                value = raw_usage.get(name)
                return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None
            return ModelReply(content, {
                "input_tokens": tokens("prompt_tokens"), "output_tokens": tokens("completion_tokens"),
                "total_tokens": tokens("total_tokens"), "cost": None,
                "duration_ms": int((time.monotonic() - started) * 1000),
                "reported_model": envelope.get("model") if isinstance(envelope.get("model"), str) else None,
            })
        except ProviderError:
            raise
        except (httpx.HTTPError, httpx.InvalidURL, ValueError, KeyError, IndexError, TypeError):
            # Never expose response bodies, headers, endpoint secrets or raw prompts.
            raise ProviderError("model transport or response envelope is invalid") from None
