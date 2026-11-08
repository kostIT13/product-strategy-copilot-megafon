"""Explicit human selection of a pinned, critic-reviewed strategy draft."""
import hashlib
import json
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
Hash = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
OptionId = Literal["O1", "O2", "O3"]


class SelectionCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", revalidate_instances="always")
    source_run_id: UUID
    critic_run_id: UUID
    source_hash: Hash
    critic_hash: Hash
    decision_key: Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")]
    selected: OptionId
    rejected: list[OptionId] = Field(default_factory=list, max_length=2)
    deferred: list[OptionId] = Field(default_factory=list, max_length=2)
    owner: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    rationale: Text
    review_trigger: Text
    review_note: Text
    critic_resolution: Text | None = None
    confirmed: bool = Field(strict=True)

    @model_validator(mode="after")
    def check_choice(self):
        ids = [self.selected, *self.rejected, *self.deferred]
        if not self.confirmed or len(ids) != 3 or set(ids) != {"O1", "O2", "O3"}:
            raise ValueError("explicit confirmation and exactly one disposition for each option are required")
        self.rejected.sort()
        self.deferred.sort()
        return self


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def run_fingerprint(run):
    return fingerprint({key: getattr(run, key) for key in
                        ("id", "project_id", "status", "task", "question", "query", "model", "prompt_version",
                         "contexts", "result", "input_run_id", "input_hash")})
