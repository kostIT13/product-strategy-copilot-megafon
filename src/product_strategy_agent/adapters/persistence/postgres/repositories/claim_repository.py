"""SQLAlchemy implementation of the claim persistence port."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from product_strategy_agent.adapters.persistence.postgres.database import get_session_factory
from product_strategy_agent.adapters.persistence.postgres.models import (
    ClaimEvidenceRecord,
    ClaimRecord,
    ProjectRecord,
    SourceRecord,
    SourceRevisionRecord,
)
from product_strategy_agent.domain.evidence.entities import (
    Claim,
    ClaimReferenceInfo,
    EvidenceReference,
)
from product_strategy_agent.domain.evidence.errors import ClaimAlreadyExists, InvalidClaim
from product_strategy_agent.domain.projects.errors import ProjectNotFound


class PostgresClaimStore:
    def get_reference_info(self, claim_id: UUID) -> ClaimReferenceInfo | None:
        with get_session_factory()() as session:
            record = session.get(ClaimRecord, claim_id)
            if record is None:
                return None
            return ClaimReferenceInfo(record.project_id, record.claim_type, record.status)

    def create(self, claim: Claim) -> Claim:
        sessions = get_session_factory()
        try:
            with sessions.begin() as session:
                record = ClaimRecord(
                    id=claim.id,
                    project_id=claim.project_id,
                    key=claim.key,
                    text=claim.text,
                    claim_type=claim.claim_type,
                    confidence=claim.confidence,
                    reasoning_note=claim.reasoning_note,
                    decision_impact=claim.decision_impact,
                    status=claim.status,
                    created_at=claim.created_at,
                )
                session.add(record)
                session.flush()
                for evidence in claim.evidence:
                    revision = session.scalar(
                        select(SourceRevisionRecord)
                        .join(SourceRecord, SourceRecord.id == SourceRevisionRecord.source_id)
                        .where(
                            SourceRecord.project_id == claim.project_id,
                            SourceRecord.id == evidence.source_id,
                            SourceRevisionRecord.revision == evidence.source_revision,
                        )
                    )
                    if revision is None:
                        raise InvalidClaim("evidence references a missing source revision or another project")
                    session.add(
                        ClaimEvidenceRecord(
                            claim_id=claim.id,
                            source_revision_id=revision.id,
                            locator=evidence.locator,
                            quote=evidence.quote,
                        )
                    )
                session.flush()
                return claim
        except IntegrityError as exc:
            if getattr(exc.orig, "sqlstate", None) == "23505":
                raise ClaimAlreadyExists(f"claim key '{claim.key}' already exists in this project") from exc
            raise

    def list_for_project(self, project_key: str) -> list[Claim]:
        with get_session_factory()() as session:
            project = session.scalar(select(ProjectRecord).where(ProjectRecord.key == project_key))
            if project is None:
                raise ProjectNotFound(f"project '{project_key}' was not found")
            records = session.scalars(
                select(ClaimRecord)
                .where(ClaimRecord.project_id == project.id)
                .order_by(ClaimRecord.created_at, ClaimRecord.key)
            ).all()
            if not records:
                return []
            evidence_rows = session.execute(
                select(ClaimEvidenceRecord, SourceRevisionRecord)
                .join(
                    SourceRevisionRecord,
                    SourceRevisionRecord.id == ClaimEvidenceRecord.source_revision_id,
                )
                .where(ClaimEvidenceRecord.claim_id.in_([record.id for record in records]))
            ).all()
            evidence_by_claim: dict[object, list[EvidenceReference]] = {}
            for evidence_record, revision_record in evidence_rows:
                evidence_by_claim.setdefault(evidence_record.claim_id, []).append(
                    EvidenceReference(
                        source_id=revision_record.source_id,
                        source_revision=revision_record.revision,
                        locator=evidence_record.locator,
                        quote=evidence_record.quote,
                    )
                )
            return [
                Claim(
                    id=record.id,
                    project_id=record.project_id,
                    key=record.key,
                    text=record.text,
                    claim_type=record.claim_type,
                    confidence=record.confidence,
                    reasoning_note=record.reasoning_note,
                    decision_impact=record.decision_impact,
                    status=record.status,
                    created_at=record.created_at,
                    evidence=tuple(evidence_by_claim.get(record.id, [])),
                )
                for record in records
            ]
