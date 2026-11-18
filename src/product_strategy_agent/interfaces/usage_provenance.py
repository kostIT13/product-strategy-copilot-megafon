"""Shared CLI/MCP composition for read-only usage provenance."""

from product_strategy_agent.adapters.persistence.files.usage_provenance_reader import (
    FileUsageProvenanceReader,
)
from product_strategy_agent.application.services.usage_provenance_service import (
    UsageProvenanceService,
)
from product_strategy_agent.domain.projects.case_effort import case_effort


def usage_provenance(projects_dir):
    return UsageProvenanceService(FileUsageProvenanceReader(projects_dir))


def usage_effort(projects_dir, project_id):
    return {
        "project_id": project_id,
        **case_effort(FileUsageProvenanceReader(projects_dir).read(project_id)),
    }
