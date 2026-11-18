"""Read explicitly selected local PNG screenshots and capture their identity."""

from hashlib import sha256
import json
from pathlib import PurePosixPath
import struct
from zlib import crc32

from product_strategy_agent.adapters.persistence.files.case_access import case_access
from product_strategy_agent.adapters.persistence.files.paths import confined
from product_strategy_agent.adapters.persistence.files.source_search_repository import (
    read_bounded,
)
from product_strategy_agent.domain.projects.ux_review import (
    check_ux_review,
    journey_manifest,
)

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_TOTAL_BYTES = 20 * 1024 * 1024


def _png_dimensions(data):
    if len(data) < 33 or data[:16] != PNG_SIGNATURE + b"\x00\x00\x00\x0dIHDR":
        raise ValueError("PNG screenshot header is invalid")
    if crc32(data[12:29]) != int.from_bytes(data[29:33], "big"):
        raise ValueError("PNG screenshot header checksum is invalid")
    width, height = struct.unpack(">II", data[16:24])
    if not (1 <= width <= 8192 and 1 <= height <= 8192):
        raise ValueError("PNG screenshot dimensions exceed the supported bounds")
    return width, height


def prepare_ux(projects_dir, project_id, journey):
    with case_access(projects_dir, project_id) as case:
        state = json.loads(read_bounded(confined(case, "state.json"), 512000))
        if not isinstance(state, dict) or state.get("project_id") != project_id:
            raise ValueError("Invalid UX review workspace")
        screens = {}
        total = 0
        for step in journey.steps:
            name = step.screenshot
            path = PurePosixPath(name)
            if (
                path.is_absolute()
                or ".." in path.parts
                or path.suffix.lower() != ".png"
                or any(char in name for char in "\\:\x00")
            ):
                raise ValueError(
                    "Use a case-relative path to an explicitly selected PNG"
                )
            normal = path.as_posix()
            if normal in screens:
                screens[name] = screens[normal]
                continue
            target = confined(case, normal)
            if not target.is_file():
                raise ValueError("Selected PNG screenshot is unavailable")
            data = read_bounded(target, min(MAX_IMAGE_BYTES, MAX_TOTAL_BYTES - total))
            total += len(data)
            width, height = _png_dimensions(data)
            screens[normal] = screens[name] = {
                "screenshot_sha256": sha256(data).hexdigest(),
                "width_px": width,
                "height_px": height,
            }
        return journey_manifest(project_id, journey, screens)


def inspect_ux_review(projects_dir, project_id, review):
    return check_ux_review(prepare_ux(projects_dir, project_id, review.journey), review)
