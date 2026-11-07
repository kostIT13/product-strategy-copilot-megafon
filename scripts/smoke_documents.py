"""Import HTML through the real CLI, check revisions, and cite extracted text."""

import json
from pathlib import Path
import subprocess
import tempfile
from uuid import uuid4

from product_strategy_agent.adapters.persistence.postgres.repositories.project_repository import PostgresProjectStore
from product_strategy_agent.adapters.persistence.postgres.repositories.source_repository import PostgresSourceStore
from product_strategy_agent.adapters.persistence.postgres.repositories.claim_repository import PostgresClaimStore
from product_strategy_agent.application.services.project_service import ProjectService
from product_strategy_agent.application.services.source_service import SourceService
from product_strategy_agent.application.services.claim_service import ClaimService
from product_strategy_agent.domain.evidence.entities import EvidenceReference
from smoke_main import require


def main():
    projects, sources, claims = PostgresProjectStore(), PostgresSourceStore(), PostgresClaimStore()
    key = f"documents-{uuid4().hex[:12]}"
    ProjectService(projects).create(key, "Synthetic document import")
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "page.html"
        path.write_text('<title>Export</title><p>Export is available.</p><script>hidden</script>', encoding="utf-8")
        command = ["psa-main", "document", "import", key, str(path), "--uri", "synthetic://document"]
        subprocess.run(command, check=True)
        subprocess.run(command, check=True)
        source = SourceService(sources).list_for_project(key)[0]
        require(source.revision.revision == 1, "unchanged imports must stay at revision 1")
        require(source.revision.title == "Export", "HTML title must be preserved")
        require("hidden" not in source.revision.extracted_text, "script content must be removed")
        ClaimService(claims, projects, sources).create(key, "FACT", "Export exists", "fact", "high",
            (EvidenceReference(source.id, 1, "paragraph:1", "Export is available."),))
        path.write_text('<p>Export is available with limits.</p>', encoding="utf-8")
        subprocess.run(command, check=True)
        source = SourceService(sources).list_for_project(key)[0]
        require(source.revision.revision == 2, "changed document must create revision 2")
        require(ClaimService(claims, projects, sources).list_for_project(key)[0].evidence[0].source_revision == 1,
                "claim must remain pinned to the imported revision")
    print(json.dumps({"status": "passed", "project_key": key, "revisions": 2}))


if __name__ == "__main__":
    main()
