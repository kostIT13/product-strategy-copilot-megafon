"""Typed authored measurement plan; no measured outcome or approval is inferred."""

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Annotated, Literal
from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    FiniteFloat,
    StringConstraints,
    ValidationError,
    field_validator,
    model_validator,
)
from product_strategy_agent.domain.projects.file_promises import check_claim

Text = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
]
ClaimID = Annotated[str, StringConstraints(pattern=r"^C-\d+$")]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Metric(Model):
    name: Text
    definition: Text
    unit: Text
    population: Text
    data_source: Text


class Measurement(Model):
    method: Text
    owner: Text
    due_at: AwareDatetime


class UnknownBaseline(Model):
    status: Literal["unknown"]
    value: None
    reason: Text
    measurement: Measurement


class ReportedBaseline(Model):
    status: Literal["reported"]
    value: FiniteFloat
    claim_id: ClaimID


class Observation(Model):
    start_condition: Text
    duration_days: int = Field(ge=1, le=3650)


class Guardrail(Model):
    name: Text
    definition: Text
    data_source: Text
    stop_rule: Text
    owner: Text


class ValidationPlan(Model):
    schema_version: Literal[1]
    hypothesis: Text
    expected_change: Text
    metric: Metric
    baseline: Annotated[
        UnknownBaseline | ReportedBaseline, Field(discriminator="status")
    ]
    comparison: Text
    success_criterion: Text
    observation: Observation
    guardrails: list[Guardrail] = Field(min_length=1, max_length=5)
    owner: Text
    decision_rule: Text

    @field_validator("schema_version", mode="before")
    @classmethod
    def exact_version(cls, value):
        if type(value) is not int or value != 1:
            raise ValueError("schema_version must be integer 1")
        return value

    @model_validator(mode="after")
    def distinct_guardrails(self):
        names = [row.name.casefold() for row in self.guardrails]
        if len(set(names)) != len(names):
            raise ValueError("guardrail names must be distinct")
        return self


@dataclass(frozen=True)
class ValidationSnapshot:
    version: int
    markdown: str | None
    input_hashes: dict


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError("non-finite JSON number")


def parse_plan(markdown):
    if markdown is None:
        raise ValueError("drafts/validation-plan.md is missing")
    text = re.sub(r"(?s)<!--.*?-->", "", markdown)
    blocks, body, fence, selected = [], [], None, False
    for line in text.splitlines():
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if marker:
            if fence is None:
                fence, selected, body = (
                    marker[1],
                    marker[2].strip() == "psa-validation-v1",
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
    if fence is not None or "<!--" in text:
        raise ValueError("unterminated validation plan fence/comment")
    if len(blocks) != 1:
        raise ValueError("include exactly one psa-validation-v1 JSON block")
    try:
        json.loads(
            blocks[0], object_pairs_hook=unique_object, parse_constant=reject_constant
        )
        return ValidationPlan.model_validate_json(blocks[0])
    except ValidationError as error:
        fields = [
            ".".join(map(str, item["loc"])) + ":" + item["type"]
            for item in error.errors(include_input=False)
        ]
        raise ValueError(
            "invalid validation plan fields: " + "; ".join(fields[:20])
        ) from None
    except (json.JSONDecodeError, RecursionError):
        raise ValueError("invalid validation plan JSON") from None


def plan_report(project_id, snapshot, plan=None, error=None, evidence=None):
    issues = [error] if error else []
    baseline_check = None
    hashes = dict(snapshot.input_hashes)
    if plan is not None and isinstance(plan.baseline, ReportedBaseline):
        baseline_check = check_claim(plan.baseline.claim_id, evidence)
        issues.extend("baseline:" + issue for issue in baseline_check["blockers"])
        hashes.update(
            {"evidence/" + key: value for key, value in evidence.input_hashes.items()}
        )
    packet = {
        "format_version": 1,
        "project_id": project_id,
        "workflow_version": snapshot.version,
        "scope": "validation_plan_v1",
        "structural_status": "incomplete" if issues else "complete",
        "issues": issues,
        "plan": plan.model_dump(mode="json") if plan else None,
        "baseline_evidence": baseline_check,
        "input_hashes": hashes,
        "requires_human_review": True,
        "semantic_alignment_verified": False,
        "numeric_alignment_verified": False,
        "observed_effect_verified": False,
        "publication_approved": False,
        "workflow_approval_granted": False,
    }
    raw = json.dumps(
        packet, ensure_ascii=False, sort_keys=True, allow_nan=False
    ).encode("utf-8")
    if len(raw) > 128000:
        raise ValueError("validation plan packet exceeds 128000 bytes")
    return {**packet, "review_hash": hashlib.sha256(raw).hexdigest()}
