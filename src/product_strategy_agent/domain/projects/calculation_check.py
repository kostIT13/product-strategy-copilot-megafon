"""Exact rational calculations over current quoted numeric literals; no semantic inference."""

from decimal import Decimal
from fractions import Fraction
import json
from pydantic import ValidationError
from product_strategy_agent.domain.projects.authored_json import optional_json_block
from product_strategy_agent.domain.projects.authored_json import NO_BLOCK
from product_strategy_agent.domain.projects.calculation_models import (
    Calculations,
    UNITS,
)
from product_strategy_agent.domain.projects.baseline_numbers import literal_number
from product_strategy_agent.domain.projects.file_promises import check_claim
from product_strategy_agent.domain.projects.claim_lifecycle import fingerprint


def parse_calculations(markdown):
    body = optional_json_block(markdown, "psa-calculations-v1")
    if body is NO_BLOCK:
        return None
    try:
        return Calculations.model_validate(body)
    except ValidationError:
        raise ValueError(
            "invalid calculation fields, decimal strings, IDs or operands"
        ) from None


def round_half_even(value, places):
    scale = 10**places
    quotient, remainder = divmod(abs(value.numerator) * scale, value.denominator)
    if 2 * remainder > value.denominator or (
        2 * remainder == value.denominator and quotient % 2
    ):
        quotient += 1
    signed = -quotient if value < 0 else quotient
    return Fraction(signed, scale)


def arithmetic(operation, values):
    if operation in {"ratio", "percentage"}:
        numerator, denominator = values["numerator"], values["denominator"]
        if denominator <= 0:
            raise ValueError("denominator_must_be_positive")
        if operation == "percentage" and not 0 <= numerator <= denominator:
            raise ValueError("percentage_share_requires_zero_to_denominator_numerator")
        return numerator / denominator * (100 if operation == "percentage" else 1)
    baseline, current = values["baseline"], values["current"]
    if operation == "percentage_points":
        return current - baseline
    if baseline <= 0:
        raise ValueError("relative_change_requires_positive_baseline")
    return (current - baseline) / baseline * 100


def check_calculation(calculation, evidence):
    issues, inputs, values, units = [], {}, {}, {}
    for name, operand in calculation.operands.items():
        anchor = operand.anchor
        proof = check_claim(anchor.claim_id, evidence)
        issues.extend(name + ":" + issue for issue in proof["blockers"])
        if not any(
            row["source_id"] == anchor.source_id
            and row["locator"] == anchor.locator
            and row["quote"] == anchor.quote
            for row in proof["evidence"]
        ):
            issues.append(name + ":anchor_does_not_match_recorded_citation")
        try:
            token = anchor.quote[anchor.number_span.start : anchor.number_span.end]
            if len(token) > 80:
                raise ValueError("numeric_operand_exceeds_80_characters")
            values[name] = Fraction(
                literal_number(
                    anchor.quote, anchor.number_span, anchor.decimal_separator
                )
            )
            units[name] = anchor.quote[anchor.unit_span.start : anchor.unit_span.end]
            if not units[name].strip():
                raise ValueError("empty_unit_literal")
        except ValueError as error:
            issues.append(name + ":" + str(error))
        inputs[name] = {
            "anchor": anchor.model_dump(mode="json"),
            "context": operand.context.model_dump(),
            "evidence": proof,
        }
    operands = list(calculation.operands.values())
    contexts = [row.context for row in operands]
    if any(
        getattr(contexts[0], field) != getattr(contexts[1], field)
        for field in ("metric", "population", "conditions")
    ):
        issues.append("authored_context_labels_mismatch")
    same_period = contexts[0].period == contexts[1].period
    if same_period != (calculation.period_relation == "same"):
        issues.append("authored_period_relation_mismatch")
    if (
        calculation.operation in {"ratio", "percentage"}
        and calculation.period_relation != "same"
    ):
        issues.append("ratio_and_share_require_same_period")
    if len(set(units.values())) != 1:
        issues.append("operand_unit_literals_mismatch")
    if calculation.operation == "percentage_points" and set(units.values()) != {"%"}:
        issues.append("percentage_points_require_percent_operands")
    if calculation.result_unit != UNITS[calculation.operation]:
        issues.append("result_unit_mismatch")
    exact = checked = None
    if not issues:
        try:
            exact = arithmetic(calculation.operation, values)
            checked = (
                round_half_even(exact, calculation.rounding.decimal_places)
                if calculation.rounding
                else exact
            )
            if checked != Fraction(Decimal(calculation.expected_value)):
                issues.append("calculation_result_mismatch")
        except ValueError as error:
            issues.append(str(error))
    serialize = lambda value: (
        {"numerator": str(value.numerator), "denominator": str(value.denominator)}
        if value is not None
        else None
    )
    return {
        "calculation_id": calculation.calculation_id,
        "operation": calculation.operation,
        "status": "blocked" if issues else "arithmetic_match",
        "issues": sorted(set(issues)),
        "inputs": inputs,
        "expected_value": calculation.expected_value,
        "result_unit": calculation.result_unit,
        "rounding": calculation.rounding.model_dump() if calculation.rounding else None,
        "exact_result": serialize(exact),
        "checked_result": serialize(checked),
        "arithmetic_matches": not issues,
    }


def calculations_report(
    project_id, snapshot, calculations=None, evidence=None, error=None
):
    rows = (
        [check_calculation(row, evidence) for row in calculations.calculations]
        if calculations
        else []
    )
    issues = ([error] if error else []) + [
        row["calculation_id"] + ":" + issue for row in rows for issue in row["issues"]
    ]
    hashes = dict(snapshot.input_hashes)
    if evidence is not None:
        hashes.update(
            {"evidence/" + key: value for key, value in evidence.input_hashes.items()}
        )
    packet = {
        "format_version": "psa-calculation-check-v1",
        "project_id": project_id,
        "workflow_version": snapshot.version,
        "status": "blocked"
        if issues
        else "arithmetic_match"
        if rows
        else "not_applicable",
        "issues": issues,
        "scope": "authored_two_operand_arithmetic_over_current_citations",
        "calculations": rows,
        "input_hashes": hashes,
        "semantic_alignment_verified": False,
        "numeric_alignment_verified": False,
        "context_truth_verified": False,
        "observed_effect_verified": False,
        "publication_approved": False,
        "experiment_approved": False,
        "workflow_approval_granted": False,
        "requires_human_review": True,
    }
    if len(json.dumps(packet, ensure_ascii=False).encode("utf-8")) > 256000:
        raise ValueError("calculation packet exceeds 256000 bytes; no truncation")
    return {**packet, "review_hash": fingerprint(packet)}
