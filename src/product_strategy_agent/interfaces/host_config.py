"""Composition for explicit project-local disabled config lifecycle."""

from product_strategy_agent.interfaces.host_profiles import host_profiles
from product_strategy_agent.interfaces.host_reviews import host_preview
from product_strategy_agent.adapters.persistence.files.host_config_store import (
    FileHostConfigStore,
)
from product_strategy_agent.application.services.host_config_service import (
    HostConfigService,
)


def host_config(root):
    return HostConfigService(
        host_preview(root), host_profiles(root), FileHostConfigStore(root)
    )
