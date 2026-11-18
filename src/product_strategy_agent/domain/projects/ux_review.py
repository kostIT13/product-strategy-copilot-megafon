"""Bind a UX walkthrough to ordered steps and screenshot regions."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from product_strategy_agent.domain.projects.claim_lifecycle import fingerprint

Text = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1500)
]
StepID = Annotated[str, StringConstraints(pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,31}$")]
Hash = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Coordinate = Annotated[int, Field(ge=0, le=8192)]
Extent = Annotated[int, Field(ge=1, le=8192)]


class UXModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class JourneyStep(UXModel):
    step_id: StepID
    task: Text
    screenshot: Annotated[str, StringConstraints(min_length=1, max_length=240)]


class Journey(UXModel):
    user_goal: Text
    steps: list[JourneyStep] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def unique_steps(self):
        if len({step.step_id for step in self.steps}) != len(self.steps):
            raise ValueError("Journey step IDs must be unique")
        return self


class ScreenRegion(UXModel):
    x: Coordinate
    y: Coordinate
    width: Extent
    height: Extent


class UXObservation(UXModel):
    step_id: StepID
    region: ScreenRegion
    aspect: Literal[
        "navigation", "hierarchy", "content", "feedback", "accessibility", "other"
    ]
    visible_observation: Text
    hypothesis: Text
    verification: Text


class UXReview(UXModel):
    journey: Journey
    manifest_sha256: Hash
    observations: list[UXObservation] = Field(max_length=36)


def journey_manifest(project_id, journey, screens):
    manifest = {
        "format_version": 1,
        "project_id": project_id,
        "user_goal": journey.user_goal,
        "steps": [
            {**step.model_dump(mode="json"), **screens[step.screenshot]}
            for step in journey.steps
        ],
    }
    return {**manifest, "manifest_sha256": fingerprint(manifest)}


def check_ux_review(manifest, review):
    if review.manifest_sha256 != manifest["manifest_sha256"]:
        raise ValueError("Journey or screenshot changed. Prepare a fresh manifest")
    steps = {step["step_id"]: step for step in manifest["steps"]}
    covered = set()
    for item in review.observations:
        step = steps.get(item.step_id)
        if step is None:
            raise ValueError("Observation refers to a step outside the journey")
        region = item.region
        if (
            region.x + region.width > step["width_px"]
            or region.y + region.height > step["height_px"]
        ):
            raise ValueError(
                f"Observation region is outside the screenshot for {item.step_id}"
            )
        covered.add(item.step_id)
    return {
        **manifest,
        "status": "authored_draft",
        "regions_checked": True,
        "content_independently_verified": False,
        "steps_without_observations": [
            step_id for step_id in steps if step_id not in covered
        ],
        "observations": [item.model_dump(mode="json") for item in review.observations],
    }
