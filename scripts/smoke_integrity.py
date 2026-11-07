"""PostgreSQL concurrency/isolation checks; creates two synthetic audit projects."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
from threading import Barrier
from uuid import uuid4

from sqlalchemy import func, select

from product_strategy_agent.adapters.persistence.postgres.database import get_session_factory
from product_strategy_agent.adapters.persistence.postgres.models import ClaimEvidenceRecord, ClaimRecord, SourceRevisionRecord
from product_strategy_agent.adapters.persistence.postgres.repositories.project_repository import PostgresProjectStore
from product_strategy_agent.adapters.persistence.postgres.repositories.source_repository import PostgresSourceStore
from product_strategy_agent.adapters.persistence.postgres.repositories.claim_repository import PostgresClaimStore
from product_strategy_agent.adapters.persistence.postgres.repositories.option_repository import PostgresOptionStore
from product_strategy_agent.adapters.persistence.postgres.repositories.decision_repository import PostgresDecisionStore
from product_strategy_agent.adapters.persistence.postgres.repositories.capability_repository import PostgresCapabilityStore
from product_strategy_agent.adapters.persistence.postgres.repositories.workflow_repository import PostgresWorkflowStore
from product_strategy_agent.application.services.project_service import ProjectService
from product_strategy_agent.application.services.source_service import SourceService
from product_strategy_agent.application.services.claim_service import ClaimService
from product_strategy_agent.application.services.option_service import OptionService
from product_strategy_agent.application.services.decision_service import DecisionService
from product_strategy_agent.application.services.capability_service import CapabilityService
from product_strategy_agent.application.services.workflow_service import WorkflowService
from product_strategy_agent.domain.evidence.entities import EvidenceReference
from product_strategy_agent.domain.evidence.errors import InvalidClaim
from product_strategy_agent.domain.decisions.entities import OptionClaim
from product_strategy_agent.domain.decisions.errors import InvalidOption, InvalidDecision
from product_strategy_agent.domain.capabilities.errors import InvalidCapability
from product_strategy_agent.domain.workflow.errors import WorkflowConflict
from smoke_main import require, rejects


def parallel(operation, workers=4):
    barrier = Barrier(workers)

    def run(index):
        barrier.wait(timeout=15)
        return operation(index)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        return list(executor.map(run, range(workers)))


def main():
    ps, ss, cs = PostgresProjectStore(), PostgresSourceStore(), PostgresClaimStore()
    os, ds, ws = PostgresOptionStore(), PostgresDecisionStore(), PostgresWorkflowStore()
    projects, sources = ProjectService(ps), SourceService(ss)
    claims, options = ClaimService(cs, ps, ss), OptionService(os, ps, cs)
    decisions = DecisionService(ds, ps, os, cs)
    capabilities = CapabilityService(PostgresCapabilityStore(), ps, cs)
    workflow = WorkflowService(ws, ps)
    key = f"integrity-{uuid4().hex[:12]}"
    project = projects.create(key, "Synthetic concurrency checks")
    foreign_key = key + "-other"
    foreign_project = projects.create(foreign_key, "Synthetic foreign project")
    print(json.dumps({"status": "starting", "project_key": key}), flush=True)

    same = parallel(lambda _: sources.register(key, "synthetic://race", "local_text", "Original text."))
    require(sum(item.created_revision for item in same) == 1, "concurrent duplicates must create one revision")
    require(len({item.source.id for item in same}) == 1, "concurrent source identities must agree")
    source = same[0].source
    changes = parallel(lambda i: sources.register(key, "synthetic://race", "local_text", f"Changed text {i}."))
    require(sorted(item.source.revision.revision for item in changes) == [2, 3, 4, 5],
            "concurrent changes must have distinct sequential revisions")
    with get_session_factory()() as session:
        count = session.scalar(select(func.count()).select_from(SourceRevisionRecord).where(
            SourceRevisionRecord.source_id == source.id))
        require(count == 5, "source revision count must match concurrent writes")

    state = workflow.start(key, "integrity-smoke")
    def transition(_):
        try:
            workflow.advance(key, "integrity-smoke", "Concurrent approval", state.version)
            return "advanced"
        except WorkflowConflict:
            return "conflict"
    outcomes = parallel(transition)
    require(outcomes.count("advanced") == 1 and outcomes.count("conflict") == 3,
            "one approval must win; stale approvals must conflict")
    require([event.sequence for event in workflow.history(key)] == [1, 2], "stale approvals must not append events")
    rejects(WorkflowConflict, lambda: workflow.advance(key, "integrity-smoke", "Delayed approval", state.version))

    foreign = sources.register(foreign_key, "synthetic://foreign", "local_text", "Foreign text.").source
    fact = claims.create(key, "FACT", "Original", "fact", "high",
                         (EvidenceReference(source.id, 1, "paragraph:1", "Original text."),))
    foreign_fact = claims.create(foreign_key, "FACT", "Foreign", "fact", "high",
                         (EvidenceReference(foreign.id, 1, "paragraph:1", "Foreign text."),))
    rejects(InvalidClaim, lambda: claims.create(key, "CROSS", "Foreign", "fact", "high", foreign_fact.evidence))
    rejects(InvalidOption, lambda: options.create(key, "CROSS", "Cross", claim_links=(OptionClaim(foreign_fact.id, "supports"),)))
    rejects(InvalidCapability, lambda: capabilities.create(key, "CROSS", "Cross", "available", (foreign_fact.id,)))
    local_option = options.create(key, "LOCAL", "Local")
    foreign_option = options.create(foreign_key, "FOREIGN", "Foreign")
    rejects(InvalidDecision, lambda: decisions.create(key, "CROSS", foreign_option.id, "owner", "reason", "trigger"))

    # Bypass service validation to force repository failure after the parent and
    # first child have been flushed. A new session must see no partial rows.
    bad_claim = replace(fact, id=uuid4(), key="ROLLBACK", evidence=fact.evidence + foreign_fact.evidence)
    rejects(InvalidClaim, lambda: cs.create(bad_claim))
    with get_session_factory()() as session:
        require(session.get(ClaimRecord, bad_claim.id) is None, "failed claim parent must roll back")
        require(session.scalar(select(func.count()).select_from(ClaimEvidenceRecord).where(
            ClaimEvidenceRecord.claim_id == bad_claim.id)) == 0, "failed claim children must roll back")
    bad_option = replace(local_option, id=uuid4(), key="ROLLBACK", claim_links=(
        OptionClaim(fact.id, "supports"), OptionClaim(foreign_fact.id, "supports")))
    rejects(InvalidOption, lambda: os.create(bad_option))
    require(os.get_by_id(bad_option.id) is None, "failed option must roll back")
    valid_decision = decisions.create(key, "VALID", local_option.id, "owner", "reason", "trigger", basis_claim_ids=(fact.id,))
    bad_decision = replace(valid_decision, id=uuid4(), key="ROLLBACK", basis_claim_ids=(fact.id, foreign_fact.id))
    rejects(InvalidDecision, lambda: ds.create(bad_decision))
    require(len(ds.list_for_project(key)) == 1, "failed decision must not persist")
    require(len(claims.list_for_project(key)) == 1, "cross-project attempts must not create claims")
    print(json.dumps({"status": "passed", "project_key": key, "foreign_project_id": str(foreign_project.id),
                      "source_revisions": 5, "approval_results": outcomes,
                      "cross_project_checks": 4, "rollback_checks": 3}))


if __name__ == "__main__":
    main()
