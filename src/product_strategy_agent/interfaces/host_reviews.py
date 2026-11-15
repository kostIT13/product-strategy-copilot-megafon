"""Review/disabled-preview composition without activation or installed-host probing."""

from product_strategy_agent.interfaces.host_acceptance import host_acceptance
from product_strategy_agent.interfaces.host_profiles import host_profiles
from product_strategy_agent.adapters.persistence.files.host_review_store import (
    FileHostReviewStore,
)
from product_strategy_agent.adapters.automation.codex_config_preview import (
    CodexConfigPreview,
)
from product_strategy_agent.application.services.host_review_service import (
    HostReviewService,
)
from product_strategy_agent.application.services.host_preview_service import (
    HostPreviewService,
)


def host_reviews(root):
    return HostReviewService(host_acceptance(root), FileHostReviewStore(root))


def host_preview(root):
    return HostPreviewService(
        host_profiles(root), host_reviews(root), CodexConfigPreview(root)
    )
