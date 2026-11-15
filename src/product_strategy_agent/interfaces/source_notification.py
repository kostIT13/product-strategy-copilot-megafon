"""Composition root for an explicitly requested local revision notice."""

from product_strategy_agent.application.services.source_notification_service import (
    SourceNotificationService,
)
from product_strategy_agent.adapters.persistence.files.source_notification_reader import (
    FileSourceNotificationReader,
)


def source_notification(root):
    return SourceNotificationService(FileSourceNotificationReader(root))
