"""HTTP contract checks without sending data to an external model."""
import json
import unittest
import httpx
from pydantic import SecretStr

from product_strategy_agent.adapters.llm.qwen import QwenChatProvider
from product_strategy_agent.config import Settings
from product_strategy_agent.domain.agent.models import ProviderError


def settings(**overrides):
    values = dict(qwen_base_url="https://provider.example/v1", qwen_model="fixture-model",
                  qwen_api_key=SecretStr("synthetic-key"), qwen_max_output_tokens=2048,
                  qwen_timeout_seconds=60, qwen_enable_thinking=None)
    values.update(overrides)
    return Settings(_env_file=None, **values)


def envelope(**overrides):
    result = {"model": "reported-model", "choices": [{"finish_reason": "stop", "message": {"content": '{"draft":true}'}}]}
    result.update(overrides)
    return result


MESSAGES = [{"role": "system", "content": "Return JSON"}]


class QwenProviderTests(unittest.TestCase):
    def test_request_contract_and_unknown_usage(self):
        requests = []
        def handle(request):
            requests.append(request)
            return httpx.Response(200, json=envelope())
        result = QwenChatProvider(settings(qwen_enable_thinking=False), httpx.MockTransport(handle)).generate(MESSAGES)
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
        result = QwenChatProvider(settings(), transport).generate(MESSAGES)
        self.assertEqual(result.usage["total_tokens"], 120)
        self.assertEqual(result.usage["reported_model"], "reported-model")

    def test_endpoint_errors_do_not_retry_or_reveal_body(self):
        for status in (302, 401, 429, 500):
            calls = []
            def handle(request):
                calls.append(request)
                return httpx.Response(status, text="synthetic-key secret response", headers={"Location": "https://other.example/"})
            with self.subTest(status=status), self.assertRaises(ProviderError) as error:
                QwenChatProvider(settings(), httpx.MockTransport(handle)).generate(MESSAGES)
            self.assertNotIn("synthetic-key", str(error.exception))
            self.assertEqual(len(calls), 1)

    def test_invalid_envelope_and_truncation_fail(self):
        for content in ({}, envelope(choices=[None]), envelope(choices=["invalid"]),
                        envelope(choices=[{"finish_reason": "length", "message": {"content": "partial"}}]),
                        envelope(choices=[{"finish_reason": "stop", "message": {"content": None}}])):
            with self.subTest(content=content), self.assertRaises(ProviderError):
                QwenChatProvider(settings(), httpx.MockTransport(lambda _: httpx.Response(200, json=content))).generate(MESSAGES)

    def test_oversized_response_is_refused(self):
        with self.assertRaises(ProviderError):
            QwenChatProvider(settings(), httpx.MockTransport(lambda _: httpx.Response(200, content=b"x" * (2 * 1024 * 1024 + 1)))).generate(MESSAGES)

    def test_missing_key_and_invalid_endpoints_fail_before_network(self):
        for config in (settings(qwen_api_key=SecretStr("")), settings(qwen_base_url="http://remote.example/v1"),
                       settings(qwen_base_url="https://user:secret@provider.example/v1"),
                       settings(qwen_base_url="https://provider.example:bad/v1")):
            calls = []
            with self.subTest(), self.assertRaises(ProviderError):
                QwenChatProvider(config, httpx.MockTransport(lambda request: calls.append(request))).generate(MESSAGES)
            self.assertFalse(calls)

    def test_local_endpoint_can_run_without_a_key(self):
        def handle(request):
            self.assertNotIn("authorization", request.headers)
            return httpx.Response(200, json=envelope())
        QwenChatProvider(settings(qwen_base_url="http://127.0.0.1:8000/v1", qwen_api_key=SecretStr("")),
                         httpx.MockTransport(handle)).generate(MESSAGES)
