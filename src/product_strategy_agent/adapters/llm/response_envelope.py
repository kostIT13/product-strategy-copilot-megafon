"""Only pass the text-only chat contract to the SDK, not provider extensions."""
import json


def sdk_response_body(envelope: dict) -> bytes:
    choice = envelope["choices"][0]
    result = {"id": envelope.get("id") if isinstance(envelope.get("id"), str) else "completion",
              "object": "chat.completion",
              "created": envelope.get("created") if type(envelope.get("created")) is int else 0,
              "model": envelope.get("model") if isinstance(envelope.get("model"), str) else "unknown",
              "choices": [{"index": 0, "finish_reason": "stop", "message": {
                  "role": "assistant", "content": choice["message"]["content"]}}]}
    usage = envelope.get("usage")
    if isinstance(usage, dict):
        result["usage"] = {name: usage[name] for name in ("prompt_tokens", "completion_tokens", "total_tokens")
                           if type(usage.get(name)) is int and usage[name] >= 0}
    return json.dumps(result, ensure_ascii=True).encode("utf-8")
