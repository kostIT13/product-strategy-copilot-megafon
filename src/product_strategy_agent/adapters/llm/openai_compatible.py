"""Single-attempt OpenAI-compatible JSON chat completion over HTTP."""
import time
import json
import hashlib
import os
import logging
from urllib.parse import urlsplit

from product_strategy_agent.config import Settings
from product_strategy_agent.domain.agent.models import ModelReply, ProviderError


class OpenAICompatibleProvider:
    def __init__(self, settings: Settings, transport=None):
        self.settings, self.transport = settings, transport
        self.model = settings.llm_model
        self.configuration_hash = hashlib.sha256(json.dumps({
            "base_url": settings.llm_base_url.rstrip("/"), "model": self.model,
            "max_tokens": settings.llm_max_output_tokens, "extra_body": settings.llm_extra_body,
        }, sort_keys=True).encode("utf-8")).hexdigest()

    def generate(self, messages: list[dict[str, str]]) -> ModelReply:
        try:
            # Avoid remote pricing-map downloads when importing LiteLLM.
            os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
            import httpx
            import litellm
            from openai import OpenAI
            from .http_transport import BoundedTransport
        except ImportError:
            raise ProviderError('install agent support: pip install -e ".[agent]"', code="provider_dependency_missing") from None
        settings = self.settings
        base = settings.llm_base_url.rstrip("/")
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
            raise ProviderError("invalid model endpoint; use HTTPS or an explicit local HTTP endpoint without URL credentials/query",
                                code="provider_invalid_endpoint") from None
        key = settings.llm_api_key.get_secret_value()
        if not key and not local:
            raise ProviderError("LLM_API_KEY is not configured", code="provider_missing_key")
        reserved = {"model", "messages", "stream", "max_tokens", "max_completion_tokens", "response_format"}
        if reserved.intersection(settings.llm_extra_body):
            raise ProviderError("LLM_EXTRA_BODY cannot override the agent request contract", code="provider_invalid_extra_body")
        litellm.suppress_debug_info = True
        litellm.turn_off_message_logging = True
        logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)
        started = time.monotonic()
        transport = None
        try:
            transport = BoundedTransport(self.transport or httpx.HTTPTransport(retries=0, trust_env=False))
            with httpx.Client(transport=transport, timeout=settings.llm_timeout_seconds,
                              follow_redirects=False, trust_env=False) as http_client:
                # A local unauthenticated server still needs a nonempty SDK key.
                with OpenAI(api_key=key or "local-no-key", base_url=base,
                            http_client=http_client, max_retries=0) as client:
                    response = litellm.completion(
                        model="openai/" + self.model, custom_llm_provider="openai",
                        api_base=base, api_key=key or "local-no-key", client=client,
                        messages=messages, stream=False,
                        max_tokens=settings.llm_max_output_tokens,
                        response_format={"type": "json_object"},
                        extra_body=settings.llm_extra_body,
                        timeout=settings.llm_timeout_seconds, num_retries=0, max_retries=0,
                        caching=False, **{"no-log": True},
                    )
            # Keep raw absence of usage and finish_reason: SDK normalization can
            # synthesize zero token counts or defaults for incomplete envelopes.
            envelope = transport.envelope
            choice = envelope["choices"][0]
            if not isinstance(choice, dict):
                raise ProviderError("model response choice is invalid", code="provider_invalid_envelope")
            if choice.get("finish_reason") != "stop":
                raise ProviderError("model completion was truncated or did not finish normally", code="provider_incomplete_completion")
            content = choice["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ProviderError("model returned no text content", code="provider_empty_content")
            raw_usage = envelope.get("usage") or {}
            if not isinstance(raw_usage, dict):
                raw_usage = {}
            def tokens(name):
                value = raw_usage.get(name)
                return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None
            if response.choices[0].message.content != content:
                raise ProviderError("model response normalization changed content", code="provider_invalid_envelope")
            return ModelReply(content, {
                "input_tokens": tokens("prompt_tokens"), "output_tokens": tokens("completion_tokens"),
                "total_tokens": tokens("total_tokens"), "cost": None,
                "duration_ms": int((time.monotonic() - started) * 1000),
                "reported_model": envelope.get("model") if isinstance(envelope.get("model"), str) else None,
            })
        except ProviderError:
            raise
        except Exception:
            # Never expose response bodies, headers, endpoint secrets or raw prompts.
            if transport is not None and transport.failure is not None:
                raise transport.failure from None
            raise ProviderError("model SDK or response normalization failed", code="provider_sdk_error") from None
