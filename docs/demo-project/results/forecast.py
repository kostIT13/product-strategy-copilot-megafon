"""Reproduce the synthetic annual forecast for the chosen O-003 scenario."""

import csv
from decimal import Decimal, ROUND_HALF_UP
import json
from pathlib import Path


BASELINE_PATH = Path(__file__).resolve().parents[1] / "materials/baseline.csv"
MARGIN_PER_NUMBER_MONTH = 500
BASE_Q4_CREATED_GROUPS = 2_000  # Assumption: the brief gives only the rate.
ASSUMPTIONS = {
    "main": {
        "eligible_unique_impressions": 9_000,
        "incremental_creation_percent": 8,
        "invite_accept_percent": 60,
        "incremental_disconnects": 132,
        "active_share_of_net_new_percent": 60,
        "additional_active_existing": 160,
        "extra_q4_created": 240,
        "extra_q4_activated": 120,
        "extra_activated_in_baseline_q4_cohort": 50,
        "paid_number_months_by_quarter": [0, 200, 350, 650],
        "direct_expenses_rub_by_quarter": [0, 120_000, 100_000, 130_000],
    },
    "downside": {
        "eligible_unique_impressions": 5_000,
        "incremental_creation_percent": 4,
        "invite_accept_percent": 50,
        "incremental_disconnects": 50,
        "active_share_of_net_new_percent": 50,
        "additional_active_existing": 30,
        "extra_q4_created": 70,
        "extra_q4_activated": 28,
        "extra_activated_in_baseline_q4_cohort": 10,
        "paid_number_months_by_quarter": [0, 40, 60, 100],
        "direct_expenses_rub_by_quarter": [0, 150_000, 140_000, 160_000],
    },
}


def whole(value):
    return int(Decimal(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def read_baseline(path):
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    baseline = {row["metric"]: int(row["baseline"]) for row in rows}
    targets = {row["metric"]: int(row["target"]) for row in rows}
    if len(baseline) != len(rows):
        raise ValueError("Each baseline metric must occur exactly once.")
    return baseline, targets


def forecast(a, baseline, targets):
    created = whole(Decimal(a["eligible_unique_impressions"]) * a["incremental_creation_percent"] / 100)
    connected = whole(Decimal(created) * a["invite_accept_percent"] / 100)
    net = connected - a["incremental_disconnects"]
    assert 0 <= a["extra_q4_activated"] <= a["extra_q4_created"] <= created
    q4_total = BASE_Q4_CREATED_GROUPS + a["extra_q4_created"]
    q4_activated = (BASE_Q4_CREATED_GROUPS * baseline["activation_percent"] // 100
                    + a["extra_q4_activated"] + a["extra_activated_in_baseline_q4_cohort"])
    activation = (Decimal(q4_activated) * 100 / q4_total).quantize(Decimal("0.01"))
    contribution = [m * MARGIN_PER_NUMBER_MONTH - cost for m, cost in zip(
        a["paid_number_months_by_quarter"], a["direct_expenses_rub_by_quarter"], strict=True
    )]
    values = {
        "gross_profit_rub": baseline["gross_profit_rub"] + sum(contribution),
        "active_family_groups": baseline["active_family_groups"]
        + whole(Decimal(net) * a["active_share_of_net_new_percent"] / 100)
        + a["additional_active_existing"],
        "connected_family_groups": baseline["connected_family_groups"] + net,
        "connected_multi_number_owners": baseline["connected_multi_number_owners"],
        "activation_percent": activation,
    }
    remaining_to_target_before_month_margin = (
        targets["gross_profit_rub"] - baseline["gross_profit_rub"]
        + sum(a["direct_expenses_rub_by_quarter"])
    )
    values_and_gaps = {key: {"value": value, "gap": targets[key] - value}
                       for key, value in values.items()}
    return {
        "extra_created": created,
        "extra_connected_before_exits": connected,
        "extra_connected_net": net,
        "q4_activation": [q4_activated, q4_total],
        "contribution_by_quarter_rub": contribution,
        "months_for_target": (remaining_to_target_before_month_margin
                              + MARGIN_PER_NUMBER_MONTH - 1) // MARGIN_PER_NUMBER_MONTH,
        "max_dev_investment_for_year_end_payback_rub": max(0, sum(contribution)),
        "indicators": values_and_gaps,
    }


if __name__ == "__main__":
    baseline, targets = read_baseline(BASELINE_PATH)
    print(json.dumps({name: forecast(a, baseline, targets) for name, a in ASSUMPTIONS.items()},
                     default=str, ensure_ascii=False, indent=2))
