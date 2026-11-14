"""Bounded version-one envelopes, snapshot identities and self-reported budgets."""

import hashlib
import json
from typing import Annotated, Literal
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

Digest = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Identifier = Annotated[
    str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
]
Cost = Annotated[
    str, StringConstraints(pattern=r"^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$", max_length=40)
]
Text = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)
]


class Model(BaseModel):
    model_config = ConfigDict(
        extra="forbid", strict=True, revalidate_instances="always"
    )


class Packet(Model):
    schema_version: Literal[1] = 1

    @field_validator("schema_version", mode="before")
    @classmethod
    def exact_version(cls, value):
        if type(value) is not int or value != 1:
            raise ValueError("automation schema_version must be integer 1")
        return value

    @model_validator(mode="after")
    def bounded(self):
        if (
            len(
                json.dumps(self.model_dump(mode="json"), ensure_ascii=False).encode(
                    "utf-8"
                )
            )
            > 128000
        ):
            raise ValueError("automation packet exceeds 128000 bytes; no truncation")
        return self


class CaseTarget(Model):
    kind: Literal["case"] = "case"
    project_id: Identifier
    workflow_version: int = Field(ge=0)
    snapshot_hash: Digest


class ReleaseTarget(Model):
    kind: Literal["release"] = "release"
    manifest_hash: Digest


class Budget(Model):
    timeout_seconds: int = Field(ge=1, le=900)
    token_limit: int = Field(ge=1, le=200000)
    max_cost: Cost | None = None
    currency: Literal["RUB", "USD"] | None = None

    @model_validator(mode="after")
    def cost_pair(self):
        if (self.max_cost is None) != (self.currency is None):
            raise ValueError("currency and max_cost must be specified together")
        return self


def fingerprint(packet):
    return hashlib.sha256(
        json.dumps(
            packet.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
