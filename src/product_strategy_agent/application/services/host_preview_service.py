"""Prepare a reviewable disabled configuration, independent of native activation."""

import sys
from product_strategy_agent.domain.automation.host_profiles import PlanHost


class HostPreviewService:
    def __init__(self, profiles, reviews, renderer):
        self.profiles, self.reviews, self.renderer = profiles, reviews, renderer

    def preview(self, plan, interpreter, review_id=None):
        plan = PlanHost.model_validate(plan)
        if (
            plan.host_id != "codex"
            or plan.feature != "mcp_stdio"
            or plan.mode != "native"
        ):
            raise ValueError(
                "this preview adapter supports only Codex native MCP stdio proposals"
            )
        platform = (
            "windows"
            if sys.platform == "win32"
            else "macos"
            if sys.platform == "darwin"
            else "linux"
        )
        if plan.platform != platform:
            raise ValueError(
                "preview requires local platform scope for interpreter path validation"
            )
        profile = self.profiles.plan(plan)
        review = (
            self.reviews.select_for_preview(review_id, plan)
            if review_id is not None
            else None
        )
        return {
            "format_version": "psa-host-config-preview-v1",
            "request": plan.model_dump(mode="json"),
            "catalog_sha256": profile["catalog_sha256"],
            "instruction_surfaces": profile["instruction_surfaces"],
            "review": review,
            "review_status": "selected_for_preview" if review else "not_reviewed",
            "preview": self.renderer.render(interpreter),
            "execution_started": False,
            "configuration_written": False,
            "host_acceptance_verified": False,
            "native_activation_allowed": False,
            "external_transfer_authorized": False,
            "human_approval_granted": False,
        }
