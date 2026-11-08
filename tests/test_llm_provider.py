"""HTTP contract checks without sending data to an external model."""
import json
import unittest
import gzip
import os
import ssl
import warnings
from unittest.mock import patch
import httpx
from pydantic import SecretStr

from product_strategy_agent.adapters.llm.openai_compatible import OpenAICompatibleProvider
from product_strategy_agent.config import Settings
from product_strategy_agent.domain.agent.models import ProviderError


def settings(**overrides):
    values = dict(llm_base_url="https://provider.example/v1", llm_model="fixture-model",
                  llm_api_key=SecretStr("synthetic-key"), llm_max_output_tokens=2048,
                  llm_timeout_seconds=60, llm_extra_body={})
    values.update(overrides)
    return Settings(_env_file=None, **values)


def envelope(**overrides):
    result = {"model": "reported-model", "choices": [{"finish_reason": "stop", "message": {"content": '{"draft":true}'}}]}
    result.update(overrides)
    return result


MESSAGES = [{"role": "system", "content": "Return JSON"}]


class OpenAICompatibleProviderTests(unittest.TestCase):
    def test_request_contract_and_unknown_usage(self):
        requests = []
        def handle(request):
            requests.append(request)
            return httpx.Response(200, json=envelope())
        result = OpenAICompatibleProvider(settings(llm_extra_body={"enable_thinking": False}), httpx.MockTransport(handle)).generate(MESSAGES)
        self.assertEqual(len(requests), 1)
        request = requests[0]
        self.assertEqual(str(request.url), "https://provider.example/v1/chat/completions")
        self.assertEqual(request.headers["authorization"], "Bearer synthetic-key")
        body = json.loads(request.content)
        self.assertEqual(body["response_format"], {"type": "json_object"})
        self.assertFalse(body["enable_thinking"])
        self.assertEqual(body["max_tokens"], 2048)
        self.assertIsNone(result.usage["input_tokens"])
        self.assertIsNone(result.usage["cost"])

    def test_measured_token_usage_is_retained(self):
        transport = httpx.MockTransport(lambda _: httpx.Response(200, json=envelope(
            usage={"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120})))
        result = OpenAICompatibleProvider(settings(), transport).generate(MESSAGES)
        self.assertEqual(result.usage["total_tokens"], 120)
        self.assertEqual(result.usage["reported_model"], "reported-model")

    def test_endpoint_errors_do_not_retry_or_reveal_body(self):
        for status in (302, 401, 429, 500):
            calls = []
            def handle(request):
                calls.append(request)
                return httpx.Response(status, text="synthetic-key secret response", headers={"Location": "https://other.example/"})
            with self.subTest(status=status), self.assertRaises(ProviderError) as error:
                OpenAICompatibleProvider(settings(), httpx.MockTransport(handle)).generate(MESSAGES)
            self.assertNotIn("synthetic-key", str(error.exception))
            self.assertEqual(error.exception.code, f"provider_http_{status}")
            self.assertEqual(len(calls), 1)

    def test_invalid_envelope_and_truncation_fail(self):
        for content, code in (({}, "provider_invalid_envelope"),
                (envelope(choices=[None]), "provider_invalid_envelope"),
                (envelope(choices=["invalid"]), "provider_invalid_envelope"),
                (envelope(choices=[{"finish_reason": "length", "message": {"content": "partial"}}]), "provider_output_limit"),
                (envelope(choices=[{"finish_reason": "content_filter", "message": {"content": "partial"}}]), "provider_content_filtered"),
                (envelope(choices=[{"finish_reason": None, "message": {"content": "partial"}}]), "provider_incomplete_completion"),
                (envelope(choices=[{"finish_reason": [], "message": {"content": "partial"}}]), "provider_invalid_envelope"),
                (envelope(choices=[{"finish_reason": "stop", "message": {"content": None}}]), "provider_invalid_envelope"),
                (envelope(choices=[{"finish_reason": "stop", "message": {"content": " "}}]), "provider_empty_content")):
            with self.subTest(content=content), self.assertRaises(ProviderError) as error:
                OpenAICompatibleProvider(settings(), httpx.MockTransport(lambda _: httpx.Response(200, json=content))).generate(MESSAGES)
            self.assertEqual(error.exception.code, code)
        with self.assertRaises(ProviderError) as error:
            OpenAICompatibleProvider(settings(), httpx.MockTransport(lambda _: httpx.Response(200, content=b"not JSON synthetic-key"))).generate(MESSAGES)
        self.assertEqual(error.exception.code, "provider_invalid_json")

    def test_oversized_response_is_refused(self):
        with self.assertRaises(ProviderError) as error:
            OpenAICompatibleProvider(settings(), httpx.MockTransport(lambda _: httpx.Response(200, content=b"x" * (2 * 1024 * 1024 + 1)))).generate(MESSAGES)
        self.assertEqual(error.exception.code, "provider_response_too_large")

    def test_missing_key_and_invalid_endpoints_fail_before_network(self):
        for config in (settings(llm_api_key=SecretStr("")), settings(llm_base_url="http://remote.example/v1"),
                       settings(llm_base_url="https://user:secret@provider.example/v1"),
                       settings(llm_base_url="https://provider.example:bad/v1")):
            calls = []
            with self.subTest(), self.assertRaises(ProviderError):
                OpenAICompatibleProvider(config, httpx.MockTransport(lambda request: calls.append(request))).generate(MESSAGES)
            self.assertFalse(calls)

    def test_local_endpoint_can_run_without_a_key(self):
        def handle(request):
            self.assertEqual(request.headers["authorization"], "Bearer local-no-key")
            return httpx.Response(200, json=envelope())
        OpenAICompatibleProvider(settings(llm_base_url="http://127.0.0.1:8000/v1", llm_api_key=SecretStr("")),
                         httpx.MockTransport(handle)).generate(MESSAGES)

    def test_model_id_and_extra_body_are_provider_independent(self):
        def handle(request):
            body = json.loads(request.content)
            self.assertEqual(body["model"], "Qwen/Qwen3-32B")
            self.assertEqual(body["chat_template_kwargs"], {"enable_thinking": False})
            self.assertNotIn("enable_thinking", body)
            return httpx.Response(200, json=envelope())
        OpenAICompatibleProvider(settings(llm_model="Qwen/Qwen3-32B",
            llm_extra_body={"chat_template_kwargs": {"enable_thinking": False}}),
            httpx.MockTransport(handle)).generate(MESSAGES)

    def test_extra_body_cannot_override_contract(self):
        for name in ("model", "messages", "stream", "max_tokens", "max_completion_tokens", "response_format"):
            calls = []
            with self.subTest(name=name), self.assertRaises(ProviderError):
                OpenAICompatibleProvider(settings(llm_extra_body={name: "override"}),
                    httpx.MockTransport(lambda request: calls.append(request))).generate(MESSAGES)
            self.assertFalse(calls)

    def test_transport_timeout_is_sanitized_without_retry(self):
        calls = []
        def handle(request):
            calls.append(request)
            raise httpx.ReadTimeout("synthetic-key secret body", request=request)
        with self.assertRaises(ProviderError) as error:
            OpenAICompatibleProvider(settings(), httpx.MockTransport(handle)).generate(MESSAGES)
        self.assertNotIn("synthetic-key", str(error.exception))
        self.assertEqual(error.exception.code, "provider_timeout")
        self.assertEqual(len(calls), 1)

    def test_compressed_response_is_decoded_once(self):
        body = gzip.compress(json.dumps(envelope()).encode())
        result = OpenAICompatibleProvider(settings(), httpx.MockTransport(lambda request:
            httpx.Response(200, content=body, headers={"Content-Encoding": "gzip"}))).generate(MESSAGES)
        self.assertEqual(result.content, '{"draft":true}')

    def test_legacy_environment_aliases(self):
        with patch.dict(os.environ, {"QWEN_MODEL": "legacy", "QWEN_BASE_URL": "https://old.example/v1",
                                     "QWEN_API_KEY": "legacy-key"}, clear=True):
            config = Settings(_env_file=None)
            self.assertEqual(config.llm_model, "legacy")
            self.assertEqual(config.llm_base_url, "https://old.example/v1")
            self.assertEqual(config.llm_api_key.get_secret_value(), "legacy-key")

    def test_generic_environment_takes_precedence_and_parses_extra_body(self):
        with patch.dict(os.environ, {"LLM_MODEL": "new", "QWEN_MODEL": "old",
                "LLM_EXTRA_BODY": '{"chat_template_kwargs":{"enable_thinking":false}}'}, clear=True):
            config = Settings(_env_file=None)
            self.assertEqual(config.llm_model, "new")
            self.assertEqual(config.llm_extra_body, {"chat_template_kwargs": {"enable_thinking": False}})

    def test_connection_and_tls_failure_codes(self):
        for tls in (False, True):
            calls = []
            def handle(request):
                calls.append(request)
                if tls:
                    try:
                        raise ssl.SSLCertVerificationError("synthetic-key certificate details")
                    except ssl.SSLCertVerificationError as cause:
                        raise httpx.ConnectError("synthetic-key host details") from cause
                raise httpx.ConnectError("synthetic-key host details")
            with self.subTest(tls=tls), self.assertRaises(ProviderError) as error:
                OpenAICompatibleProvider(settings(), httpx.MockTransport(handle)).generate(MESSAGES)
            self.assertEqual(error.exception.code, "provider_tls_error" if tls else "provider_connection_error")
            self.assertNotIn("synthetic-key", str(error.exception))
            self.assertEqual(len(calls), 1)

    def test_diagnostic_code_cannot_contain_upstream_data(self):
        for code in ("synthetic-key", "provider_http_999", "provider_http_401 secret"):
            with self.subTest(code=code), self.assertRaises(ValueError):
                ProviderError(code=code)

    def test_sdk_error_before_transport_is_sanitized(self):
        with patch.dict(os.environ, {"LITELLM_LOCAL_MODEL_COST_MAP": "True"}):
            import litellm
        calls = []
        with patch.object(litellm, "completion", side_effect=RuntimeError("synthetic-key upstream details")):
            with self.assertRaises(ProviderError) as error:
                OpenAICompatibleProvider(settings(), httpx.MockTransport(lambda request: calls.append(request))).generate(MESSAGES)
        self.assertEqual(error.exception.code, "provider_sdk_error")
        self.assertNotIn("synthetic-key", str(error.exception))
        self.assertFalse(calls)

    def test_provider_metadata_extensions_cannot_escape_in_sdk_warnings(self):
        response = envelope(metadata=[{"secret": "synthetic-key"}], usage={
            "prompt_tokens": 11, "completion_tokens": 3, "total_tokens": 14,
            "metadata": [{"secret": "synthetic-key"}]})
        response["choices"][0]["message"]["metadata"] = [{"secret": "synthetic-key"}]
        with warnings.catch_warnings(record=True) as emitted:
            warnings.simplefilter("always")
            reply = OpenAICompatibleProvider(settings(), httpx.MockTransport(lambda _:
                httpx.Response(200, json=response))).generate(MESSAGES)
        self.assertEqual(reply.content, '{"draft":true}')
        self.assertEqual(reply.usage["total_tokens"], 14)
        self.assertNotIn("synthetic-key", str([str(item.message) for item in emitted]))

    def test_checkpoint_fingerprint_tracks_request_settings_and_allows_key_rotation(self):
        original = OpenAICompatibleProvider(settings()).configuration_hash
        rotated = OpenAICompatibleProvider(settings(llm_api_key=SecretStr("rotated-key"), llm_timeout_seconds=5))
        self.assertEqual(original, rotated.configuration_hash)
        for changes in ({"llm_model": "other"}, {"llm_base_url": "https://other.example/v1"},
                        {"llm_max_output_tokens": 1000}, {"llm_extra_body": {"enable_thinking": False}}):
            with self.subTest(changes=changes):
                self.assertNotEqual(original, OpenAICompatibleProvider(settings(**changes)).configuration_hash)

    def test_truncated_response_keeps_counters_without_reasoning_text(self):
        body = envelope(choices=[{"finish_reason": "length", "message": {"content": "", "reasoning_content": "synthetic-secret"}}],
                        usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30,
                               "completion_tokens_details": {"reasoning_tokens": 20}, "debug": "synthetic-secret"})
        with self.assertRaises(ProviderError) as error:
            OpenAICompatibleProvider(settings(), httpx.MockTransport(lambda _: httpx.Response(200, json=body))).generate(MESSAGES)
        self.assertEqual(error.exception.code, "provider_output_limit")
        self.assertEqual(error.exception.usage["reasoning_tokens"], 20)
        self.assertEqual(error.exception.usage["content_chars"], 0)
        self.assertEqual(error.exception.usage["output_token_limit"], 2048)
        self.assertIsNone(error.exception.usage["cost"])
        self.assertNotIn("synthetic-secret", json.dumps(error.exception.usage))
