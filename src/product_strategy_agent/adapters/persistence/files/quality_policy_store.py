"""Read creation provenance and commit explicit legacy policy migration through workflow v1."""

import json
from product_strategy_agent.adapters.persistence.files.case_access import (
    locked_store_method,
)
from product_strategy_agent.adapters.persistence.files.paths import confined
from product_strategy_agent.adapters.persistence.files.artifact_bundle import read_small
from product_strategy_agent.adapters.persistence.files.workspace_manifest import (
    load_receipt,
)
from product_strategy_agent.adapters.persistence.files.workflow_repository import (
    FileWorkflowStore,
)
from product_strategy_agent.domain.projects.quality_policy import policy_required


def initially_required(case):
    path = confined(case, ".psa/initialization.json")
    if not path.exists():
        return False  # Historical MVP folders can predate init receipts.
    receipt = json.loads(read_small(case, ".psa/initialization.json"))
    if not isinstance(receipt, dict) or not isinstance(
        receipt.get("operation_id"), str
    ):
        raise ValueError("invalid initialization receipt for quality policy")
    checked = load_receipt(case, case.name, receipt["operation_id"])
    return checked["format_version"] == 2


def required_for_case(case, state, events):
    return policy_required(state, events, initially_required(case))


class FileQualityPolicyStore:
    def __init__(self, root):
        self.workflow = FileWorkflowStore(root)
        self.root = self.workflow.root

    def access(self, project_id):
        return self.workflow.access(project_id)

    def replay(self, project_id, command):
        return self.workflow.replay(project_id, command)

    @locked_store_method()
    def capture(self, project_id):
        return {
            **self.workflow.capture(project_id),
            "initially_required": initially_required(self.workflow._case(project_id)),
        }

    @locked_store_method()
    def commit(self, project_id, command, snapshot, timestamp):
        return self.workflow.commit(
            project_id,
            command,
            snapshot["state"],
            snapshot["after"],
            snapshot["events"],
            snapshot["event"],
            snapshot["inputs"],
        )
