"""Disabled-only config merge and exact-byte transaction contracts."""

from copy import deepcopy
import hashlib
import json
import re
import tomllib
from typing import Literal
from uuid import UUID
from pydantic import Field, model_validator, ValidationError
from product_strategy_agent.domain.automation.contracts import Packet, Digest, Text
from product_strategy_agent.domain.automation.handoffs import strict_json
from product_strategy_agent.domain.automation.host_profiles import PlanHost

START = "# BEGIN PSA MANAGED CODEX MCP v1 sha256="
END = "# END PSA MANAGED CODEX MCP\n"
KEYS = {
    "command",
    "args",
    "cwd",
    "enabled",
    "required",
    "enabled_tools",
    "default_tools_approval_mode",
    "supports_parallel_tool_calls",
}


def digest(text):
    return None if text is None else hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_config(text):
    if text is None:
        return {}
    if len(text.encode("utf-8")) > 64000:
        raise ValueError("host config exceeds 64000 bytes")
    try:
        data = tomllib.loads(text)
        if "mcp_servers" in data and not isinstance(data["mcp_servers"], dict):
            raise ValueError("invalid mcp_servers table")
        return data
    except ValueError:
        raise ValueError(
            "host config TOML invalid; preserve it for manual inspection"
        ) from None


def without_psa(data):
    result = deepcopy(data)
    servers = result.get("mcp_servers", {})
    if not isinstance(servers, dict):
        raise ValueError("mcp_servers must be a table")
    servers.pop("psa", None)
    if not servers:
        result.pop("mcp_servers", None)
    return result


def block(fragment):
    return START + digest(fragment) + "\n" + fragment + END


def owned_span(text):
    if (
        text is None
        or "# BEGIN PSA MANAGED" not in text
        and "# END PSA MANAGED" not in text
    ):
        return None
    pattern = r"(?m)^" + re.escape(START) + r"([0-9a-f]{64})\n(.*?)^" + re.escape(END)
    matches = list(re.finditer(pattern, text, re.DOTALL))
    if (
        len(matches) != 1
        or text.count("# BEGIN PSA MANAGED") != 1
        or text.count("# END PSA MANAGED") != 1
    ):
        raise ValueError(
            "host managed markers invalid or unsupported; preserve for inspection"
        )
    match = matches[0]
    fragment = match.group(2)
    if digest(fragment) != match.group(1):
        raise ValueError("managed block was edited; refusing to overwrite")
    data = parse_config(fragment)
    server = data.get("mcp_servers", {}).get("psa")
    if (
        set(data) != {"mcp_servers"}
        or set(data["mcp_servers"]) != {"psa"}
        or not isinstance(server, dict)
        or set(server) != KEYS
    ):
        raise ValueError("unsupported managed block schema")
    for key in ("enabled", "required", "supports_parallel_tool_calls"):
        if type(server[key]) is not bool:
            raise ValueError("invalid managed boolean")
    for key in ("command", "cwd", "default_tools_approval_mode"):
        if not isinstance(server[key], str):
            raise ValueError("invalid managed string")
    for key in ("args", "enabled_tools"):
        if not isinstance(server[key], list) or any(
            not isinstance(item, str) for item in server[key]
        ):
            raise ValueError("invalid managed argument/tool list")
    return match.start(), match.end(), server


def merge(before, fragment, action):
    original = parse_config(before)
    span = owned_span(before)
    if action == "install_disabled":
        if span is not None or "psa" in original.get("mcp_servers", {}):
            raise ValueError("PSA server already exists; no unmanaged overwrite")
        text = before or ""
        after = (
            text + ("\n" if text and not text.endswith("\n") else "") + block(fragment)
        )
    else:
        if span is None:
            raise ValueError("operation requires a valid managed PSA block")
        if action == "disable":
            values = span[2]
            values["enabled"] = False
            fragment = "[mcp_servers.psa]\n" + "".join(
                f"{key} = {json.dumps(value, ensure_ascii=False)}\n"
                for key, value in values.items()
            )
        elif action != "refresh_disabled":
            raise ValueError("unsupported managed merge action")
        after = before[: span[0]] + block(fragment) + before[span[1] :]
    parsed = parse_config(after)
    if parsed["mcp_servers"]["psa"].get("enabled") is not False or without_psa(
        original
    ) != without_psa(parsed):
        raise ValueError("merge would activate PSA or change unrelated settings")
    return after


def assert_inactive(text):
    data = parse_config(text)
    server = data.get("mcp_servers", {}).get("psa")
    if server is not None and (
        not isinstance(server, dict) or server.get("enabled") is not False
    ):
        raise ValueError(
            "restoring active or unspecified PSA activation is not permitted"
        )


class PlanConfigChange(Packet):
    operation_id: UUID
    plan: PlanHost
    action: Literal["install_disabled", "refresh_disabled", "disable", "restore"]
    interpreter: str | None = Field(default=None, max_length=1000)
    review_operation_id: UUID | None = None
    source_operation_id: UUID | None = None
    changed_by: Text
    reason: Text

    @model_validator(mode="after")
    def action_scope(self):
        if (
            self.plan.host_id != "codex"
            or self.plan.feature != "mcp_stdio"
            or self.plan.mode != "native"
        ):
            raise ValueError("config changes require Codex MCP native proposal scope")
        if self.action == "restore":
            if (
                self.source_operation_id is None
                or self.interpreter is not None
                or self.review_operation_id is not None
            ):
                raise ValueError("restore requires source operation only")
        elif self.interpreter is None or self.source_operation_id is not None:
            raise ValueError("merge requires interpreter and no restore source")
        return self


class ApplyConfigChange(PlanConfigChange):
    expected_before_hash: Digest | None
    expected_after_hash: Digest | None
    scope_hash: Digest


def parse_request(raw, model):
    if len(raw) > 64000:
        raise ValueError("config request exceeds 64000 bytes")
    try:
        return model.model_validate_json(
            json.dumps(strict_json(raw), ensure_ascii=False, allow_nan=False)
        )
    except ValidationError:
        raise ValueError("invalid disabled config request schema") from None
