from pathlib import Path
import struct
from tempfile import TemporaryDirectory
import unittest
from zlib import compress, crc32

from product_strategy_agent.adapters.persistence.files.ux_reader import (
    inspect_ux_review,
    prepare_ux,
)
from product_strategy_agent.cli import init_project
from product_strategy_agent.domain.projects.ux_review import Journey, UXReview


def png(width, height, value):
    def chunk(kind, body):
        return (
            struct.pack(">I", len(body))
            + kind
            + body
            + struct.pack(">I", crc32(kind + body))
        )

    header = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    pixels = (b"\x00" + bytes([value]) * width) * height
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", compress(pixels))
        + chunk(b"IEND", b"")
    )


class UXReviewTests(unittest.TestCase):
    def test_bounds_and_screenshot_binding_on_a_two_step_walkthrough(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            case = init_project("fixture", root / "projects")
            shot = case / "screen.png"
            shot.write_bytes(png(20, 30, 240))
            journey = Journey(
                user_goal="Reschedule a fixture appointment",
                steps=[
                    {
                        "step_id": "choose",
                        "task": "Choose a fixture time",
                        "screenshot": "screen.png",
                    },
                    {
                        "step_id": "confirm",
                        "task": "Confirm the time",
                        "screenshot": "screen.png",
                    },
                ],
            )
            manifest = prepare_ux(case.parent, case.name, journey)
            self.assertEqual(manifest["steps"][0]["width_px"], 20)
            self.assertEqual(manifest["steps"][0]["height_px"], 30)
            observation = {
                "step_id": "choose",
                "region": {"x": 10, "y": 22, "width": 10, "height": 8},
                "aspect": "hierarchy",
                "visible_observation": "Fixture observation.",
                "hypothesis": "The available time might be hard to notice.",
                "verification": "Observe a permitted task completion.",
            }

            def check(observations):
                draft = UXReview(
                    journey=journey,
                    manifest_sha256=manifest["manifest_sha256"],
                    observations=observations,
                )
                return inspect_ux_review(case.parent, case.name, draft)

            events = (case / "events.jsonl").read_bytes()
            self.assertEqual(
                check([observation])["steps_without_observations"], ["confirm"]
            )
            self.assertEqual((case / "events.jsonl").read_bytes(), events)
            with self.assertRaisesRegex(ValueError, "outside the screenshot"):
                check(
                    [{**observation, "region": {**observation["region"], "width": 11}}]
                )
            with self.assertRaisesRegex(ValueError, "outside the journey"):
                check([{**observation, "step_id": "other"}])
            shot.write_bytes(png(20, 30, 225))
            with self.assertRaisesRegex(ValueError, "fresh manifest"):
                check([observation])
            external = journey.steps[0].model_copy(
                update={"screenshot": "../outside.png"}
            )
            with self.assertRaisesRegex(ValueError, "case-relative"):
                prepare_ux(
                    case.parent,
                    case.name,
                    journey.model_copy(update={"steps": [external]}),
                )
            shot.write_bytes(b"not a png")
            with self.assertRaisesRegex(ValueError, "header is invalid"):
                prepare_ux(case.parent, case.name, journey)
