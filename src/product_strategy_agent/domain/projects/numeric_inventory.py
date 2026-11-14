"""Bounded raw-text digit inventory for human review; never a numeric proof."""

from dataclasses import dataclass
import json
import re
from product_strategy_agent.domain.projects.claim_lifecycle import fingerprint

DOCUMENTS = (
    "drafts/product-strategy.md",
    "drafts/communication-strategy.md",
    "drafts/validation-plan.md",
)
TOKEN = re.compile(r"[+-]?\d+(?:[.,]\d+)*")
MAX_TOKENS = 1000
MAX_PACKET = 512000


@dataclass(frozen=True)
class NumericInventorySnapshot:
    version: int
    documents: dict
    input_hashes: dict


def inventory_report(project_id, snapshot):
    documents, issues, total = [], [], 0
    for path in DOCUMENTS:
        text = snapshot.documents.get(path)
        rows = []
        if text is None:
            issues.append(path + ":document_missing")
        else:
            if len(text.encode("utf-8")) > 512000:
                raise ValueError("numeric inventory document exceeds 512000 bytes")
            offset = 0
            for line_number, line in enumerate(text.splitlines(keepends=True), 1):
                for match in TOKEN.finditer(line):
                    total += 1
                    if total > MAX_TOKENS or len(match[0]) > 160:
                        raise ValueError(
                            "numeric inventory exceeds 1000 tokens or 160 characters per token; no partial report"
                        )
                    start = max(0, match.start() - 60)
                    end = min(len(line), match.end() + 60)
                    rows.append(
                        {
                            "token": match[0],
                            "line": line_number,
                            "column_start": match.start(),
                            "column_end": match.end(),
                            "start": offset + match.start(),
                            "end": offset + match.end(),
                            "context": line[start:end],
                            "context_column_start": start,
                            "context_column_end": end,
                            "context_is_excerpt": start > 0 or end < len(line),
                            "review_status": "unassessed",
                        }
                    )
                offset += len(line)
        documents.append({"path": path, "present": text is not None, "tokens": rows})
    packet = {
        "format_version": "psa-numeric-inventory-v1",
        "project_id": project_id,
        "workflow_version": snapshot.version,
        "status": "blocked"
        if issues
        else "needs_human_review"
        if total
        else "no_digit_tokens",
        "scope": "raw_text_digit_tokens_in_three_authored_drafts",
        "issues": issues,
        "token_count": total,
        "documents": documents,
        "input_hashes": dict(snapshot.input_hashes),
        "digit_scan_complete": not issues,
        "numeric_coverage_verified": False,
        "numeric_alignment_verified": False,
        "evidence_verified": False,
        "arithmetic_verified": False,
        "workflow_approval_granted": False,
        "requires_human_review": True,
    }
    packet["review_hash"] = fingerprint(packet)
    if len(json.dumps(packet, ensure_ascii=False).encode("utf-8")) > MAX_PACKET:
        raise ValueError("numeric inventory packet exceeds 512000 bytes; no truncation")
    return packet
