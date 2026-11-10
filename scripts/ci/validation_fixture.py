"""Authored synthetic measurement plan, never an observed product outcome."""

import json


def synthetic_validation_plan():
    return {
        "schema_version": 1,
        "hypothesis": "A local synthetic export trial may reduce fixture task effort.",
        "expected_change": "Hypothesis: less fixture task effort; effect size is not measured.",
        "metric": {
            "name": "Fixture task completion",
            "definition": "Completed synthetic export tasks divided by attempted synthetic tasks.",
            "unit": "ratio",
            "population": "Generated fixture tasks only",
            "data_source": "Temporary synthetic test log",
        },
        "baseline": {
            "status": "unknown",
            "value": None,
            "reason": "No baseline observation has been made for this synthetic trial.",
            "measurement": {
                "method": "Record fixture outcomes before enabling the change.",
                "owner": "Synthetic fixture analyst",
                "due_at": "2027-01-15T12:00:00Z",
            },
        },
        "comparison": "Compare with a separately recorded unchanged synthetic fixture run.",
        "success_criterion": "Proposed fixture-only criterion: higher completion ratio with no guardrail violation; this is not an observed result.",
        "observation": {
            "start_condition": "After baseline is recorded and the fixture actor authorizes the trial.",
            "duration_days": 7,
        },
        "guardrails": [
            {
                "name": "Fixture data integrity",
                "definition": "Count unexpected changes to fixture source material.",
                "data_source": "Temporary source hash checks",
                "stop_rule": "Stop on any unexpected fixture source modification.",
                "owner": "Synthetic fixture operator",
            }
        ],
        "owner": "Synthetic fixture analyst",
        "decision_rule": "Review baseline and guardrails; stop or revise on failure, request a human decision before any real use.",
    }


def validation_markdown(plan=None):
    plan = synthetic_validation_plan() if plan is None else plan
    return (
        "# Synthetic validation plan\n\n[HYPOTHESIS] This fixture defines a proposed measurement process and does not report a measured effect.\n\n"
        "```psa-validation-v1\n"
        + json.dumps(plan, ensure_ascii=False, indent=2)
        + "\n```\n"
    )
