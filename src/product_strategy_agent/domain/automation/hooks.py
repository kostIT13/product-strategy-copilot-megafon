"""Fixed hook triggers and result matching; no dispatcher, commands or side effects."""

from typing import Annotated, Literal
from uuid import UUID
from pydantic import Field, model_validator
from product_strategy_agent.domain.automation.contracts import (
    CaseTarget,
    Digest,
    Packet,
    ReleaseTarget,
    Text,
    fingerprint,
)


class HookRequest(Packet):
    operation_id: UUID
    trigger: Literal[
        "before_strategy_gate",
        "before_validation_gate",
        "source_revision",
        "release_check",
    ]
    target: Annotated[CaseTarget | ReleaseTarget, Field(discriminator="kind")]
    recursion_depth: int = Field(default=0, ge=0, le=0)

    @model_validator(mode="after")
    def target_kind(self):
        if (self.trigger == "release_check") != isinstance(self.target, ReleaseTarget):
            raise ValueError(
                "release trigger requires release target; other hooks require case target"
            )
        return self


class HookResult(Packet):
    operation_id: UUID
    request_fingerprint: Digest
    status: Literal["passed", "blocked", "failed", "skipped"]
    issues: list[Text] = Field(default_factory=list, max_length=32)

    @model_validator(mode="after")
    def status_consistency(self):
        if (self.status == "passed") != (not self.issues):
            raise ValueError(
                "passed hook has no issues; other outcomes require diagnostic issues"
            )
        return self


def validate_hook_binding(request, result):
    request = HookRequest.model_validate(request)
    result = HookResult.model_validate(result)
    if (
        result.operation_id != request.operation_id
        or result.request_fingerprint != fingerprint(request)
    ):
        raise ValueError("hook result does not match exact request/target")
    return result


def required_hook_allows(request, result):
    request = HookRequest.model_validate(request)
    result = validate_hook_binding(request, result)
    # Notification delivery is never a required pre-gate check, even after all reviews.
    return request.trigger != "source_revision" and result.status == "passed"
