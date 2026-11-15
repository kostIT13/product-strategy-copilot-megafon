"""Bounded explicit runs, immutable historical outcomes and safe journal decoding."""

import json
from typing import Literal
from pydantic import AwareDatetime, Field, ValidationError, model_validator
from product_strategy_agent.domain.automation.contracts import Packet, fingerprint
from product_strategy_agent.domain.automation.hooks import (
    HookRequest,
    HookResult,
    validate_hook_binding,
)
from product_strategy_agent.domain.automation.handoffs import strict_json


class HookRun(Packet):
    request: HookRequest
    timeout_seconds: int = Field(default=30, ge=1, le=120)

    @model_validator(mode="after")
    def supported(self):
        if self.request.trigger not in {
            "before_strategy_gate",
            "before_validation_gate",
        }:
            raise ValueError("only before-gate execution is supported")
        return self


class HookCompletion(Packet):
    run_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    result: HookResult
    recorded_at: AwareDatetime
    completion: Literal["attempted", "interrupted"]


def encode(packet):
    raw = json.dumps(
        {"packet": packet.model_dump(mode="json"), "hash": fingerprint(packet)},
        ensure_ascii=False,
        sort_keys=True,
    ).encode("utf-8")
    if len(raw) > 128000:
        raise ValueError("hook journal record exceeds 128000 bytes")
    return raw


def decode(raw, model):
    try:
        body = strict_json(raw)
        if not isinstance(body, dict) or set(body) != {"packet", "hash"}:
            raise ValueError("invalid envelope")
        packet = model.model_validate_json(
            json.dumps(body["packet"], ensure_ascii=False, allow_nan=False)
        )
        if fingerprint(packet) != body["hash"]:
            raise ValueError("invalid hash")
        return packet
    except (ValidationError, ValueError, TypeError):
        raise ValueError("invalid hook journal schema/hash") from None


def validate_completion(run, completion):
    if completion.run_hash != fingerprint(run):
        raise ValueError("hook completion does not match run")
    validate_hook_binding(run.request, completion.result)
    if completion.completion == "interrupted" and completion.result.status != "failed":
        raise ValueError("interrupted hook cannot pass")
    return completion
