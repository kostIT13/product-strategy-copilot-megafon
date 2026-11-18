"""Structural readiness of recorded alternatives for human comparison."""

REQUIRED_ROLES = ("status_quo", "stop", "change")
REQUIRED_FIELDS = (
    "name",
    "description",
    "benefits",
    "costs",
    "risks",
    "strongest_objection",
)
PLACEHOLDERS = {
    "-",
    "—",
    "?",
    "todo",
    "tbd",
    "n/a",
    "unknown",
    "неизвестно",
    "уточнить",
}


def is_described(value):
    if not isinstance(value, str):
        return False
    cleaned = value.strip().casefold().rstrip(".")
    return bool(cleaned) and cleaned not in PLACEHOLDERS


def comparison_readiness(options, affected_option_ids):
    affected = set(affected_option_ids)
    rows = []
    eligible_roles = set()
    for option in options:
        option_id, role = option["option_id"], option.get("role")
        missing = [
            field for field in REQUIRED_FIELDS if not is_described(option.get(field))
        ]
        affected_evidence = option_id in affected
        eligible = not missing and not affected_evidence and role in REQUIRED_ROLES
        if eligible:
            eligible_roles.add(role)
        rows.append(
            {
                "option_id": option_id,
                "role": role,
                "missing_fields": missing,
                "affected_evidence": affected_evidence,
                "eligible": eligible,
            }
        )
    missing_roles = [role for role in REQUIRED_ROLES if role not in eligible_roles]
    return {"ready": not missing_roles, "missing_roles": missing_roles, "options": rows}
