"""Traceability checks for authored strategy and external commitments."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

CLAIM_MARKER = re.compile(r"\[(C-\d+)\]")
CLASSIFICATION_MARKER = re.compile(r"\[(HYPOTHESIS|OPEN QUESTION)\]", re.IGNORECASE)
COMMITMENT_MARKER = re.compile(r"\[COMMITMENT:\s*(CAP-\d+)\]", re.IGNORECASE)


def _read_records(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"{path.name}:{line_number}: invalid JSON ({error.msg})") from error
        if not isinstance(item, dict):
            raise ValueError(f"{path.name}:{line_number}: each JSONL row must be an object")
        records.append(item)
    return records


def _paragraphs(path: Path) -> list[tuple[int, str, str]]:
    if not path.is_file():
        return []
    text = re.sub(
        r"(?s)<!--.*?-->",
        lambda match: "\n" * match.group(0).count("\n"),
        path.read_text(encoding="utf-8"),
    )
    result: list[tuple[int, str, str]] = []
    section = ""
    for match in re.finditer(r"(?m)(?:^\s*\n)*(\S[\s\S]*?)(?=\n\s*\n|\Z)", text):
        paragraph = " ".join(line.strip() for line in match.group(1).splitlines())
        folded = paragraph.casefold()
        if folded.startswith(("заполните ", "укажите ", "опишите ", "добавьте сюда", "todo", "tbd")):
            continue
        lines = [line.strip() for line in match.group(1).splitlines() if line.strip()]
        if lines and all(line.startswith("#") for line in lines):
            section = lines[-1].lstrip("# ").strip()
        elif paragraph:
            result.append((text.count("\n", 0, match.start(1)) + 1, paragraph, section))
    return result


def coverage_report(project_dir: Path) -> dict[str, Any]:
    """Check prose paragraphs for claim/classification markers and valid commitments."""
    errors: list[str] = []
    try:
        claims = _read_records(project_dir / "claims.jsonl")
        capabilities = _read_records(project_dir / "capabilities.jsonl")
    except ValueError as error:
        return {"ok": False, "checked_paragraphs": 0, "errors": [str(error)]}

    claim_ids = {item.get("claim_id") for item in claims if isinstance(item.get("claim_id"), str)}
    capability_map = {
        item.get("capability_id"): item for item in capabilities
        if isinstance(item.get("capability_id"), str)
    }
    checked = 0
    for name in ("product-strategy.md", "communication-strategy.md"):
        path = project_dir / "drafts" / name
        for line_number, paragraph, section in _paragraphs(path):
            checked += 1
            claims_found = CLAIM_MARKER.findall(paragraph)
            commitments = COMMITMENT_MARKER.findall(paragraph)
            classified = bool(CLASSIFICATION_MARKER.search(paragraph))
            if not claims_found and not commitments and not classified:
                errors.append(f"drafts/{name}:{line_number}: add [C-ID], [HYPOTHESIS], [OPEN QUESTION], or [COMMITMENT: CAP-ID]")
            if name == "communication-strategy.md" and "ключевое сообщение" in section.casefold():
                if not commitments and not classified:
                    errors.append(f"drafts/{name}:{line_number}: mark customer-facing copy as [COMMITMENT: CAP-ID] or explicitly as [HYPOTHESIS]/[OPEN QUESTION]")
            for claim_id in claims_found:
                if claim_id not in claim_ids:
                    errors.append(f"drafts/{name}:{line_number}: unknown claim marker [{claim_id}]")
            if "[COMMITMENT" in paragraph.upper() and not commitments:
                errors.append(f"drafts/{name}:{line_number}: commitment marker must name a capability, e.g. [COMMITMENT: CAP-001]")
            for capability_id in commitments:
                capability = capability_map.get(capability_id)
                if capability is None:
                    errors.append(f"drafts/{name}:{line_number}: unknown capability commitment [{capability_id}]")
                elif capability.get("status") != "available":
                    errors.append(f"drafts/{name}:{line_number}: commitment [{capability_id}] is not marked available")

    return {"ok": not errors, "checked_paragraphs": checked, "errors": errors}
