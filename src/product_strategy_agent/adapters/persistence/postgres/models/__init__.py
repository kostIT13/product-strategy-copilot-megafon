"""ORM models registered with SQLAlchemy metadata."""

from product_strategy_agent.adapters.persistence.postgres.models.project import ProjectRecord
from product_strategy_agent.adapters.persistence.postgres.models.claim import (
    ClaimEvidenceRecord,
    ClaimRecord,
)
from product_strategy_agent.adapters.persistence.postgres.models.source import (
    SourceRecord,
    SourceRevisionRecord,
)

__all__ = [
    "ClaimEvidenceRecord",
    "ClaimRecord",
    "ProjectRecord",
    "SourceRecord",
    "SourceRevisionRecord",
]
