"""Transaction-scoped rechecks; parent UPDATE locks also guard new FK child links."""
from types import SimpleNamespace
from uuid import UUID
from sqlalchemy import func, select
from product_strategy_agent.adapters.persistence.postgres.models import (
    AgentRunRecord, DecisionRecord, DecisionClaimRecord, DecisionOptionRecord, OptionRecord, OptionClaimRecord,
    SourceRecord, SourceRevisionRecord, StrategyInputRecord, StrategySelectionRecord)
from product_strategy_agent.adapters.persistence.postgres.repositories.agent_run_repository import PostgresAgentRunStore
from product_strategy_agent.application.services.agent_context import source_context, review_target_hash
from product_strategy_agent.domain.decisions.selection import fingerprint, run_fingerprint


def locked_row(session, model, project_id, row_id):
    row = session.scalar(select(model).where(model.id == row_id, model.project_id == project_id).with_for_update())
    if row is None:
        raise ValueError("reviewed record no longer exists in this project")
    return row


def guard_approval_inputs(session, project_id, preview):
    snapshot = preview["strategy_input"]
    selection = session.scalar(select(StrategySelectionRecord).where(
        StrategySelectionRecord.project_id == project_id,
        StrategySelectionRecord.source_run_id == UUID(snapshot["source_run_id"])).with_for_update())
    if selection is None or fingerprint(selection.payload) != snapshot["receipt_hash"]:
        raise ValueError("recorded selection changed before approval")
    expected_runs = {preview["strategy_run_id"]: preview["strategy_fingerprint"],
        preview["critic_run_id"]: preview["critic_fingerprint"],
        snapshot["source_run_id"]: snapshot["source_fingerprint"],
        selection.payload["critic_run_id"]: snapshot["critic_hash"]}
    for run_id, expected in sorted(expected_runs.items()):
        row = locked_row(session, AgentRunRecord, project_id, UUID(run_id))
        if run_fingerprint(PostgresAgentRunStore._entity(row)) != expected:
            raise ValueError("reviewed run changed before approval")
    inputs = session.scalar(select(StrategyInputRecord).where(StrategyInputRecord.project_id == project_id,
        StrategyInputRecord.input_hash == preview["strategy_input_hash"]).with_for_update())
    if (inputs is None or inputs.snapshot != snapshot or review_target_hash(inputs.snapshot) != preview["strategy_input_hash"]
            or str(inputs.source_run_id) != snapshot["source_run_id"] or str(inputs.decision_id) != snapshot["decision"]["id"]):
        raise ValueError("strategy input changed before approval")
    for model, expected, children, parent_key in (
        (DecisionRecord, snapshot["decision"], (DecisionOptionRecord, DecisionClaimRecord), "decision_id"),
        (OptionRecord, snapshot["selected_option"], (OptionClaimRecord,), "option_id")):
        row = locked_row(session, model, project_id, UUID(expected["id"]))
        # Compare scalar columns using the same JSON representation as the application snapshot.
        for column in row.__table__.columns:
            value = getattr(row, column.name)
            if column.name in expected and (str(value) if isinstance(value, UUID) or column.name.endswith("_at") else value) != expected[column.name]:
                raise ValueError("canonical strategy record changed before approval")
        for child in children:
            rows = session.scalars(select(child).where(getattr(child, parent_key) == row.id).with_for_update()).all()
            if child is DecisionOptionRecord:
                actual = sorted((str(item.option_id), item.disposition) for item in rows)
                wanted = sorted((item["option_id"], item["disposition"]) for item in expected["alternatives"])
                if actual != wanted:
                    raise ValueError("decision alternatives changed before approval")
            elif rows:
                raise ValueError("canonical evidence links changed before approval")
    for reference in sorted(preview["contexts"], key=lambda item: item["source_id"]):
        source_id = UUID(reference["source_id"])
        source = locked_row(session, SourceRecord, project_id, source_id)
        latest = session.scalar(select(func.max(SourceRevisionRecord.revision)).where(SourceRevisionRecord.source_id == source_id))
        revision = session.scalar(select(SourceRevisionRecord).where(SourceRevisionRecord.source_id == source_id,
            SourceRevisionRecord.revision == reference["revision"]).with_for_update())
        if revision is None or latest != reference["revision"]:
            raise ValueError("source revisions changed before approval")
        context = source_context(SimpleNamespace(id=source.id, uri=source.uri, revision=revision), reference["context_chars"])
        rebuilt = {**{key: value for key, value in context.items() if key != "text"}, "context_chars": len(context["text"])}
        if rebuilt != reference:
            raise ValueError("source checkpoint changed before approval")
