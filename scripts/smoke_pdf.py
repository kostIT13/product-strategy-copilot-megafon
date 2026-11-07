"""Import a synthetic multipage PDF and verify persisted page citations."""

import json
from pathlib import Path
import subprocess
import tempfile
from uuid import uuid4

from pdf_fixture import make_pdf
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
    key = f"pdf-{uuid4().hex[:12]}"
    ProjectService(ps).create(key, "Synthetic PDF import")
    source_service = SourceService(ss)
    claim_service = ClaimService(cs, ps, ss)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "research.pdf"
        path.write_bytes(make_pdf(("First page.", "", "Export is available.")))
        command = ["psa-main", "document", "import", key, str(path), "--uri", "synthetic://pdf"]
        subprocess.run(command, check=True)
        subprocess.run(command, check=True)
        source = source_service.list_for_project(key)[0]
        require(source.revision.revision == 1, "repeat PDF import must be idempotent")
        require(source.revision.locator == "pages:1-3", "page range must be persisted")
        require(any("2" in note and "without" in note for note in source.revision.limitations), "blank page must be noted")
        claim_service.create(key, "PDF-FACT", "Export exists", "fact", "high",
            (EvidenceReference(source.id, 1, "page:3", "Export is available."),))
        path.write_bytes(make_pdf(("First page.", "", "Export is limited.")))
        subprocess.run(command, check=True)
        require(source_service.list_for_project(key)[0].revision.revision == 2, "PDF update must create revision 2")
        require(claim_service.list_for_project(key)[0].evidence[0].source_revision == 1, "PDF citation must remain pinned")
        require("Export is available." in source_service.get_revision(source.id, 1).revision.extracted_text,
                "original PDF text must remain accessible")
    print(json.dumps({"status": "passed", "project_key": key, "pages": 3, "revisions": 2}))


if __name__ == "__main__":
    main()
