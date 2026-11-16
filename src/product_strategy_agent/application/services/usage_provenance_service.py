"""Display declarations and source binding without upgrading measurement trust."""

from product_strategy_agent import __version__
from product_strategy_agent.application.ports.usage_provenance import (
    UsageProvenanceReader,
)
from product_strategy_agent.domain.automation.usage_provenance import project_usage
from product_strategy_agent.domain.projects.workspace import validate_workspace_id


class UsageProvenanceService:
    def __init__(self, reader: UsageProvenanceReader):
        self.reader = reader

    def inspect(self, project_id):
        validate_workspace_id(project_id)
        return {
            "format_version": "psa-usage-provenance-v1",
            "package_version": __version__,
            "project_id": project_id,
            **project_usage(self.reader.read(project_id)),
            "source_hash_computed": True,
            "source_authentication": "not_performed",
            "measurement_verified": False,
            "records_changed": False,
            "model_called_by_diagnostic": False,
            "workflow_approval_granted": False,
        }
