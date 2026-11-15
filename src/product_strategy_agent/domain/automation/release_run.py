"""Release-check execution config; artifact paths stay outside untrusted packets."""

from pydantic import Field, model_validator
from product_strategy_agent.domain.automation.contracts import Packet
from product_strategy_agent.domain.automation.hooks import HookRequest


class ReleaseRun(Packet):
    request: HookRequest
    timeout_seconds: int = Field(default=30, ge=1, le=120)

    @model_validator(mode="after")
    def release_only(self):
        if self.request.trigger != "release_check":
            raise ValueError("release run requires release_check trigger")
        return self
