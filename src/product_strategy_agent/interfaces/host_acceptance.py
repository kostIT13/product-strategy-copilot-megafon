"""Host-observation composition, without auto-acceptance or installed-host probing."""

from product_strategy_agent.interfaces.host_profiles import host_profiles
from product_strategy_agent.adapters.persistence.files.host_acceptance_store import (
    FileHostAcceptanceStore,
)
from product_strategy_agent.adapters.persistence.files.host_evidence_reader import (
    FileHostEvidenceReader,
)
from product_strategy_agent.application.services.host_acceptance_service import (
    HostAcceptanceService,
)


def host_acceptance(root):
    return HostAcceptanceService(host_profiles(root), FileHostAcceptanceStore(root))


def evidence_reader(root):
    return FileHostEvidenceReader(root)
