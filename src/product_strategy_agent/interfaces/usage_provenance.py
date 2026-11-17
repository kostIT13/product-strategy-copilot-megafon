"""Shared CLI/MCP composition for read-only usage provenance."""

from product_strategy_agent.adapters.persistence.files.usage_provenance_reader import (
    FileUsageProvenanceReader,
)
from product_strategy_agent.application.services.usage_provenance_service import (
    UsageProvenanceService,
)


def usage_provenance(projects_dir):
    return UsageProvenanceService(FileUsageProvenanceReader(projects_dir))
