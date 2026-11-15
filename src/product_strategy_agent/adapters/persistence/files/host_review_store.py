"""Separate immutable review channel sharing host observations' OS lock and protocol."""

from product_strategy_agent.adapters.persistence.files.host_acceptance_store import (
    FileHostAcceptanceStore,
)
from product_strategy_agent.domain.automation.host_reviews import (
    encode,
    decode,
    validate_parent,
)


class FileHostReviewStore(FileHostAcceptanceStore):
    prefix = ".psa/host-acceptance/reviews/v1"
    encode = staticmethod(encode)

    def identifier(self, record):
        return record.command.operation_id

    def decode(self, raw, operation_id):
        record = decode(raw, operation_id)
        report = FileHostAcceptanceStore(self.root).read(
            record.command.report_operation_id
        )
        if report is None:
            raise ValueError("host review parent report is missing")
        validate_parent(record, report)
        return record
