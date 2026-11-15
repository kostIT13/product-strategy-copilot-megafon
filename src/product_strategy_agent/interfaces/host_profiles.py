"""Host planning composition and strict request boundary."""

import json
from pydantic import ValidationError
from product_strategy_agent.adapters.persistence.files.host_catalog_reader import (
    FileHostCatalogReader,
)
from product_strategy_agent.application.services.host_profile_service import (
    HostProfileService,
)
from product_strategy_agent.domain.automation.handoffs import strict_json
from product_strategy_agent.domain.automation.host_profiles import PlanHost


def host_profiles(root):
    return HostProfileService(FileHostCatalogReader(root))


def parse_host_plan(raw):
    if len(raw) > 64000:
        raise ValueError("host plan request exceeds 64000 bytes")
    try:
        return PlanHost.model_validate_json(
            json.dumps(strict_json(raw), ensure_ascii=False, allow_nan=False)
        )
    except ValidationError:
        raise ValueError("invalid host plan request schema") from None
