"""HTTP contract checks without sending data to an external model."""
import json
import unittest
import gzip
import os
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
            self.assertEqual(len(calls), 1)

    def test_invalid_envelope_and_truncation_fail(self):
        for content in ({}, envelope(choices=[None]), envelope(choices=["invalid"]),
                        envelope(choices=[{"finish_reason": "length", "message": {"content": "partial"}}]),
                        envelope(choices=[{"finish_reason": "stop", "message": {"content": None}}])):
            with self.subTest(content=content), self.assertRaises(ProviderError):
                OpenAICompatibleProvider(settings(), httpx.MockTransport(lambda _: httpx.Response(200, json=content))).generate(MESSAGES)

    def test_oversized_response_is_refused(self):
        with self.assertRaises(ProviderError):
            OpenAICompatibleProvider(settings(), httpx.MockTransport(lambda _: httpx.Response(200, content=b"x" * (2 * 1024 * 1024 + 1)))).generate(MESSAGES)

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
