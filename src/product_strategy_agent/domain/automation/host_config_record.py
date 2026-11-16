"""Private before/after intent, preserving full config without returning its contents."""

import json
from pydantic import AwareDatetime, Field, model_validator, field_validator
from typing import Literal
from product_strategy_agent.domain.automation.contracts import Model, fingerprint
from product_strategy_agent.domain.automation.handoffs import strict_json
from product_strategy_agent.domain.automation.host_config import (
    ApplyConfigChange,
    digest,
    parse_config,
    assert_inactive,
    owned_span,
    merge,
)


class ConfigRecord(Model):
    schema_version: Literal[1] = Field(...)
    command: ApplyConfigChange
    before: str | None
    after: str | None
    prepared_at: AwareDatetime

    @field_validator("schema_version", mode="before")
    @classmethod
    def version(cls, value):
        if type(value) is not int or value != 1:
            raise ValueError("config journal version must be integer 1")
        return value

    @model_validator(mode="after")
    def byte_binding(self):
        parse_config(self.before)
        assert_inactive(self.after)
        if (
            digest(self.before) != self.command.expected_before_hash
            or digest(self.after) != self.command.expected_after_hash
        ):
            raise ValueError("config intent byte/hash mismatch")
        if self.command.action != "restore":
            span = owned_span(self.after)
            if span is None:
                raise ValueError("config intent requires managed after block")
            fragment = (
                self.after[span[0] : span[1]]
                .split("\n", 1)[1]
                .rsplit("# END PSA MANAGED CODEX MCP\n", 1)[0]
            )
            if merge(self.before, fragment, self.command.action) != self.after:
                raise ValueError(
                    "config intent does not reconstruct its controlled merge"
                )
        return self


def encode(record):
    raw = json.dumps(
        {"record": record.model_dump(mode="json"), "record_hash": fingerprint(record)},
        ensure_ascii=False,
        sort_keys=True,
    ).encode("utf-8")
    if len(raw) > 512000:
        raise ValueError("config private intent exceeds 512000 bytes")
    return raw


def decode(raw, identifier):
    try:
        body = strict_json(raw)
        if not isinstance(body, dict) or set(body) != {"record", "record_hash"}:
            raise ValueError("invalid envelope")
        record = ConfigRecord.model_validate_json(
            json.dumps(body["record"], ensure_ascii=False, allow_nan=False)
        )
        if (
            record.command.operation_id != identifier
            or fingerprint(record) != body["record_hash"]
        ):
            raise ValueError("invalid config intent identity")
        return record
    except (ValueError, TypeError):
        raise ValueError("invalid config private journal schema/hash") from None
