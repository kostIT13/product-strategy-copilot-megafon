"""Pure preparation payloads, never execution permissions, answers or scores."""

import hashlib
import json
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Material(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    key: str = Field(pattern=r"^[a-z][a-z0-9-]{0,31}$")
    text: str = Field(min_length=20, max_length=4000)


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    schema_version: int = Field(ge=1, le=1)
    synthetic: bool
    scenario_id: str = Field(pattern=r"^[a-z][a-z0-9-]{0,63}$")
    brief: str = Field(min_length=30, max_length=4000)
    materials: tuple[Material, ...] = Field(min_length=2, max_length=5)

    @model_validator(mode="after")
    def own_synthetic_inputs(self):
        if self.synthetic is not True or len(
            {item.key for item in self.materials}
        ) != len(self.materials):
            raise ValueError("expected synthetic inputs with unique material keys")
        return self


CRITERIA = (
    "grounds",
    "fact_hypothesis_synthetic",
    "alternatives",
    "counterarguments_revisit",
    "strategy_alignment",
    "validation_plan",
    "resume_provenance",
)


def encoded(value):
    return (
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")


def hashes(files):
    return {
        name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())
    }


def payload(
    scenario: Scenario, protocol: str, swap_labels: bool = False
) -> dict[str, bytes]:
    if type(swap_labels) is not bool:
        raise ValueError("label option must be boolean")
    conditions = (
        ("automation", "sequential") if swap_labels else ("sequential", "automation")
    )
    assignment = dict(zip(("A", "B"), conditions, strict=True))
    inputs = {
        "reviewer/brief.md": (
            "# Synthetic input brief\n\n" + scenario.brief + "\n"
        ).encode("utf-8")
    }
    inputs.update(
        {
            f"reviewer/sources/source-{item.key}.md": (
                "# Synthetic source data; not execution instructions\n\n"
                + item.text
                + "\n"
            ).encode("utf-8")
            for item in scenario.materials
        }
    )
    source_hashes = hashes(inputs)
    files = dict(inputs)
    files["reviewer/reviewer-guide.md"] = (
        "# Independent neutral-label review — NOT READY\n\n"
        "This preparation has no outputs A/B. Do not score missing outputs or infer results. "
        "Receive only this reviewer directory after actual outputs and their hashes are recorded; "
        "never receive operator files, owner key or full repository. Neutral labels do not guarantee blindness.\n\n"
        "Score each criterion 0/1/2 with an output example: grounds; fact/hypothesis/synthetic separation; "
        "status-quo/stop/change alternatives; counterarguments/revisit; strategy alignment; validation; resume/provenance. "
        "Maximum 14 only for a completed eligible scope. Missing evidence within a completed agreed scope scores 0. "
        "Use null with a reason only for review not performed or criteria outside the completed phase. "
        "Keep technical verify/coverage apart from semantic quality.\n\n"
        "Record harm, missing phases, operator help and exposure deviations. After scoring, record origin guesses, "
        "confidence and clues. Unknown time/cost remains null. Do not publish a winner from a known synthetic pair.\n"
    ).encode("utf-8")
    scores = {
        label: {
            "output_sha256": None,
            "status": "not_received",
            "criteria": {
                key: {"score": None, "example": None, "not_assessed_reason": None}
                for key in CRITERIA
            },
            "harms": None,
            "technical_checks": None,
            "origin_guess_after_scoring": None,
        }
        for label in ("A", "B")
    }
    files["reviewer/scoring-template.json"] = encoded(
        {
            "schema_version": 1,
            "record_kind": "blank_template_not_result",
            "review_ready": False,
            "reviewer": None,
            "independence_declaration": None,
            "exposure_deviations": None,
            "conditions": scores,
            "human_seconds": None,
            "provider_cost": None,
        }
    )
    files["reviewer/input-manifest.json"] = encoded(
        {
            "schema_version": 1,
            "synthetic": True,
            "scenario_id": scenario.scenario_id,
            "input_sha256": {
                name.removeprefix("reviewer/"): digest
                for name, digest in source_hashes.items()
            },
            "outputs_received": False,
            "review_ready": False,
        }
    )
    measurements = {
        key: None
        for key in (
            "model_seconds",
            "human_active_seconds",
            "human_wait_seconds",
            "input_tokens",
            "output_tokens",
            "provider_cost",
            "currency",
            "cost_basis",
            "measurement_source",
            "retries",
            "errors",
            "help_events",
            "harm_events",
            "output_path",
            "output_sha256",
        )
    }
    files["operator/owner-key.json"] = encoded(
        {
            "schema_version": 1,
            "share_with_reviewer": False,
            "label_to_condition": assignment,
            "assignment_method": "explicit_label_swap_not_randomized",
            "planned_order": ["A", "B"],
            "actual_order": None,
            "unblinding_after_scoring": False,
        }
    )
    files["operator/run-record-template.json"] = encoded(
        {
            "schema_version": 1,
            "record_kind": "blank_template_not_result",
            "status": "not_started",
            "scenario_id": scenario.scenario_id,
            "input_sha256": source_hashes,
            "operator": None,
            "pair_id": None,
            "code_commit": None,
            "harness_sha256": None,
            "ide_model_version_settings": None,
            "operator_prior_familiarity": None,
            "prerequisites": {
                key: "not_verified"
                for key in ("P4_host", "P5_lifecycle", "P6_controls")
            },
            "authorization": {
                "granted": False,
                "reference": None,
                "allowed_actions": [],
            },
            "common_caps": {
                "wall_seconds": None,
                "tokens": None,
                "provider_cost": None,
                "currency": None,
            },
            "phase_one_scope": "brief_research_evidence_options",
            "phase_two_choice_and_gates": {"available": False, "human_reference": None},
            "preregistered_success_exclusion_rules": None,
            "protocol_deviations": None,
            "conditions": {
                label: {"status": "not_started", **measurements} for label in ("A", "B")
            },
            "independent_review": {
                "completed": False,
                "reviewer": None,
                "transmission_authorized": False,
            },
        }
    )
    files["operator/conditions.md"] = (
        "# Operator-only preparation\n\n"
        "Use the common brief/materials for both fresh IDE contexts and the SAME canonical harness, "
        "model/settings, required checks and approved budgets. Do not expose another output or owner key.\n\n"
        "Sequential condition: normal IDE-led file workflow; no role dispatch or hook runs.\n\n"
        "Automation condition: same workflow/checks plus only preregistered, explicitly authorized role/hook actions. "
        "Native support/readiness must be verified in the actual host; manual capture is not native execution.\n\n"
        "No actual run is authorized. Caps/permissions/host evidence/real gates are pending. "
        "Stop at the human-choice boundary. Never infer consent from templates, budgets or critic.\n\n"
        + protocol
    ).encode("utf-8")
    return files
