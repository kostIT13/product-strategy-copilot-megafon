"""Validate authored qualitative analysis against captured transcript excerpts."""

from hashlib import sha256

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from product_strategy_agent.domain.projects.claim_lifecycle import fingerprint
from product_strategy_agent.domain.projects.file_promises import citation_excerpt

Text = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1500)
]
Quote = Annotated[str, StringConstraints(min_length=1, max_length=1500)]
SourceID = Annotated[str, StringConstraints(pattern=r"^S-[A-Za-z0-9_-]{1,120}$")]
Hash = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Locator = Annotated[str, StringConstraints(min_length=1, max_length=200)]


class DraftModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Transcript(DraftModel):
    source_id: SourceID
    content_hash: Hash


class CodedExcerpt(DraftModel):
    source_id: SourceID
    locator: Locator
    quote: Quote
    relation: Literal["supports", "challenges"]

    @model_validator(mode="after")
    def substantive_quote(self):
        if not self.quote.strip():
            raise ValueError("An excerpt needs a nonblank quote")
        return self


class Theme(DraftModel):
    label: Text
    interpretation: Text
    limitation: Text
    next_check: Text
    excerpts: list[CodedExcerpt] = Field(min_length=1, max_length=12)


class InterviewAnalysis(DraftModel):
    research_question: Text
    material_kind: Literal["consented_interviews", "synthetic_dialogues"]
    consent_declared: bool = False
    deidentified_declared: bool
    transcripts: list[Transcript] = Field(min_length=1, max_length=8)
    themes: list[Theme] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def scope_is_explicit(self):
        if not self.deidentified_declared:
            raise ValueError("Use deidentified transcripts")
        if self.consent_declared != (self.material_kind == "consented_interviews"):
            raise ValueError(
                "Declare participant consent only for real, consented interviews"
            )
        ids = {row.source_id for row in self.transcripts}
        labels = {row.label.casefold() for row in self.themes}
        if len(ids) != len(self.transcripts) or len(labels) != len(self.themes):
            raise ValueError("Transcript IDs and theme labels must be unique")
        for theme in self.themes:
            if any(row.source_id not in ids for row in theme.excerpts):
                raise ValueError("Every excerpt must reference a selected transcript")
        return self


def analyze_interviews(request, sources):
    checked_themes = []
    for theme in request.themes:
        references = []
        for ref in theme.excerpts:
            source, text = sources[ref.source_id]
            try:
                found = ref.quote in citation_excerpt(source, text, ref.locator)
            except ValueError:
                found = False
            if not found:
                raise ValueError(
                    f"Quote or locator failed verification for {ref.source_id}"
                )
            references.append(
                {
                    "source_id": ref.source_id,
                    "content_hash": source["content_hash"],
                    "quote_sha256": sha256(ref.quote.encode("utf-8")).hexdigest(),
                    "locator": ref.locator,
                    "relation": ref.relation,
                }
            )
        checked_themes.append(
            {
                "label": theme.label,
                "interpretation": theme.interpretation,
                "limitation": theme.limitation,
                "next_check": theme.next_check,
                "verified_excerpts": references,
            }
        )
    return {
        "format_version": 1,
        "research_question": request.research_question,
        "material_kind": request.material_kind,
        "evidence_scope": "hypothesis_only"
        if request.material_kind == "synthetic_dialogues"
        else "qualitative_observations_only",
        "review_status": "authored_draft",
        "consent_declared": request.consent_declared,
        "deidentified_declared": request.deidentified_declared,
        "independent_consent_or_content_verified": False,
        "population_or_demand_verified": False,
        "analysis_sha256": fingerprint(request.model_dump(mode="json")),
        "themes": checked_themes,
    }
