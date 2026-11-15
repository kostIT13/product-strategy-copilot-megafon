"""Read-only capability matrix and scoped fallback proposals, never native activation."""

from copy import deepcopy

from product_strategy_agent.application.ports.host_catalog_reader import (
    HostCatalogReader,
)
from product_strategy_agent.domain.automation.contracts import fingerprint
from product_strategy_agent.domain.automation.host_profiles import PlanHost

FALLBACK = {
    "mode": "sequential",
    "requires_case_selection": True,
    "steps": [
        "Read AGENTS.md and agent/README.md",
        "psa status ID",
        "psa resume ID",
        "psa context ID",
    ],
    "human_gates_required": True,
}


class HostProfileService:
    def __init__(self, reader: HostCatalogReader):
        self.reader = reader

    def catalog(self):
        catalog, digest = self.reader.read()
        return {
            "format_version": "psa-host-matrix-v1",
            "catalog_version": catalog.catalog_version,
            "catalog_sha256": digest,
            "hosts": [profile.model_dump(mode="json") for profile in catalog.hosts],
            "native_activation_allowed": False,
            "host_acceptance_verified": False,
        }

    def profile(self, host_id):
        catalog, digest = self.reader.read()
        profile = next(
            (item for item in catalog.hosts if item.host_id == host_id), None
        )
        if profile is None:
            raise ValueError("unknown host profile")
        return {
            "format_version": "psa-host-profile-v1",
            "catalog_version": catalog.catalog_version,
            "catalog_sha256": digest,
            "profile": profile.model_dump(mode="json"),
            "instruction_surfaces": self.reader.surfaces(profile),
            "fallback": deepcopy(FALLBACK),
            "native_activation_allowed": False,
            "host_acceptance_verified": False,
        }

    def plan(self, command):
        command = PlanHost.model_validate(command)
        profile = self.profile(command.host_id)
        return {
            "format_version": "psa-host-plan-v1",
            "request": command.model_dump(mode="json"),
            "request_fingerprint": fingerprint(command),
            "catalog_sha256": profile["catalog_sha256"],
            "catalog_version": profile["catalog_version"],
            "instruction_surfaces": profile["instruction_surfaces"],
            "status": "ready" if command.mode == "sequential" else "fallback_required",
            "proposed_mode": "sequential",
            "native_capability_status": "not_verified",
            "reason": "Exact host version/platform native acceptance has not been recorded",
            "fallback": deepcopy(FALLBACK),
            "native_activation_allowed": False,
            "execution_started": False,
            "configuration_written": False,
            "external_transfer_authorized": False,
            "human_approval_granted": False,
        }
