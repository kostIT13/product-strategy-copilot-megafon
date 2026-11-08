"""Atomic attempt reservation and optimistic versioned checkpoint transitions."""
from dataclasses import asdict
from datetime import datetime, timezone
from sqlalchemy import select

from product_strategy_agent.adapters.persistence.postgres.database import get_session_factory
from product_strategy_agent.adapters.persistence.postgres.models.agent_pipeline import AgentPipelineRecord
from product_strategy_agent.adapters.persistence.postgres.models.agent_run import AgentRunRecord
from product_strategy_agent.domain.agent.pipeline import AgentPipeline, PipelineConflict


class PostgresAgentPipelineStore:
    def create(self, pipeline):
        if pipeline.status != "prepared" or pipeline.version != 0 or pipeline.agent_run_id is not None:
            raise ValueError("pipeline must begin with prepared evidence")
        with get_session_factory().begin() as session:
            session.add(AgentPipelineRecord(**asdict(pipeline)))
        return pipeline

    def get(self, project_id, pipeline_id):
        with get_session_factory()() as session:
            row = session.scalar(select(AgentPipelineRecord).where(
                AgentPipelineRecord.id == pipeline_id, AgentPipelineRecord.project_id == project_id))
            return self._entity(row) if row else None

    def reserve(self, project_id, pipeline_id, expected_version, run):
        with get_session_factory().begin() as session:
            row = self._locked(session, project_id, pipeline_id, expected_version)
            if row.status != "prepared":
                raise PipelineConflict("pipeline draft has already been reserved")
            if (run.project_id != project_id or run.status != "running" or run.contexts != row.contexts
                    or (run.question, run.query, run.model, run.prompt_version) !=
                       (row.question, row.query, row.model, row.prompt_version)):
                raise ValueError("agent attempt does not match pipeline evidence")
            session.add(AgentRunRecord(**asdict(run)))
            session.flush()
            row.agent_run_id, row.status = run.id, "draft_running"
            self._bump(row)
            session.flush()
            return self._entity(row)

    def advance(self, project_id, pipeline_id, expected_version, status, *, result=None):
        with get_session_factory().begin() as session:
            row = self._locked(session, project_id, pipeline_id, expected_version)
            run = session.scalar(select(AgentRunRecord).where(
                AgentRunRecord.id == row.agent_run_id, AgentRunRecord.project_id == project_id))
            if row.status == "draft_running" and status in {"draft_ready", "failed"}:
                expected = "succeeded" if status == "draft_ready" else "failed"
                if run is None or run.status != expected:
                    raise PipelineConflict("model attempt has not reached the expected terminal state")
                row.error_code = run.error_code if status == "failed" else None
            elif row.status == "draft_ready" and status == "completed" and result is not None:
                if run is None or run.status != "succeeded":
                    raise PipelineConflict("pipeline requires a successful draft")
                row.result = result
            else:
                raise PipelineConflict("invalid pipeline checkpoint transition")
            row.status = status
            self._bump(row)
            session.flush()
            return self._entity(row)

    @staticmethod
    def _locked(session, project_id, pipeline_id, expected_version):
        if type(expected_version) is not int or expected_version < 0:
            raise ValueError("expected version must be a nonnegative integer")
        row = session.scalar(select(AgentPipelineRecord).where(
            AgentPipelineRecord.id == pipeline_id, AgentPipelineRecord.project_id == project_id).with_for_update())
        if row is None or row.version != expected_version:
            raise PipelineConflict("pipeline version changed or pipeline does not exist; inspect it before resuming")
        return row

    @staticmethod
    def _bump(row):
        row.version += 1
        row.updated_at = datetime.now(timezone.utc)

    @staticmethod
    def _entity(row):
        return AgentPipeline(**{name: getattr(row, name) for name in AgentPipeline.__dataclass_fields__})
