"""Version-two readable projection; keep version-one builder frozen for replay."""

import json
from product_strategy_agent.domain.projects.claim_lifecycle import claim_impact
from product_strategy_agent.domain.projects.render_documents import render_documents_v1
from product_strategy_agent.domain.projects.source_lifecycle import source_statuses


def render_documents_v2(state, inputs, events):
    rows = lambda name: [
        json.loads(line) for line in inputs[name].splitlines() if line.strip()
    ]
    claims = rows("claims.jsonl")
    impact = claim_impact(
        claims,
        events,
        rows("options.jsonl"),
        rows("decision-log.jsonl"),
        rows("capabilities.jsonl"),
    )
    current = {
        **inputs,
        "claims.jsonl": "".join(
            json.dumps(row, ensure_ascii=False) + "\n"
            for row in claims
            if impact["statuses"][row["claim_id"]] == "active"
        ),
    }
    current["capabilities.jsonl"] = "".join(
        json.dumps(
            {**row, "status": "needs_review"}
            if row["capability_id"] in impact["affected_capability_ids"]
            else row,
            ensure_ascii=False,
        )
        + "\n"
        for row in rows("capabilities.jsonl")
    )
    statuses = source_statuses(rows("sources.jsonl"), events)
    if "withdrawn" in statuses.values():
        current["sources.jsonl"] = "".join(json.dumps({**row, "status": statuses[row["source_id"]]}, ensure_ascii=False) + "\n" for row in rows("sources.jsonl"))
    output = render_documents_v1(state, current)
    if "withdrawn" in statuses.values():
        note = "> Withdrawn sources are audit history, not current evidence: " + ", ".join(key for key, value in statuses.items() if value == "withdrawn") + ".\n\n"
        output = {name: note + text for name, text in output.items()}
    if impact["inactive_claim_ids"]:
        note = (
            "> Lifecycle: inactive claims are historical, not current evidence: "
            + ", ".join(impact["inactive_claim_ids"])
            + ".\n\n"
        )
        output = {name: note + text for name, text in output.items()}
        output["03_evidence.md"] += (
            "\n## Неактивные основания — аудит\n\n"
            + "\n".join(
                f"- {key}: {impact['statuses'][key]} (original record remains in claims.jsonl)"
                for key in impact["inactive_claim_ids"]
            )
            + "\n"
        )
        output["04_options.md"] += (
            "\nNeeds review (historical option refs): "
            + (", ".join(impact["affected_option_ids"]) or "none")
            + "\n"
        )
        output["decision.md"] += (
            "\nCurrent decision needs review: "
            + str(impact["current_decision_needs_review"]).lower()
            + ". No human decision was changed.\n"
        )
    return output
