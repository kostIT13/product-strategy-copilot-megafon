"""Aggregate reported case effort without treating missing coverage as zero."""

from collections import defaultdict
from decimal import Decimal, localcontext
from typing import get_args

from product_strategy_agent.domain.automation.usage_provenance import (
    read_usage_rows,
    sha256,
)
from product_strategy_agent.domain.projects.usage_record import UsageCategory

CATEGORIES = (*get_args(UsageCategory), "unclassified")
DURATION_BASES = ("measured", "estimated", "basis_unspecified")


def _totals(rows):
    durations = defaultdict(list)
    costs = defaultdict(list)
    retries = []
    for row in rows:
        if row.duration_ms is not None:
            durations[row.duration_certainty or "basis_unspecified"].append(
                row.duration_ms
            )
        if row.cost.amount is not None:
            if len(row.cost.amount) > 128:
                raise ValueError("Case cost amount exceeds 128 characters")
            costs[(row.cost.currency, row.cost.certainty)].append(
                Decimal(row.cost.amount)
            )
        if row.retry_count is not None:
            retries.append(row.retry_count)
    with localcontext() as context:
        # Allow 128 integral digits and 128 fractional digits plus carry from the bounded ledger.
        context.prec = 260
        cost_totals = [
            {
                "currency": currency,
                "basis": basis,
                "amount": format(sum(amounts), "f"),
                "records": len(amounts),
            }
            for (currency, basis), amounts in sorted(costs.items())
        ]
    return {
        "records": len(rows),
        "duration_ms_by_basis": {
            basis: sum(durations[basis]) if durations[basis] else None
            for basis in DURATION_BASES
        },
        "rows_without_duration": len(rows) - sum(map(len, durations.values())),
        "cost_by_currency_and_basis": cost_totals,
        "rows_without_cost": len(rows) - sum(map(len, costs.values())),
        "recorded_retries": sum(retries) if retries else None,
        "rows_without_retry_count": len(rows) - len(retries),
    }


def case_effort(snapshot):
    rows = [row for _, row in read_usage_rows(snapshot)]
    groups = {category: [] for category in CATEGORIES}
    for row in rows:
        groups[row.category or "unclassified"].append(row)
    return {
        "format_version": 1,
        "scope": "recorded_usage_only",
        "complete_case_effort_verified": False,
        "usage_sha256": sha256(snapshot.raw),
        "totals": _totals(rows),
        "categories_without_records": [
            category for category in CATEGORIES[:-1] if not groups[category]
        ],
        "by_category": {category: _totals(items) for category, items in groups.items()},
    }
