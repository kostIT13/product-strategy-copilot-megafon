"""Whitelist response counters; never return raw content or reasoning text."""


def response_usage(envelope):
    if not isinstance(envelope, dict):
        return None
    raw = envelope.get("usage")
    raw = raw if isinstance(raw, dict) else {}
    def count(value):
        return value if type(value) is int and value >= 0 else None
    details = raw.get("completion_tokens_details")
    details = details if isinstance(details, dict) else {}
    choices = envelope.get("choices")
    choice = choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], dict) else {}
    message = choice.get("message")
    message = message if isinstance(message, dict) else {}
    content = message.get("content")
    reasoning = message.get("reasoning_content", message.get("reasoning"))
    result = {"input_tokens": count(raw.get("prompt_tokens")), "output_tokens": count(raw.get("completion_tokens")),
              "total_tokens": count(raw.get("total_tokens")), "reasoning_tokens": count(details.get("reasoning_tokens")),
              "content_chars": len(content) if isinstance(content, str) else None,
              "reasoning_chars": len(reasoning) if isinstance(reasoning, str) else None, "cost": None}
    if all(value is None for value in result.values()):
        return None
    model = envelope.get("model")
    result["reported_model"] = model if isinstance(model, str) and len(model) <= 250 else None
    return result
