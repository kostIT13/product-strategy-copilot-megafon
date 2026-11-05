"""Structural validation and local citation verification."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from product_strategy_agent.ledger import CLAIM_TYPES, CONFIDENCE_LEVELS
from product_strategy_agent.workflow import MODE_PROFILES

REGISTRIES = {
    "sources.jsonl": ("source_id", "S"),
    "claims.jsonl": ("claim_id", "C"),
    "gaps.jsonl": ("gap_id", "G"),
    "options.jsonl": ("option_id", "O"),
    "decision-log.jsonl": ("decision_id", "D"),
    "usage.jsonl": (None, None),
}
STAGES = {"intake", "research_plan", "source_collection", "evidence_review", "options", "strategy", "validation", "completed", "blocked"}
STAGE_STATUSES = {"not_started", "in_progress", "needs_review", "done", "blocked"}


def _read_jsonl(path: Path, errors: list[str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not path.is_file():
        errors.append(f"Missing registry: {path.name}")
        return records
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
            if not isinstance(record, dict):
                errors.append(f"{path.name}:{line_number}: each JSONL row must be an object")
            else:
                records.append(record)
        except json.JSONDecodeError as error:
            errors.append(f"{path.name}:{line_number}: invalid JSON ({error.msg})")
    return records


def _safe_extracted_path(project_dir: Path, raw_path: str) -> Path | None:
    candidate = (project_dir / raw_path).resolve()
    source_root = (project_dir / "sources").resolve()
    try:
        candidate.relative_to(source_root)
    except ValueError:
        return None
    return candidate


def validate_project(project_dir: Path) -> list[str]:
    errors: list[str] = []
    state_path = project_dir / "state.json"
    if not state_path.is_file():
        return ["Missing state.json; not a project workspace"]
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return [f"state.json: invalid JSON ({error.msg})"]
    if not isinstance(state, dict):
        return ["state.json: top-level value must be an object"]
    if state.get("schema_version") != 1:
        errors.append("state.json: schema_version must be 1")
    mode = state.get("mode", "decision_grade")
    if not isinstance(mode, str) or mode not in MODE_PROFILES:
        errors.append("state.json: mode must be quick_scan, decision_grade, or deep_research")
    if not isinstance(state.get("status"), str) or state.get("status") not in STAGES:
        errors.append(f"state.json: unknown status {state.get('status')!r}")
    stages = state.get("stages")
    if not isinstance(stages, dict):
        errors.append("state.json: stages must be an object")
    else:
        for name, status in stages.items():
            if name not in STAGES or not isinstance(status, str) or status not in STAGE_STATUSES:
                errors.append(f"state.json: invalid stage/status {name!r}={status!r}")
    for name in ("01_brief.md", "sources/"):
        if not (project_dir / name).exists():
            errors.append(f"Missing required artifact: {name}")

    loaded: dict[str, list[dict[str, Any]]] = {}
    for filename, (id_field, prefix) in REGISTRIES.items():
        records = _read_jsonl(project_dir / filename, errors)
        loaded[filename] = records
        if id_field:
            seen: set[str] = set()
            id_pattern = rf"{prefix}-[A-F0-9]{{12}}" if prefix == "S" else rf"{prefix}-\d+"
            for line_number, record in enumerate(records, 1):
                record_id = record.get(id_field)
                if not isinstance(record_id, str) or not re.fullmatch(id_pattern, record_id):
                    errors.append(f"{filename}:{line_number}: invalid {id_field}")
                else:
                    if record_id in seen:
                        errors.append(f"{filename}:{line_number}: duplicate {id_field} {record_id}")
                    seen.add(record_id)
                if record.get("schema_version") != 1:
                    errors.append(f"{filename}:{line_number}: schema_version must be 1")

    sources = {record["source_id"]: record for record in loaded["sources.jsonl"] if isinstance(record.get("source_id"), str)}
    claims = {record["claim_id"]: record for record in loaded["claims.jsonl"] if isinstance(record.get("claim_id"), str)}
    options = {record["option_id"]: record for record in loaded["options.jsonl"] if isinstance(record.get("option_id"), str)}
    for line_number, claim in enumerate(loaded["claims.jsonl"], 1):
        if not isinstance(claim.get("text"), str) or not claim["text"].strip():
            errors.append(f"claims.jsonl:{line_number}: text is required")
        if not isinstance(claim.get("type"), str) or claim.get("type") not in CLAIM_TYPES:
            errors.append(f"claims.jsonl:{line_number}: invalid type")
        if not isinstance(claim.get("confidence"), str) or claim.get("confidence") not in CONFIDENCE_LEVELS:
            errors.append(f"claims.jsonl:{line_number}: invalid confidence")
        source_ids, locators, quotes = (claim.get(key, []) for key in ("source_ids", "source_locators", "quotes"))
        if not all(isinstance(value, list) for value in (source_ids, locators, quotes)):
            errors.append(f"claims.jsonl:{line_number}: source_ids, source_locators, and quotes must be arrays")
            continue
        if len(source_ids) != len(locators):
            errors.append(f"claims.jsonl:{line_number}: source_ids and source_locators counts differ")
        if claim.get("type") == "fact" and (not source_ids or len(source_ids) != len(quotes)):
            errors.append(f"claims.jsonl:{line_number}: fact needs a source, locator, and exact quote for each citation")
        if quotes and len(source_ids) != len(quotes):
            errors.append(f"claims.jsonl:{line_number}: source_ids and quotes counts differ")
        for source_id in source_ids:
            if not isinstance(source_id, str) or source_id not in sources:
                errors.append(f"claims.jsonl:{line_number}: unknown source {source_id}")
        for ref in claim.get("contradicts", []) or []:
            if not isinstance(ref, str) or ref not in claims:
                errors.append(f"claims.jsonl:{line_number}: unknown contradicted claim {ref}")
        supersedes = claim.get("supersedes")
        if supersedes and (not isinstance(supersedes, str) or supersedes not in claims):
            errors.append(f"claims.jsonl:{line_number}: unknown superseded claim {supersedes}")

    for line_number, decision in enumerate(loaded["decision-log.jsonl"], 1):
        for claim_id in decision.get("claim_ids", []) or []:
            if not isinstance(claim_id, str) or claim_id not in claims:
                errors.append(f"decision-log.jsonl:{line_number}: unknown claim {claim_id}")
        if not decision.get("chosen_option") or not decision.get("owner"):
            errors.append(f"decision-log.jsonl:{line_number}: chosen_option and owner are required")
        option_id = decision.get("option_id")
        if option_id and (not isinstance(option_id, str) or option_id not in options):
            errors.append(f"decision-log.jsonl:{line_number}: unknown option {option_id}")

    for line_number, option in enumerate(loaded["options.jsonl"], 1):
        if not option.get("name") or not option.get("description"):
            errors.append(f"options.jsonl:{line_number}: name and description are required")
        if not isinstance(option.get("role"), str) or option.get("role") not in {"status_quo", "stop", "change"}:
            errors.append(f"options.jsonl:{line_number}: invalid role")
        for claim_id in option.get("claim_ids", []) or []:
            if not isinstance(claim_id, str) or claim_id not in claims:
                errors.append(f"options.jsonl:{line_number}: unknown claim {claim_id}")
    if loaded["options.jsonl"]:
        roles = {option.get("role") for option in loaded["options.jsonl"]}
        if len(loaded["options.jsonl"]) < 3 or not {"status_quo", "stop", "change"}.issubset(roles):
            errors.append("options.jsonl: add at least three options, including status_quo, stop, and change")

    for line_number, source in enumerate(loaded["sources.jsonl"], 1):
        raw_path = source.get("extracted_text_path")
        if not isinstance(raw_path, str) or not raw_path:
            errors.append(f"sources.jsonl:{line_number}: extracted_text_path is required")
        elif _safe_extracted_path(project_dir, raw_path) is None:
            errors.append(f"sources.jsonl:{line_number}: extracted_text_path must stay inside sources/")

    usage_ids: set[str] = set()
    for line_number, event in enumerate(loaded["usage.jsonl"], 1):
        if event.get("schema_version") != 1:
            errors.append(f"usage.jsonl:{line_number}: schema_version must be 1")
        event_id = event.get("event_id")
        if not isinstance(event_id, str) or not re.fullmatch(r"USE-\d+", event_id):
            errors.append(f"usage.jsonl:{line_number}: invalid event_id")
        elif event_id in usage_ids:
            errors.append(f"usage.jsonl:{line_number}: duplicate event_id {event_id}")
        else:
            usage_ids.add(event_id)
        for field in ("provider", "model", "operation"):
            if not isinstance(event.get(field), str) or not event[field].strip():
                errors.append(f"usage.jsonl:{line_number}: {field} is required")
        if not isinstance(event.get("stage"), str) or event.get("stage") not in STAGES - {"blocked", "completed"}:
            errors.append(f"usage.jsonl:{line_number}: invalid stage")
        cost = event.get("cost")
        if not isinstance(cost, dict) or cost.get("certainty") not in {"measured", "estimated", "unknown"}:
            errors.append(f"usage.jsonl:{line_number}: invalid cost object/certainty")
        elif cost.get("certainty") == "unknown" and cost.get("amount") is not None:
            errors.append(f"usage.jsonl:{line_number}: unknown cost certainty cannot have an amount")
        elif cost.get("certainty") != "unknown" and not isinstance(cost.get("amount"), str):
            errors.append(f"usage.jsonl:{line_number}: measured/estimated cost needs a decimal string amount")
        elif cost.get("certainty") != "unknown" and not re.fullmatch(r"\d+(?:\.\d+)?", cost["amount"]):
            errors.append(f"usage.jsonl:{line_number}: cost amount must be a non-negative decimal string")
        if isinstance(cost, dict) and (not isinstance(cost.get("currency"), str) or not re.fullmatch(r"[A-Z]{3}", cost["currency"])):
            errors.append(f"usage.jsonl:{line_number}: currency must be a three-letter uppercase code")
        for field in ("input_tokens", "output_tokens", "duration_ms", "retry_count"):
            value = event.get(field)
            if value is not None and (type(value) is not int or value < 0):
                errors.append(f"usage.jsonl:{line_number}: {field} must be a non-negative integer or null")
        if event.get("request_content_logged") is not False:
            errors.append(f"usage.jsonl:{line_number}: request_content_logged must be false")
    return errors


def _normalize_quote(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def verify_project(project_dir: Path) -> tuple[list[str], list[str]]:
    errors = validate_project(project_dir)
    warnings: list[str] = []
    if errors:
        return errors, warnings
    registry_errors: list[str] = []
    sources = _read_jsonl(project_dir / "sources.jsonl", registry_errors)
    source_texts: dict[str, str] = {}
    for source in sources:
        source_id = source["source_id"]
        path = _safe_extracted_path(project_dir, source["extracted_text_path"])
        if path is None:
            errors.append(f"{source_id}: extracted text path escapes sources/")
            continue
        if not path.is_file():
            errors.append(f"{source_id}: extracted text is missing")
            continue
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != source.get("content_hash"):
            errors.append(f"{source_id}: content hash mismatch")
            continue
        source_texts[source_id] = data.decode("utf-8", errors="replace")

    for claim in _read_jsonl(project_dir / "claims.jsonl", registry_errors):
        claim_id = claim.get("claim_id", "<unknown>")
        source_ids = claim.get("source_ids", [])
        locators = claim.get("source_locators", [])
        quotes = claim.get("quotes", [])
        for index, source_id in enumerate(source_ids):
            if index >= len(locators) or index >= len(quotes):
                continue
            if source_id not in source_texts:
                warnings.append(f"{claim_id}: citation {source_id} is unverifiable because source text is unavailable")
                continue
            locator, quote = locators[index], quotes[index]
            if not isinstance(locator, str) or not isinstance(quote, str) or not quote.strip():
                warnings.append(f"{claim_id}: citation {source_id} has no usable locator or quote")
                continue
            text = source_texts[source_id]
            range_match = re.fullmatch(r"lines:(\d+)-(\d+)", locator.strip(), re.IGNORECASE)
            match = re.fullmatch(r"(?:paragraph|p|line):(\d+)", locator.strip(), re.IGNORECASE)
            if range_match:
                start, end = (int(value) for value in range_match.groups())
                lines = text.splitlines()
                if start < 1 or end < start or end > len(lines):
                    errors.append(f"{claim_id}: locator {locator!r} is outside source {source_id}")
                    continue
                excerpt = "\n".join(lines[start - 1:end])
            elif match:
                position = int(match.group(1))
                lines = text.splitlines() if locator.lower().startswith("line:") else [line for line in text.splitlines() if line.strip()]
                if position < 1 or position > len(lines):
                    errors.append(f"{claim_id}: locator {locator!r} is outside source {source_id}")
                    continue
                excerpt = lines[position - 1]
            else:
                warnings.append(f"{claim_id}: locator {locator!r} is not supported for plain text verification")
                continue
            if _normalize_quote(quote) not in _normalize_quote(excerpt):
                errors.append(f"{claim_id}: quote does not match {source_id} at {locator}")
    errors.extend(registry_errors)
    return errors, warnings
