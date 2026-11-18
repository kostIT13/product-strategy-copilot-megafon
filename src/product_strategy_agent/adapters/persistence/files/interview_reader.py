"""Read only the explicitly selected, revision-bound local transcripts."""

from hashlib import sha256
from pathlib import PurePosixPath

from product_strategy_agent.adapters.persistence.files.case_access import case_access
from product_strategy_agent.adapters.persistence.files.paths import confined
from product_strategy_agent.adapters.persistence.files.source_search_repository import (
    read_bounded,
)
from product_strategy_agent.adapters.persistence.files.workflow_repository import (
    FileWorkflowStore,
)
from product_strategy_agent.application.services.claim_lifecycle_service import (
    impact_from_snapshot,
    rows,
)
from product_strategy_agent.domain.projects.interview_analysis import analyze_interviews
from product_strategy_agent.domain.projects.model_respondent import (
    SYNTHETIC_TRANSCRIPT_HEADER,
)


def interview_report(projects_dir, project_id, request):
    with case_access(projects_dir, project_id) as case:
        snapshot = FileWorkflowStore(case.parent).inspect_claims(project_id)
        impact = impact_from_snapshot(project_id, snapshot)
        by_id = {row["source_id"]: row for row in rows(snapshot, "sources")}
        sources = {}
        for ref in request.transcripts:
            if impact["source_statuses"].get(ref.source_id) != "extracted":
                raise ValueError("Choose current imported transcript sources")
            source = by_id[ref.source_id]
            plain_text = source.get("kind") == "local_text" and PurePosixPath(
                source["uri_or_path"]
            ).suffix.lower() in {".txt", ".md"}
            document = source.get("kind") == "uploaded_document" and source.get(
                "document_format"
            ) in {"docx", "pdf"}
            if not (plain_text or document):
                raise ValueError(
                    "Use a local TXT, Markdown, DOCX or PDF text transcript"
                )
            path = f"sources/{ref.source_id}.txt"
            if source.get("extracted_text_path") != path:
                raise ValueError("Transcript source path is not canonical")
            data = read_bounded(confined(case, path), 1024 * 1024)
            if (
                sha256(data).hexdigest() != ref.content_hash
                or source.get("content_hash") != ref.content_hash
            ):
                raise ValueError("Transcript revision hash mismatch")
            text = data.decode("utf-8")
            first_line = text.partition("\n")[0].removesuffix("\r")
            if (
                request.material_kind == "consented_interviews"
                and first_line == SYNTHETIC_TRANSCRIPT_HEADER
            ):
                raise ValueError(
                    "A generated synthetic transcript must use synthetic_dialogues"
                )
            sources[ref.source_id] = (source, text)
        return {
            "project_id": project_id,
            "workflow_version": impact["workflow_version"],
            **analyze_interviews(request, sources),
        }
