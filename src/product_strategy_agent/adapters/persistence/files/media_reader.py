"""Read metadata and hashes for one explicitly selected local media file."""

from hashlib import sha256
import json
from pathlib import PurePosixPath

from product_strategy_agent.adapters.documents.media import (
    mp4_duration,
    png_dimensions,
    wav_duration,
)
from product_strategy_agent.adapters.persistence.files.case_access import case_access
from product_strategy_agent.adapters.persistence.files.paths import confined
from product_strategy_agent.adapters.persistence.files.source_search_repository import (
    read_bounded,
)
from product_strategy_agent.domain.projects.media_review import (
    check_media_review,
    media_manifest,
)


def prepare_media(projects_dir, project_id, selection):
    name = selection.path
    path = PurePosixPath(name)
    media_format = path.suffix.lower().removeprefix(".")
    if (
        path.is_absolute()
        or ".." in path.parts
        or any(char in name for char in "\\:\x00")
        or media_format not in {"png", "wav", "mp4"}
    ):
        raise ValueError("Select a case-relative PNG, PCM WAV or non-fragmented MP4")
    with case_access(projects_dir, project_id) as case:
        state = json.loads(read_bounded(confined(case, "state.json"), 512000))
        if not isinstance(state, dict) or state.get("project_id") != project_id:
            raise ValueError("Invalid media review workspace")
        target = confined(case, path.as_posix())
        if not target.is_file():
            raise ValueError("Selected media file is unavailable")
        limit = (5 if media_format == "png" else 20) * 1024 * 1024
        data = read_bounded(target, limit)
        metadata = {
            "media_format": media_format,
            "content_sha256": sha256(data).hexdigest(),
        }
        if media_format == "png":
            metadata["width_px"], metadata["height_px"] = png_dimensions(data)
        else:
            duration = (
                wav_duration(data) if media_format == "wav" else mp4_duration(data)
            )
            if not 1 <= duration <= 86400000:
                raise ValueError("Media duration must be between 1 ms and 24 hours")
            metadata["duration_ms"] = duration
            metadata["duration_basis"] = (
                "pcm_frames" if media_format == "wav" else "mp4_movie_header"
            )
        return media_manifest(project_id, selection, metadata)


def inspect_media_review(projects_dir, project_id, review):
    manifest = prepare_media(projects_dir, project_id, review.selection)
    return check_media_review(manifest, review)
