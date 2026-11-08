"""Coherent project-scoped preflight evidence; no writes and no model dependencies."""
from sqlalchemy import case, func, select, text
from product_strategy_agent.adapters.persistence.postgres.database import get_session_factory
from product_strategy_agent.adapters.persistence.postgres.models import (
    ProjectRecord, CapabilityRecord, CapabilityClaimRecord, ClaimRecord, ClaimEvidenceRecord, SourceRecord, SourceRevisionRecord)
from product_strategy_agent.domain.capabilities.entities import Capability
from product_strategy_agent.domain.capabilities.promises import PromiseEvidenceSnapshot, PromiseSource
from product_strategy_agent.domain.evidence.entities import Claim, EvidenceReference
from product_strategy_agent.domain.projects.errors import ProjectNotFound

MAX_SOURCE_CHARS = 200000
MAX_EVIDENCE_ROWS = 200


class PostgresPromiseEvidenceReader:
    def read(self, project_key, request):
        cap_ids = {support.capability_id for item in request.candidates for support in item.support}
        claim_ids = {claim_id for item in request.candidates for support in item.support for claim_id in support.claim_ids}
        with get_session_factory()() as session:
            session.connection(execution_options={"isolation_level": "REPEATABLE READ"})
            session.execute(text("SET TRANSACTION READ ONLY"))
            project = session.scalar(select(ProjectRecord).where(ProjectRecord.key == project_key))
            if project is None:
                raise ProjectNotFound("project was not found")
            caps = session.scalars(select(CapabilityRecord).where(CapabilityRecord.project_id == project.id,
                CapabilityRecord.id.in_(cap_ids)).order_by(CapabilityRecord.id)).all()
            links = session.execute(select(CapabilityClaimRecord.capability_id, CapabilityClaimRecord.claim_id)
                .join(CapabilityRecord, CapabilityRecord.id == CapabilityClaimRecord.capability_id)
                .where(CapabilityRecord.project_id == project.id, CapabilityRecord.id.in_(cap_ids),
                       CapabilityClaimRecord.claim_id.in_(claim_ids))).all()
            capabilities = tuple(Capability(row.id, row.project_id, row.key, row.name, row.description, row.status,
                tuple(sorted((link.claim_id for link in links if link.capability_id == row.id), key=str)), row.created_at) for row in caps)
            rows = session.scalars(select(ClaimRecord).where(ClaimRecord.project_id == project.id,
                ClaimRecord.id.in_(claim_ids)).order_by(ClaimRecord.id)).all()
            evidence_rows = session.execute(select(ClaimEvidenceRecord, SourceRevisionRecord.source_id, SourceRevisionRecord.revision)
                .join(ClaimRecord, ClaimRecord.id == ClaimEvidenceRecord.claim_id)
                .join(SourceRevisionRecord, SourceRevisionRecord.id == ClaimEvidenceRecord.source_revision_id)
                .where(ClaimRecord.project_id == project.id, ClaimRecord.id.in_(claim_ids))
                .order_by(ClaimEvidenceRecord.id).limit(MAX_EVIDENCE_ROWS + 1)).all()
            if len(evidence_rows) > MAX_EVIDENCE_ROWS:
                raise ValueError("too many promise evidence references; split the request")
            claims = tuple(Claim(row.id, row.project_id, row.key, row.text, row.claim_type, row.confidence,
                row.reasoning_note, row.decision_impact, row.status, row.created_at,
                tuple(EvidenceReference(source_id, revision, evidence.locator, evidence.quote)
                      for evidence, source_id, revision in evidence_rows if evidence.claim_id == row.id)) for row in rows)
            revision_ids = {row[0].source_revision_id for row in evidence_rows}
            source_ids = {row[1] for row in evidence_rows}
            latest = dict(session.execute(select(SourceRevisionRecord.source_id, func.max(SourceRevisionRecord.revision))
                .join(SourceRecord, SourceRecord.id == SourceRevisionRecord.source_id)
                .where(SourceRecord.project_id == project.id, SourceRecord.id.in_(source_ids))
                .group_by(SourceRevisionRecord.source_id)).all())
            # Oversized texts become an explicit blocker; never silently validate only a prefix.
            excerpts = case((func.length(SourceRevisionRecord.extracted_text) <= MAX_SOURCE_CHARS,
                             SourceRevisionRecord.extracted_text), else_=None).label("checked_text")
            sources = session.execute(select(SourceRecord, SourceRevisionRecord.id, SourceRevisionRecord.revision,
                SourceRevisionRecord.title, SourceRevisionRecord.locator, SourceRevisionRecord.content_hash, excerpts,
                SourceRevisionRecord.limitations, SourceRevisionRecord.provenance)
                .join(SourceRevisionRecord, SourceRevisionRecord.source_id == SourceRecord.id)
                .where(SourceRecord.project_id == project.id, SourceRevisionRecord.id.in_(revision_ids))
                .order_by(SourceRevisionRecord.id)).all()
            witnesses = tuple(PromiseSource(source.id, source.project_id, revision_id, revision, latest[source.id],
                source.uri, title, locator, digest, checked_text, source.status, source.reliability, tuple(limitations), provenance)
                for source, revision_id, revision, title, locator, digest, checked_text, limitations, provenance in sources)
            return PromiseEvidenceSnapshot(project.id, capabilities, claims, witnesses)
