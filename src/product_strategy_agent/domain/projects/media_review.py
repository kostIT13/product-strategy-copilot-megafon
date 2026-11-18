"""Attach authored observations to bounded regions or timed intervals."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from product_strategy_agent.domain.projects.claim_lifecycle import fingerprint
from product_strategy_agent.domain.projects.ux_review import ScreenRegion


class MediaModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class MediaSelection(MediaModel):
    path: Annotated[str, StringConstraints(min_length=1, max_length=240)]


class Interval(MediaModel):
    start_ms: Annotated[int, Field(ge=0, le=86400000)]
    end_ms: Annotated[int, Field(ge=1, le=86400000)]


Text = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1500)
]


class MediaObservation(MediaModel):
    anchor: ScreenRegion | Interval
    basis: Literal["visual_review", "listening", "provided_transcript"]
    observation: Text
    limitation: Text


class MediaReview(MediaModel):
    selection: MediaSelection
    manifest_sha256: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    observations: list[MediaObservation] = Field(min_length=1, max_length=36)


def media_manifest(project_id, selection, metadata):
    payload = {
        "format_version": 1,
        "project_id": project_id,
        "path": selection.path,
        **metadata,
    }
    return {**payload, "manifest_sha256": fingerprint(payload)}


def check_media_review(manifest, review):
    if manifest["manifest_sha256"] != review.manifest_sha256:
        raise ValueError("Media file or selection changed. Prepare a fresh manifest")
    media_format = manifest["media_format"]
    for item in review.observations:
        anchor = item.anchor
        if media_format == "png":
            if not isinstance(anchor, ScreenRegion) or item.basis != "visual_review":
                raise ValueError(
                    "PNG observations require a visual review and pixel region"
                )
            if (
                anchor.x + anchor.width > manifest["width_px"]
                or anchor.y + anchor.height > manifest["height_px"]
            ):
                raise ValueError("Observation region is outside the image")
        else:
            if (
                not isinstance(anchor, Interval)
                or not anchor.start_ms < anchor.end_ms <= manifest["duration_ms"]
            ):
                raise ValueError(
                    "Observation needs a nonempty interval within the media duration"
                )
            if media_format == "wav" and item.basis == "visual_review":
                raise ValueError(
                    "WAV observations require listening or a provided transcript"
                )
    return {
        **manifest,
        "status": "authored_draft",
        "anchors_checked": True,
        "content_independently_verified": False,
        "observations": [item.model_dump(mode="json") for item in review.observations],
    }
