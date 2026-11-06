"""ORM models registered with SQLAlchemy metadata."""

from product_strategy_agent.adapters.persistence.postgres.models.project import ProjectRecord
from product_strategy_agent.adapters.persistence.postgres.models.claim import (
    ClaimEvidenceRecord,
    ClaimRecord,
)
from product_strategy_agent.adapters.persistence.postgres.models.decision import (
    DecisionClaimRecord,
    DecisionOptionRecord,
    DecisionRecord,
)
from product_strategy_agent.adapters.persistence.postgres.models.option import (
    OptionClaimRecord,
    OptionRecord,
)
from product_strategy_agent.adapters.persistence.postgres.models.source import (
    SourceRecord,
    SourceRevisionRecord,
)

__all__ = [
    "ClaimEvidenceRecord",
    "ClaimRecord",
    "DecisionClaimRecord",
    "DecisionOptionRecord",
    "DecisionRecord",
    "OptionClaimRecord",
    "OptionRecord",
    "ProjectRecord",
    "SourceRecord",
    "SourceRevisionRecord",
]
