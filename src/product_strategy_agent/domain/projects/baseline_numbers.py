"""Check an explicitly selected numeric literal; never infer semantic alignment."""

from decimal import Decimal
import hashlib
import json
import re
from typing import Annotated, Literal
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    model_validator,
    field_validator,
)
from product_strategy_agent.domain.projects.validation_plan import (
    unique_object,
    reject_constant,
)
from product_strategy_agent.domain.projects.file_promises import check_claim


class Span(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    start: int = Field(ge=0, le=500)
    end: int = Field(ge=1, le=500)

    @model_validator(mode="after")
    def ordered(self):
        if self.start >= self.end:
            raise ValueError("span must be nonempty and ordered")
        return self


class NumberAnchor(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal[1]
    claim_id: Annotated[str, StringConstraints(pattern=r"^C-\d+$")]
    source_id: Annotated[str, StringConstraints(pattern=r"^S-[A-Za-z0-9_-]{1,120}$")]
    locator: Annotated[str, StringConstraints(min_length=1, max_length=200)]
    quote: Annotated[str, StringConstraints(min_length=1, max_length=500)]
    decimal_separator: Literal[".", ","] = "."
    number_span: Span
    unit_span: Span

    @field_validator("schema_version", mode="before")
    @classmethod
    def exact_version(cls, value):
        if type(value) is not int or value != 1:
            raise ValueError("schema_version must be integer 1")
        return value

    @model_validator(mode="after")
    def spans(self):
        if type(self.schema_version) is not int:
            raise ValueError("schema_version must be integer 1")
        if max(self.number_span.end, self.unit_span.end) > len(self.quote):
            raise ValueError("span is outside quote")
        if max(self.number_span.start, self.unit_span.start) < min(
            self.number_span.end, self.unit_span.end
        ):
            raise ValueError("number and unit spans must not overlap")
        return self


def parse_anchor(markdown):
    text = re.sub(r"(?s)<!--.*?-->", "", markdown)
    blocks, body, fence, selected = [], [], None, False
    for line in text.splitlines():
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if marker:
            if fence is None:
                fence, selected, body = (
                    marker[1],
                    marker[2].strip() == "psa-baseline-number-v1",
                    [],
                )
            elif (
                marker[1][0] == fence[0]
                and len(marker[1]) >= len(fence)
                and not marker[2].strip()
            ):
                if selected:
                    blocks.append("\n".join(body))
                fence, selected = None, False
            elif selected:
                body.append(line)
        elif selected:
            body.append(line)
    if fence is not None or "<!--" in text or len(blocks) != 1:
        raise ValueError("include exactly one closed psa-baseline-number-v1 JSON block")
    try:
        body = json.loads(
            blocks[0], object_pairs_hook=unique_object, parse_constant=reject_constant
        )
        return NumberAnchor.model_validate(body)
    except ValidationError:
        raise ValueError("invalid numeric anchor fields/spans") from None
    except (json.JSONDecodeError, RecursionError):
        raise ValueError("invalid numeric anchor JSON") from None


def literal_number(quote, span, decimal_separator="."):
    token = quote[span.start : span.end]
    if decimal_separator not in {".", ","} or not re.fullmatch(
        r"[+-]?(?:0|[1-9][0-9]*)(?:" + re.escape(decimal_separator) + r"[0-9]+)?", token
    ):
        raise ValueError("unsupported numeric literal; use an ungrouped decimal")
    before = quote[span.start - 1] if span.start else ""
    after = quote[span.end : span.end + 1]
    if (before and (before.isalnum() or before in "_.,+-/")) or (
        after and (after.isalnum() or after in "_+-/")
    ):
        raise ValueError("numeric span selects only part of a token")
    if after in {".", ","} and quote[span.end + 1 : span.end + 2].isdigit():
        raise ValueError("numeric span selects only part of a decimal")
    if re.search(r"[0-9][ \u00a0\u202f]+$", quote[: span.start]) or re.match(
        r"[ \u00a0\u202f]+[0-9]", quote[span.end :]
    ):
        raise ValueError("ambiguous grouped or adjacent numeric literals")
    return Decimal(token.replace(",", "."))


def numbers_report(project_id, snapshot, plan=None, evidence=None, error=None):
    issues = [error] if error else []
    proof, anchor, number_match, unit_match = None, None, False, False
    applicable = plan is not None and plan.baseline.status == "reported"
    hashes = dict(snapshot.input_hashes)
    if applicable:
        proof = check_claim(plan.baseline.claim_id, evidence)
        issues.extend("baseline:" + item for item in proof["blockers"])
        hashes.update(
            {"evidence/" + key: value for key, value in evidence.input_hashes.items()}
        )
        try:
            anchor = parse_anchor(snapshot.markdown)
            if anchor.claim_id != plan.baseline.claim_id:
                issues.append("anchor_claim_mismatch")
            if not any(
                row["source_id"] == anchor.source_id
                and row["locator"] == anchor.locator
                and row["quote"] == anchor.quote
                for row in proof["evidence"]
            ):
                issues.append("anchor_does_not_match_recorded_citation")
            number_match = literal_number(
                anchor.quote, anchor.number_span, anchor.decimal_separator
            ) == Decimal(str(plan.baseline.value))
            unit_match = (
                anchor.quote[anchor.unit_span.start : anchor.unit_span.end]
                == plan.metric.unit
            )
            if not number_match:
                issues.append("baseline_numeric_literal_mismatch")
            if not unit_match:
                issues.append("metric_unit_literal_mismatch")
        except ValueError as failure:
            issues.append(str(failure))
    status = (
        "blocked" if issues else "literal_match" if applicable else "not_applicable"
    )
    packet = {
        "format_version": "psa-baseline-number-check-v1",
        "project_id": project_id,
        "workflow_version": snapshot.version,
        "status": status,
        "issues": issues,
        "scope": "one_author_selected_reported_baseline_literal_and_unit",
        "baseline_value": plan.baseline.value if applicable else None,
        "metric_unit": plan.metric.unit if plan else None,
        "anchor": anchor.model_dump(mode="json") if anchor else None,
        "baseline_evidence": proof,
        "numeric_literal_matches": bool(not issues and number_match),
        "unit_literal_matches": bool(not issues and unit_match),
        "input_hashes": hashes,
        "semantic_alignment_verified": False,
        "numeric_alignment_verified": False,
        "source_truthfulness_verified": False,
        "experiment_approved": False,
        "workflow_approval_granted": False,
        "requires_human_review": True,
    }
    raw = json.dumps(
        packet, ensure_ascii=False, sort_keys=True, allow_nan=False
    ).encode("utf-8")
    if len(raw) > 128000:
        raise ValueError("numeric baseline packet exceeds 128000 bytes")
    return {**packet, "review_hash": hashlib.sha256(raw).hexdigest()}
