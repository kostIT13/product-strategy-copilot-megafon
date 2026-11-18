"""Author drafts for human review of changes in evidence and recommendations."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Text = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1500)
]
Hash = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class ProposedChange(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    action: Literal["keep", "recheck", "revise"]
    rationale: Text
    next_step: Text | None = None

    @model_validator(mode="after")
    def require_next_step(self):
        if self.action != "keep" and self.next_step is None:
            raise ValueError("recheck and revise require a concrete next_step")
        return self


class RevisionProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    context_sha256: Hash
    change_summary: Text
    claims: dict[str, ProposedChange] = Field(max_length=50)
    decisions: dict[str, ProposedChange] = Field(max_length=50)
    product_strategy: ProposedChange
    communication_strategy: ProposedChange
    validation_plan: ProposedChange


def check_proposal(context, draft):
    if not context["latest_revision"] or context["source_status"] != "extracted":
        raise ValueError("Prepare a draft from the latest revision of an active source")
    if draft.context_sha256 != context["context_sha256"]:
        raise ValueError("Revision context changed. Refresh it and recheck the draft")
    remaining = {}
    for kind, id_key in (("claims", "claim_id"), ("decisions", "decision_id")):
        visible = {row[id_key] for row in context[f"affected_{kind}"]}
        covered = set(getattr(draft, kind))
        if covered - visible:
            raise ValueError(
                f"Draft references {kind} outside the selected revision context"
            )
        remaining[kind] = context[f"affected_{kind[:-1]}_count"] - len(covered)
    return {
        "status": "draft",
        "complete_dependency_coverage": not any(remaining.values()),
        "unaddressed_counts": remaining,
        "revision_event_id": context["revision_event_id"],
        "project_id": context["project_id"],
        "workflow_version": context["workflow_version"],
        "draft": draft.model_dump(mode="json"),
    }
