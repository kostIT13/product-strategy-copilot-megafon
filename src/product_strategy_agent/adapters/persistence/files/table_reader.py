"""Use the verified imported table revision rather than the original file path."""

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
from product_strategy_agent.domain.projects.source_import import MAX_TEXT_BYTES
from product_strategy_agent.domain.projects.table_analysis import analyze_table


def table_report(projects_dir, project_id, request):
    with case_access(projects_dir, project_id) as case:
        snapshot = FileWorkflowStore(case.parent).inspect_claims(project_id)
        impact = impact_from_snapshot(project_id, snapshot)
        if impact["source_statuses"].get(request.source_id) != "extracted":
            raise ValueError("Choose a current imported source")
        source = next(
            row
            for row in rows(snapshot, "sources")
            if row["source_id"] == request.source_id
        )
        if source.get("document_format") == "xlsx" and source.get("kind") == "dataset":
            table_format = "xlsx"
        elif (
            source.get("kind") == "local_text"
            and PurePosixPath(source["uri_or_path"]).suffix.lower() == ".csv"
        ):
            table_format = "csv"
        else:
            raise ValueError("Table analysis supports imported CSV and XLSX sources")
        path = f"sources/{request.source_id}.txt"
        if source.get("extracted_text_path") != path:
            raise ValueError("Table source text path is not canonical")
        data = read_bounded(confined(case, path), MAX_TEXT_BYTES)
        digest = sha256(data).hexdigest()
        if digest != source.get("content_hash") or (
            request.expected_content_hash is not None
            and digest != request.expected_content_hash
        ):
            raise ValueError("Table source revision hash mismatch")
        return {
            **analyze_table(data.decode("utf-8"), table_format, request),
            "project_id": project_id,
            "workflow_version": impact["workflow_version"],
            "source_id": request.source_id,
            "content_hash": digest,
        }
