"""Exercise XLSX import/revisions and cell citations via the real CLI."""

import json
from pathlib import Path
import subprocess
import tempfile
from uuid import uuid4

from xlsx_fixture import make_xlsx
from smoke_main import require
from product_strategy_agent.adapters.persistence.postgres.repositories.project_repository import PostgresProjectStore
from product_strategy_agent.adapters.persistence.postgres.repositories.source_repository import PostgresSourceStore
from product_strategy_agent.adapters.persistence.postgres.repositories.claim_repository import PostgresClaimStore
from product_strategy_agent.application.services.project_service import ProjectService
from product_strategy_agent.application.services.source_service import SourceService
from product_strategy_agent.application.services.claim_service import ClaimService
from product_strategy_agent.domain.evidence.entities import EvidenceReference


def main():
    ps, ss, cs = PostgresProjectStore(), PostgresSourceStore(), PostgresClaimStore()
    sources, claims = SourceService(ss), ClaimService(cs, ps, ss)
    key = f"xlsx-{uuid4().hex[:12]}"
    ProjectService(ps).create(key, "Synthetic XLSX import")
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "metrics.xlsx"
        path.write_bytes(make_xlsx())
        command = ["psa-main", "document", "import", key, str(path), "--uri", "synthetic://xlsx"]
        subprocess.run(command, check=True)
        subprocess.run(command, check=True)
        source = sources.list_for_project(key)[0]
        require(source.revision.revision == 1, "same XLSX must be idempotent")
        require(source.revision.locator == "workbook:visible-sheets", "workbook locator must persist")
        require("DO_NOT_IMPORT" not in source.revision.extracted_text, "hidden sheets must be excluded")
        require('[formula] = "=B2*100"' in source.revision.extracted_text, "formula must remain unevaluated")
        claims.create(key, "CELL-FACT", "Retention was 0.75", "fact", "high", (
            EvidenceReference(source.id, 1, "sheet:'Metrics'!B2", "'Metrics'!B2 [number] = 0.75"),))
        path.write_bytes(make_xlsx(0.8))
        subprocess.run(command, check=True)
        require(sources.list_for_project(key)[0].revision.revision == 2, "changed cells must create revision 2")
        require(claims.list_for_project(key)[0].evidence[0].source_revision == 1, "cell citation must remain pinned")
    print(json.dumps({"status": "passed", "project_key": key, "revisions": 2}))


if __name__ == "__main__":
    main()
