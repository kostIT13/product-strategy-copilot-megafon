"""Explicit material selection and bound read-only role handoffs."""

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Annotated, Literal
from uuid import UUID
from pydantic import Field, StringConstraints, field_validator, model_validator
from product_strategy_agent.domain.automation.contracts import (
    Budget,
    CaseTarget,
    Digest,
    Identifier,
    Model,
    Packet,
    fingerprint,
)
from product_strategy_agent.domain.automation.subagents import (
    Excerpt,
    Role,
    SubagentTask,
)

FILES = frozenset(
    (
        "01_brief.md",
        "02_research-plan.md",
        "claims.jsonl",
        "gaps.jsonl",
        "options.jsonl",
        "capabilities.jsonl",
        "decision-log.jsonl",
        "drafts/product-strategy.md",
        "drafts/communication-strategy.md",
        "drafts/validation-plan.md",
    )
)
METADATA = frozenset(("state.json", "events.jsonl", "sources.jsonl"))
Version = Annotated[
    str, StringConstraints(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$", max_length=40)
]
Goal = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
]


def allowed_material(path):
    if path not in FILES and not re.fullmatch(
        r"sources/S-[A-Za-z0-9_-]{1,120}\.txt", path
    ):
        raise ValueError("handoff material path is not allowlisted")
    return path


def strict_json(raw):
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8-sig")

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate handoff JSON field")
            result[key] = value
        return result

    def reject(value):
        raise ValueError("non-finite handoff JSON number")

    try:
        return json.loads(raw, object_pairs_hook=unique, parse_constant=reject)
    except (json.JSONDecodeError, RecursionError):
        raise ValueError("invalid handoff JSON") from None


class Selection(Model):
    input_id: Identifier
    path: str
    start: int = Field(default=0, ge=0)
    end: int | None = Field(default=None, ge=1)

    @field_validator("path")
    @classmethod
    def material(cls, value):
        return allowed_material(value)

    @model_validator(mode="after")
    def ordered(self):
        if self.end is not None and self.end <= self.start:
            raise ValueError("selection end must follow start")
        return self


class PrepareHandoff(Packet):
    task_id: UUID
    role: Role
    goal: Goal
    budget: Budget
    selections: list[Selection] = Field(min_length=1, max_length=16)

    @model_validator(mode="after")
    def distinct_ids(self):
        ids = [row.input_id for row in self.selections]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate handoff input IDs")
        return self


def parse_request(raw):
    return PrepareHandoff.model_validate_json(
        json.dumps(strict_json(raw), ensure_ascii=False, allow_nan=False)
    )


class RoleCatalog(Packet):
    schema_version: Literal[1] = Field(...)
    roles: dict[Role, Version]

    @model_validator(mode="after")
    def all_roles(self):
        if set(self.roles) != {"research", "evidence", "critic"}:
            raise ValueError("role catalog requires research/evidence/critic")
        return self


class ProfileRef(Model):
    role: Role
    version: Version
    sha256: Digest
    catalog_sha256: Digest


class RoleProfile(ProfileRef):
    text: str = Field(min_length=1, max_length=16000)

    @model_validator(mode="after")
    def exact_hash(self):
        if not self.text.strip():
            raise ValueError("role instructions are empty")
        if hashlib.sha256(self.text.encode("utf-8")).hexdigest() != self.sha256:
            raise ValueError("role instructions hash mismatch")
        return self

    def reference(self):
        return ProfileRef.model_validate(self.model_dump(exclude={"text"}))


class InputOrigin(Model):
    input_id: Identifier
    path: str
    file_sha256: Digest
    start: int = Field(ge=0)
    end: int = Field(ge=1)
    source_id: str | None = None

    @model_validator(mode="after")
    def origin(self):
        allowed_material(self.path)
        expected = (
            self.path.removeprefix("sources/").removesuffix(".txt")
            if self.path.startswith("sources/")
            else None
        )
        if self.source_id != expected or self.end <= self.start:
            raise ValueError("invalid handoff origin/source/range")
        return self


class SelectionIdentity(Model):
    origins: list[InputOrigin]


class SnapshotIdentity(Model):
    project_id: Identifier
    workflow_version: int = Field(ge=0)
    input_hashes: dict[str, Digest]


class TaskGoal(Model):
    requested_goal: Goal
    role_profile: ProfileRef
    selection_hash: Digest


class Handoff(Packet):
    format_version: Literal["psa-subagent-handoff-v1"] = "psa-subagent-handoff-v1"
    task: SubagentTask
    role_instructions: RoleProfile
    origins: list[InputOrigin] = Field(min_length=1, max_length=16)
    input_hashes: dict[str, Digest]

    @model_validator(mode="after")
    def bound_inputs(self):
        ids = [row.input_id for row in self.origins]
        if ids != [row.input_id for row in self.task.inputs]:
            raise ValueError("handoff origin IDs/order mismatch")
        if set(self.input_hashes) != METADATA | {row.path for row in self.origins}:
            raise ValueError("handoff input hash scope mismatch")
        for origin, excerpt in zip(self.origins, self.task.inputs):
            if origin.file_sha256 != self.input_hashes[
                origin.path
            ] or origin.end - origin.start != len(excerpt.text):
                raise ValueError("handoff excerpt origin mismatch")
        goal = TaskGoal.model_validate_json(json.dumps(strict_json(self.task.goal)))
        if (
            goal.role_profile != self.role_instructions.reference()
            or self.task.role != self.role_instructions.role
            or goal.selection_hash
            != fingerprint(SelectionIdentity(origins=self.origins))
        ):
            raise ValueError("handoff role/selection binding mismatch")
        identity = SnapshotIdentity(
            project_id=self.task.target.project_id,
            workflow_version=self.task.target.workflow_version,
            input_hashes=self.input_hashes,
        )
        if self.task.target.snapshot_hash != fingerprint(identity):
            raise ValueError("handoff snapshot hash mismatch")
        return self


@dataclass(frozen=True)
class Material:
    text: str
    source_id: str | None


@dataclass(frozen=True)
class HandoffSnapshot:
    version: int
    input_hashes: dict
    materials: dict[str, Material]


def build_handoff(project_id, request, snapshot, profile):
    inputs, origins = [], []
    for selection in request.selections:
        material = snapshot.materials[selection.path]
        end = len(material.text) if selection.end is None else selection.end
        if not 0 <= selection.start < end <= len(material.text):
            raise ValueError("handoff selection outside material; no clipping")
        text = material.text[selection.start : end]
        inputs.append(
            Excerpt(
                input_id=selection.input_id,
                text=text,
                sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            )
        )
        origins.append(
            InputOrigin(
                input_id=selection.input_id,
                path=selection.path,
                file_sha256=snapshot.input_hashes[selection.path],
                start=selection.start,
                end=end,
                source_id=material.source_id,
            )
        )
    identity = SnapshotIdentity(
        project_id=project_id,
        workflow_version=snapshot.version,
        input_hashes=snapshot.input_hashes,
    )
    goal = TaskGoal(
        requested_goal=request.goal,
        role_profile=profile.reference(),
        selection_hash=fingerprint(SelectionIdentity(origins=origins)),
    )
    task = SubagentTask(
        task_id=request.task_id,
        role=request.role,
        target=CaseTarget(
            project_id=project_id,
            workflow_version=snapshot.version,
            snapshot_hash=fingerprint(identity),
        ),
        goal=goal.model_dump_json(),
        budget=request.budget,
        inputs=inputs,
    )
    packet = Handoff(
        task=task,
        role_instructions=profile,
        origins=origins,
        input_hashes=snapshot.input_hashes,
    )
    result = {
        **packet.model_dump(mode="json"),
        "handoff_fingerprint": fingerprint(packet),
        "task_fingerprint": fingerprint(task),
        "execution_started": False,
        "canonical_writes": False,
    }
    if len(json.dumps(result, ensure_ascii=False).encode("utf-8")) > 128000:
        raise ValueError("prepared handoff exceeds 128000 bytes; no truncation")
    return result
