"""Compose coherent file checks and publish/replay human review through the journal."""

import json
from pathlib import Path
from product_strategy_agent.adapters.persistence.files.case_access import (
    locked_store_method,
)
from product_strategy_agent.adapters.persistence.files.paths import confined
from product_strategy_agent.adapters.persistence.files.artifact_bundle import read_small
from product_strategy_agent.adapters.persistence.files.workflow_repository import (
    FileWorkflowStore,
)
from product_strategy_agent.adapters.persistence.files.workflow_bundle import payload
from product_strategy_agent.adapters.persistence.files.semantic_review_bundle import (
    extra_payload,
)
from product_strategy_agent.adapters.persistence.files.semantic_gate_proof import (
    selected_review,
)

DOCUMENTS = (
    "01_brief.md",
    "02_research-plan.md",
    "drafts/product-strategy.md",
    "drafts/communication-strategy.md",
    "drafts/validation-plan.md",
)


class FileSemanticReviewStore:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.workflow = FileWorkflowStore(self.root)

    def access(self, project_id):
        return self.workflow.access(project_id)

    def replay(self, project_id, command):
        return self.workflow.replay(project_id, command)

    @locked_store_method()
    def capture(self, project_id):
        case = self.workflow._case(project_id)
        snapshot = self.workflow.capture_claims(project_id)
        snapshot["documents"] = {
            name: read_small(case, name).decode("utf-8")
            if confined(case, name).exists()
            else None
            for name in DOCUMENTS
        }
        return snapshot

    @locked_store_method()
    def checks(self, project_id, scope, snapshot):
        from product_strategy_agent.coverage import coverage_report
        from product_strategy_agent.application.services.strategy_structure_service import (
            StrategyStructureService,
        )
        from product_strategy_agent.adapters.persistence.files.strategy_structure_reader import (
            FileStrategyStructureReader,
        )
        from product_strategy_agent.application.services.validation_plan_service import (
            ValidationPlanService,
        )
        from product_strategy_agent.application.services.baseline_numbers_service import (
            BaselineNumbersService,
        )
        from product_strategy_agent.adapters.persistence.files.validation_plan_store import (
            FileValidationPlanStore,
        )
        from product_strategy_agent.application.services.claim_lifecycle_service import (
            impact_from_snapshot,
        )
        from product_strategy_agent.adapters.persistence.files.promise_reader import (
            FilePromiseReader,
        )
        from product_strategy_agent.domain.projects.file_promises import check_claim

        case = self.workflow._case(project_id)
        coverage = coverage_report(case)
        structure = StrategyStructureService(
            FileStrategyStructureReader(self.root)
        ).check(project_id)
        impact = impact_from_snapshot(project_id, snapshot)
        claims = [
            json.loads(line) for line in snapshot["claims"].splitlines() if line.strip()
        ]
        facts = [
            row["claim_id"]
            for row in claims
            if row.get("type") == "fact"
            and impact["statuses"][row["claim_id"]] == "active"
        ]
        evidence = FilePromiseReader(self.root).read_for_claims(project_id, facts)
        proof = [check_claim(key, evidence) for key in facts]
        issues = list(coverage["errors"])
        if structure["structural_status"] != "complete":
            issues.append("strategy sections are incomplete")
        if (
            impact["current_decision_id"] is None
            or impact["current_decision_needs_review"]
        ):
            issues.append(
                "current human decision is missing or requires evidence review"
            )
        issues.extend(
            f"{row['claim_id']}: {item}" for row in proof for item in row["blockers"]
        )
        measurement = numbers = None
        if scope == "validation":
            store = FileValidationPlanStore(self.root)
            measurement = ValidationPlanService(store).check(project_id)
            numbers = BaselineNumbersService(store).check(project_id)
            if measurement["structural_status"] != "complete":
                issues.extend(measurement["issues"])
            if numbers["status"] == "blocked":
                issues.extend(numbers["issues"])
        return {
            "coverage": coverage,
            "structure": structure,
            "impact": impact,
            "factual_evidence": proof,
            "measurement": measurement,
            "baseline_numbers": numbers,
            "blocking_issues": sorted(set(issues)),
        }

    @locked_store_method()
    def commit(self, project_id, command, snapshot, packet, timestamp):
        case = self.workflow._case(project_id)
        extras, state, event = extra_payload(command, snapshot, packet, timestamp)
        files, manifest = payload(
            project_id,
            command,
            snapshot["state"],
            state,
            snapshot["events"],
            event,
            snapshot["inputs"],
            extras,
        )
        return self.workflow._publish(case, command, files, manifest)

    @locked_store_method()
    def require_gate_review(self, project_id, scope, operation_id, packet):
        snapshot = self.capture(project_id)
        state = json.loads(snapshot["state"])
        events = [
            json.loads(line) for line in snapshot["events"].splitlines() if line.strip()
        ]
        return selected_review(
            confined(self.workflow._case(project_id), ".psa/workflow/operations"),
            project_id,
            scope,
            operation_id,
            state,
            events,
            snapshot["inputs"],
        )
