"""Bounded provider diagnostics safe to persist or expose through CLI/MCP."""

PROVIDER_ERROR_CODES = frozenset({
    "provider_error", "provider_dependency_missing", "provider_invalid_endpoint",
    "provider_missing_key", "provider_invalid_extra_body", "provider_timeout",
    "provider_connection_error", "provider_tls_error", "provider_response_too_large",
    "provider_invalid_json", "provider_invalid_envelope", "provider_incomplete_completion",
    "provider_empty_content", "provider_sdk_error",
}) | frozenset(f"provider_http_{status}" for status in range(100, 600))


class ProviderError(Exception):
    """Never put upstream exception text, bodies, URLs or headers in the code."""

    def __init__(self, message: str = "model provider failed", *, code: str = "provider_error"):
        if code not in PROVIDER_ERROR_CODES:
            raise ValueError("unknown provider diagnostic code")
        self.code = code
        super().__init__(message)
