"""Composition and strict JSON boundary for explicit local preflight."""

import json
from pydantic import ValidationError
from product_strategy_agent.domain.automation.handoffs import strict_json
from product_strategy_agent.domain.automation.hooks import HookRequest
from product_strategy_agent.application.services.hook_preflight_service import (
    HookPreflightService,
)
from product_strategy_agent.adapters.persistence.files.hook_preflight_reader import (
    FileHookPreflightReader,
)


def parse_hook_request(raw):
    if len(raw) > 64000:
        raise ValueError("hook request exceeds 64000 bytes")
    try:
        return HookRequest.model_validate_json(
            json.dumps(strict_json(raw), ensure_ascii=False, allow_nan=False)
        )
    except ValidationError:
        # Union tag errors can echo attacker-supplied values even without input/context.
        raise ValueError("invalid hook request schema") from None


def hook_preflight(root):
    return HookPreflightService(FileHookPreflightReader(root))
