"""Exercise the PostgreSQL service chain using a new synthetic audit project.

Apply Alembic migrations first. The project remains in the database for inspection.
Run only against a development database configured via DATABASE_URL / .env.
"""

import json
from uuid import uuid4

from product_strategy_agent.adapters.persistence.postgres.repositories.capability_repository import PostgresCapabilityStore
from product_strategy_agent.adapters.persistence.postgres.repositories.claim_repository import PostgresClaimStore
from product_strategy_agent.adapters.persistence.postgres.repositories.decision_repository import PostgresDecisionStore
from product_strategy_agent.adapters.persistence.postgres.repositories.option_repository import PostgresOptionStore
from product_strategy_agent.adapters.persistence.postgres.repositories.project_repository import PostgresProjectStore
from product_strategy_agent.adapters.persistence.postgres.repositories.source_repository import PostgresSourceStore
from product_strategy_agent.adapters.persistence.postgres.repositories.workflow_repository import PostgresWorkflowStore
from product_strategy_agent.application.services.capability_service import CapabilityService
from product_strategy_agent.application.services.claim_service import ClaimService
from product_strategy_agent.application.services.decision_service import DecisionService
from product_strategy_agent.application.services.option_service import OptionService
from product_strategy_agent.application.services.project_service import ProjectService
from product_strategy_agent.application.services.source_service import SourceService
from product_strategy_agent.application.services.workflow_service import WorkflowService
from product_strategy_agent.domain.decisions.entities import OptionClaim
from product_strategy_agent.domain.evidence.entities import EvidenceReference
from product_strategy_agent.domain.evidence.errors import InvalidClaim
from product_strategy_agent.domain.projects.errors import ProjectAlreadyExists
from product_strategy_agent.domain.workflow.errors import WorkflowGateBlocked


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def rejects(error_type, operation) -> None:
    try:
        operation()
    except error_type:
        return
    raise AssertionError(f"expected {error_type.__name__}")


def main() -> None:
    project_store, source_store, claim_store = PostgresProjectStore(), PostgresSourceStore(), PostgresClaimStore()
    option_store, decision_store = PostgresOptionStore(), PostgresDecisionStore()
    projects = ProjectService(project_store)
    sources = SourceService(source_store)
    claims = ClaimService(claim_store, project_store, source_store)
    options = OptionService(option_store, project_store, claim_store)
    decisions = DecisionService(decision_store, project_store, option_store, claim_store)
    capabilities = CapabilityService(PostgresCapabilityStore(), project_store, claim_store)
    workflow = WorkflowService(PostgresWorkflowStore(), project_store)
    key = f"smoke-{uuid4().hex[:16]}"
    print(json.dumps({"project_key": key, "status": "starting"}), flush=True)
    projects.create(key, "Synthetic integration smoke")
    rejects(ProjectAlreadyExists, lambda: projects.create(key, "Duplicate"))
    workflow.start(key, "synthetic-smoke")

    def advance():
        state, _ = workflow.status(key)
        return workflow.advance(key, "synthetic-smoke", "Synthetic integration check", state.version)

    advance()
    advance()
    rejects(WorkflowGateBlocked, advance)
    first = sources.register(key, "synthetic://export", "local_text", "Export is available.")
    same = sources.register(key, "synthetic://export", "local_text", "Export is available.")
    require(not same.created_revision and same.source.revision.id == first.source.revision.id,
            "same content must not create a second revision")
    advance()
    rejects(WorkflowGateBlocked, advance)
    rejects(InvalidClaim, lambda: claims.create(key, "BAD", "Invalid quote", "fact", "low",
        (EvidenceReference(first.source.id, 1, "paragraph:1", "Absent quote"),)))
    fact = claims.create(key, "C-001", "Export is available", "fact", "high",
        (EvidenceReference(first.source.id, 1, "paragraph:1", "Export is available."),))
    revised = sources.register(key, "synthetic://export", "local_text", "Export is available with limits.")
    require(revised.source.revision.revision == 2, "changed content must create revision 2")
    require(claims.list_for_project(key)[0].evidence[0].source_revision == 1,
            "claim must remain linked to its original revision")
    advance()
    rejects(WorkflowGateBlocked, advance)
    alternatives = [options.create(key, f"OPT-{i}", name, claim_links=(OptionClaim(fact.id, "supports"),))
                    for i, name in enumerate(("Maintain", "Change", "Stop"), start=1)]
    advance()
    rejects(WorkflowGateBlocked, advance)
    decision = decisions.create(key, "D-001", alternatives[0].id, "synthetic owner",
        "Synthetic rationale", "New source evidence", basis_claim_ids=(fact.id,),
        rejected_option_ids=(alternatives[1].id,), deferred_option_ids=(alternatives[2].id,))
    capabilities.create(key, "CAP-001", "Export", "available", (fact.id,))
    advance()
    completed = advance()
    require(completed.current_stage == "completed", "workflow must reach completed")
    history = workflow.history(key)
    require([event.sequence for event in history] == list(range(1, 9)), "event history must be sequential")
    require(len(decisions.list_for_project(key)) == 1, "decision must be persisted")
    require(len(capabilities.list_for_project(key)) == 1, "capability must be persisted")
    print(json.dumps({"status": "passed", "project_key": key,
                      "decision_id": str(decision.id), "events": len(history)}))


if __name__ == "__main__":
    main()
