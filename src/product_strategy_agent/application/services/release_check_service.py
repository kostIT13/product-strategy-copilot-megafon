"""Explicit offline release integrity, without install, tags, draft or publication."""

from uuid import UUID
from product_strategy_agent.application.ports.release_reader import ReleaseReader
from product_strategy_agent.application.services.hook_preflight_service import (
    nonrecursive,
)
from product_strategy_agent.domain.automation.contracts import (
    ReleaseTarget,
    fingerprint,
)
from product_strategy_agent.domain.automation.hooks import HookRequest, HookResult


class ReleaseCheckService:
    def __init__(self, reader: ReleaseReader):
        self.reader = reader

    def prepare(self, archive, operation_id):
        if not isinstance(operation_id, UUID):
            raise ValueError("release check requires UUID")
        with nonrecursive():
            info = self.reader.inspect(archive)
            return HookRequest(
                operation_id=operation_id,
                trigger="release_check",
                target=ReleaseTarget(manifest_hash=info["manifest_hash"]),
            ).model_dump(mode="json")

    def check(self, command, archive):
        command = HookRequest.model_validate(command)
        if command.trigger != "release_check":
            raise ValueError("release check requires release_check trigger")

        def result(status, issues):
            return HookResult(
                operation_id=command.operation_id,
                request_fingerprint=fingerprint(command),
                status=status,
                issues=issues,
            ).model_dump(mode="json")

        with nonrecursive():
            try:
                info = self.reader.inspect(archive)
            except (ValueError, KeyError, TypeError):
                return result(
                    "blocked",
                    [
                        "release integrity checks blocked; inspect archive, manifest and SHA256SUMS"
                    ],
                )
            except OSError:
                return result(
                    "failed",
                    ["release assets unavailable; inspect configured artifact path"],
                )
            if info["manifest_hash"] != command.target.manifest_hash:
                return result(
                    "blocked", ["release manifest is stale; prepare a new request"]
                )
            if info["dirty"]:
                return result(
                    "blocked",
                    [
                        "release manifest describes a dirty checkout; rebuild from a clean commit"
                    ],
                )
            return result("passed", [])
