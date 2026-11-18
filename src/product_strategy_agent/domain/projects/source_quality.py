"""Project current source assessment coverage for evidence review."""

from collections import Counter, defaultdict


METADATA_FIELDS = ("author", "publisher_or_owner", "published_at")


def _assessment_history(events):
    assessments, invalidations = {}, {}
    for event in events:
        source_id = event.get("source_id")
        if event.get("event_type") == "source_assessed":
            assessments[source_id] = event.get("assessment")
            invalidations.pop(source_id, None)
        elif event.get("event_type") in {
            "source_imported",
            "source_revised",
        } and event.get("assessment_invalidated"):
            invalidations[source_id] = event.get("event_id")
    return assessments, invalidations


def source_quality(sources, claims, events, impact):
    by_source = {row["source_id"]: row for row in sources}
    references = defaultdict(set)
    for claim in claims:
        claim_id = claim["claim_id"]
        if impact["statuses"].get(claim_id) == "active":
            for source_id in claim.get("source_ids", []):
                references[source_id].add(claim_id)
    assessments, invalidations = _assessment_history(events)
    items = []
    for source_id in sorted(
        set(by_source) | set(references), key=lambda key: (not references.get(key), key)
    ):
        row = by_source.get(source_id, {})
        lifecycle = impact["source_statuses"].get(source_id, "missing")
        assessment = row.get("source_assessment")
        content_hash = row.get("content_hash")
        invalidated_by = invalidations.get(source_id)
        if lifecycle != "extracted":
            status = "unavailable"
        elif invalidated_by and assessment is None:
            status = "invalidated"
        elif assessment is None:
            status = "inconsistent" if source_id in assessments else "unassessed"
        elif (
            not isinstance(assessment, dict)
            or assessment.get("source_id") != source_id
            or assessment.get("content_hash") != content_hash
            or assessment != assessments.get(source_id)
            or assessment.get("reliability")
            not in ("unassessed", "low", "medium", "high")
            or invalidated_by
            or any(
                row.get(key) != assessment.get(key)
                for key in (*METADATA_FIELDS, "reliability")
            )
        ):
            status = "inconsistent"
        else:
            status = "recorded"
        reliability = assessment.get("reliability") if status == "recorded" else None
        items.append(
            {
                "source_id": source_id,
                "source_status": lifecycle,
                "content_hash": content_hash,
                "active_claim_ids": sorted(references.get(source_id, ())),
                "assessment_status": status,
                "reliability": reliability,
                "unknown_metadata": [
                    key for key in METADATA_FIELDS if assessment.get(key) is None
                ]
                if status == "recorded"
                else None,
                "invalidated_by_revision_or_import": invalidated_by,
                "needs_attention": status != "recorded" or reliability == "unassessed",
            }
        )
    used = [item for item in items if item["active_claim_ids"]]
    return {
        "format_version": 1,
        "workflow_version": impact["workflow_version"],
        "scope": "registry_and_event_history",
        "sources": items,
        "assessment_status_counts": dict(
            Counter(item["assessment_status"] for item in items)
        ),
        "sources_used_by_active_claims": len(used),
        "used_sources_needing_attention": [
            item["source_id"] for item in used if item["needs_attention"]
        ],
        "approval_granted": False,
    }
