"""Conservative host profiles; installed instructions never imply native acceptance."""

from pathlib import PurePosixPath
from typing import Annotated, Literal
from pydantic import Field, StringConstraints, field_validator, model_validator
from product_strategy_agent.domain.automation.contracts import Model, Packet

HostId = Literal["codex", "cursor", "claude", "qwen", "sourcecraft"]
CAPABILITIES = {
    "instruction_loading",
    "skill_discovery",
    "mcp_stdio",
    "subagents",
    "hooks",
    "isolation",
    "budget_enforcement",
    "cancellation",
}


class HostProfile(Model):
    host_id: HostId
    instruction_paths: list[str] = Field(min_length=1, max_length=8)
    capabilities: dict[str, Literal["not_verified"]]

    @model_validator(mode="after")
    def fixed_capabilities(self):
        if set(self.capabilities) != CAPABILITIES:
            raise ValueError("host capability set must match protocol v1")
        if len(set(self.instruction_paths)) != len(self.instruction_paths):
            raise ValueError("duplicate host instruction path")
        for name in self.instruction_paths:
            path = PurePosixPath(name)
            if (
                not name
                or len(name) > 200
                or path.is_absolute()
                or ".." in path.parts
                or path.as_posix() != name
                or "\\" in name
                or ":" in name
                or not name.endswith((".md", ".mdc"))
                or not (
                    name in {"AGENTS.md", "CLAUDE.md", "QWEN.md"}
                    or name.startswith(
                        (".agents/skills/", ".claude/skills/", ".cursor/rules/")
                    )
                )
            ):
                raise ValueError("unsupported host instruction path")
        return self


class HostCatalog(Model):
    schema_version: Literal[1] = Field(...)
    catalog_version: Annotated[
        str, StringConstraints(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$", max_length=40)
    ]
    hosts: list[HostProfile] = Field(min_length=5, max_length=5)

    @field_validator("schema_version", mode="before")
    @classmethod
    def version(cls, value):
        if type(value) is not int or value != 1:
            raise ValueError("host catalog schema must be integer 1")
        return value

    @model_validator(mode="after")
    def complete(self):
        if {row.host_id for row in self.hosts} != {
            "codex",
            "cursor",
            "claude",
            "qwen",
            "sourcecraft",
        }:
            raise ValueError(
                "host catalog must contain each declared host exactly once"
            )
        return self


class PlanHost(Packet):
    host_id: HostId
    host_version: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
    ]
    platform: Literal["windows", "linux", "macos"]
    feature: Literal["mcp_stdio", "subagents", "hooks"]
    mode: Literal["sequential", "native"]
