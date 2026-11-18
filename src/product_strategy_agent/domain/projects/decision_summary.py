"""Follow-up signals for the last recorded decision and its case measurement plan."""

from datetime import datetime


def decision_summary(
    state, decisions, options, claims, events, impact, validation, now
):
    latest = decisions[-1] if decisions else None
    summary = {
        "project_id": state["project_id"],
        "workflow_version": impact["workflow_version"],
        "stage": state["status"],
        "workflow_next_action": state.get("next_action"),
        "decision": latest,
        "measurement": None,
        "attention": [],
    }
    attention = summary["attention"]
    if latest is None:
        attention.append({"code": "decision_not_recorded"})
        return summary

    claim_ids = set(latest.get("claim_ids", []))
    rejected = set(latest.get("rejected_alternatives", []))
    for option in options:
        option_id = option["option_id"]
        if option_id == latest.get("option_id") or rejected.intersection(
            (option_id, option.get("name"))
        ):
            claim_ids.update(option.get("claim_ids", []))
    inactive = {
        claim_id: impact["statuses"].get(claim_id, "missing")
        for claim_id in sorted(claim_ids)
        if impact["statuses"].get(claim_id) != "active"
    }
    if inactive:
        attention.append({"code": "decision_evidence_needs_review", "claims": inactive})
    sources = {
        source_id
        for claim in claims
        if claim["claim_id"] in claim_ids
        for source_id in claim.get("source_ids", [])
    }
    unavailable = {
        source_id: impact["source_statuses"].get(source_id, "missing")
        for source_id in sorted(sources)
        if impact["source_statuses"].get(source_id) != "extracted"
    }
    if unavailable:
        attention.append(
            {"code": "decision_sources_need_review", "sources": unavailable}
        )
    reviewed = {
        event.get("revision_event_id")
        for event in events
        if event.get("event_type") == "source_revision_reviewed"
    }
    pending = [
        {"revision_event_id": event["event_id"], "source_id": event["source_id"]}
        for event in events
        if event.get("event_type") == "source_revised"
        and event.get("source_id") in sources
        and event.get("event_id") not in reviewed
    ]
    if pending:
        attention.append(
            {"code": "source_revision_review_pending", "revisions": pending}
        )
    if not latest.get("revisit_when"):
        attention.append({"code": "revisit_condition_missing"})

    plan = validation["plan"]
    summary["measurement"] = {
        "relationship": "current_case_draft",
        "structural_status": validation["structural_status"],
        "issues": validation["issues"],
        "draft_sha256": validation["input_hashes"]["drafts/validation-plan.md"],
        "plan": plan,
    }
    if validation["structural_status"] != "complete":
        attention.append({"code": "measurement_plan_needs_review"})
    if plan and plan["baseline"]["status"] == "unknown":
        measurement = plan["baseline"]["measurement"]
        due = datetime.fromisoformat(measurement["due_at"].replace("Z", "+00:00"))
        attention.append(
            {
                "code": "baseline_measurement_overdue"
                if due <= now
                else "baseline_measurement_pending",
                "owner": measurement["owner"],
                "due_at": measurement["due_at"],
            }
        )
    return summary
