"""One transaction: recheck pinned inputs, insert three alternatives and a human decision."""
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from product_strategy_agent.adapters.persistence.postgres.database import get_session_factory
from product_strategy_agent.adapters.persistence.postgres.models import (
    AgentRunRecord, DecisionOptionRecord, DecisionRecord, OptionRecord, ProjectRecord,
    SourceRecord, SourceRevisionRecord, StrategySelectionRecord)
from product_strategy_agent.adapters.persistence.postgres.repositories.agent_run_repository import PostgresAgentRunStore
from product_strategy_agent.application.services.agent_context import source_context
from product_strategy_agent.domain.decisions.selection import run_fingerprint, option_description


class PostgresStrategySelectionStore:
    def get(self, project_id, source_run_id):
        with get_session_factory()() as session:
            record = session.scalar(select(StrategySelectionRecord).where(
                StrategySelectionRecord.project_id == project_id, StrategySelectionRecord.source_run_id == source_run_id))
            return record.payload if record else None

    def record(self, project_id, command, request_hash, preview):
        try:
            with get_session_factory().begin() as session:
                if session.scalar(select(ProjectRecord).where(ProjectRecord.id == project_id).with_for_update()) is None:
                    raise ValueError("project no longer exists")
                existing = session.scalar(select(StrategySelectionRecord).where(
                    StrategySelectionRecord.project_id == project_id, StrategySelectionRecord.source_run_id == command.source_run_id))
                if existing:
                    if existing.request_hash != request_hash:
                        raise ValueError("this options run already has a different recorded selection")
                    return existing.payload
                for run_id, expected in sorted(((command.source_run_id, preview["source_fingerprint"]),
                                                (command.critic_run_id, preview["critic_hash"])), key=lambda item: str(item[0])):
                    row = session.scalar(select(AgentRunRecord).where(AgentRunRecord.id == run_id,
                        AgentRunRecord.project_id == project_id).with_for_update(read=True))
                    if row is None or run_fingerprint(PostgresAgentRunStore._entity(row)) != expected:
                        raise ValueError("reviewed run changed before recording")
                for reference in sorted(preview["contexts"], key=lambda item: item["source_id"]):
                    source_id = UUID(reference["source_id"])
                    source = session.scalar(select(SourceRecord).where(SourceRecord.id == source_id,
                        SourceRecord.project_id == project_id).with_for_update(read=True))
                    latest = session.scalar(select(func.max(SourceRevisionRecord.revision)).where(SourceRevisionRecord.source_id == source_id))
                    revision = session.scalar(select(SourceRevisionRecord).where(SourceRevisionRecord.source_id == source_id,
                        SourceRevisionRecord.revision == reference["revision"]).with_for_update(read=True))
                    if source is None or revision is None or latest != reference["revision"]:
                        raise ValueError("source revisions changed before recording")
                    context = source_context(SimpleNamespace(id=source.id, uri=source.uri, revision=revision), reference["context_chars"])
                    rebuilt = {**{key: value for key, value in context.items() if key != "text"}, "context_chars": len(context["text"])}
                    if rebuilt != reference:
                        raise ValueError("source checkpoint changed before recording")
                now = datetime.now(timezone.utc)
                ids = {item: uuid4() for item in ("O1", "O2", "O3")}
                draft = preview["draft"]
                for option in draft["options"]:
                    session.add(OptionRecord(id=ids[option["option_id"]], project_id=project_id,
                        key=f"ai-{command.source_run_id.hex}-{option['option_id'].lower()}", name=option["name"],
                        description=option_description(option), strengths=[], risks=option["risks"],
                        assumptions=[f"{item['text']} Validate: {item['validation_question']}" for item in option["assumptions"]],
                        status="proposed", created_at=now))
                session.flush()
                selected = next(item for item in draft["options"] if item["option_id"] == command.selected)
                decision_id, review_id = uuid4(), uuid4()
                session.add(DecisionRecord(id=decision_id, project_id=project_id, key=command.decision_key,
                    selected_option_id=ids[command.selected], owner=command.owner, rationale=command.rationale,
                    assumptions=[item["text"] for item in selected["assumptions"]], risks=selected["risks"],
                    review_trigger=command.review_trigger, decided_at=now))
                session.flush()
                for disposition, local_ids in (("selected", [command.selected]), ("rejected", command.rejected), ("deferred", command.deferred)):
                    for local_id in local_ids:
                        session.add(DecisionOptionRecord(id=uuid4(), decision_id=decision_id, option_id=ids[local_id], disposition=disposition))
                payload = {"id": str(review_id), "project_id": str(project_id), "source_run_id": str(command.source_run_id),
                    "critic_run_id": str(command.critic_run_id), "decision_id": str(decision_id),
                    "option_ids": {key: str(value) for key, value in ids.items()}, "request_hash": request_hash,
                    "recorded_at": now.isoformat(), "command": command.model_dump(mode="json"), "review_snapshot": preview,
                    "workflow_approval_granted": False, "identity_verified": False}
                session.add(StrategySelectionRecord(id=review_id, project_id=project_id, source_run_id=command.source_run_id,
                    critic_run_id=command.critic_run_id, decision_id=decision_id, o1_id=ids["O1"], o2_id=ids["O2"], o3_id=ids["O3"],
                    request_hash=request_hash, payload=payload))
                session.flush()
                return payload
        except IntegrityError:
            raise ValueError("canonical key or reference conflict; selection transaction rolled back") from None
