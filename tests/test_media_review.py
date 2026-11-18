from pathlib import Path
import struct
from tempfile import TemporaryDirectory
import unittest
import wave

from product_strategy_agent.adapters.persistence.files.media_reader import (
    inspect_media_review,
    prepare_media,
)
from product_strategy_agent.cli import init_project
from product_strategy_agent.domain.projects.media_review import (
    MediaReview,
    MediaSelection,
)
from test_ux_review import png


def mp4_metadata_fixture(handler=b"vide"):
    def box(name, content):
        return struct.pack(">I4s", len(content) + 8, name) + content

    header = bytes(12) + struct.pack(">II", 1000, 2500) + bytes(80)
    track = box(b"trak", box(b"mdia", box(b"hdlr", bytes(8) + handler + bytes(12))))
    return (
        box(b"ftyp", b"isom" + bytes(4) + b"isom")
        + box(b"moov", box(b"mvhd", header) + track)
        + box(b"mdat", b"fixture media bytes")
    )


class MediaReviewTests(unittest.TestCase):
    def test_file_identity_and_observation_bounds_for_supported_media(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            case = init_project("fixture", root / "projects")
            (case / "image.png").write_bytes(png(20, 30, 180))
            (case / "video.mp4").write_bytes(mp4_metadata_fixture())
            with wave.open(str(case / "audio.wav"), "wb") as writer:
                writer.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
                writer.writeframes(bytes(16000))
            cases = [
                (
                    "image.png",
                    {"x": 10, "y": 20, "width": 10, "height": 10},
                    "visual_review",
                    {"x": 10, "y": 20, "width": 11, "height": 10},
                    "width_px",
                    20,
                ),
                (
                    "audio.wav",
                    {"start_ms": 0, "end_ms": 1000},
                    "listening",
                    {"start_ms": 0, "end_ms": 1001},
                    "duration_ms",
                    1000,
                ),
                (
                    "video.mp4",
                    {"start_ms": 2000, "end_ms": 2500},
                    "visual_review",
                    {"start_ms": 2500, "end_ms": 2500},
                    "duration_ms",
                    2500,
                ),
            ]
            events = (case / "events.jsonl").read_bytes()
            for file, anchor, basis, invalid, key, value in cases:
                with self.subTest(file=file):
                    selection = MediaSelection(path=file)
                    manifest = prepare_media(case.parent, case.name, selection)
                    self.assertEqual(manifest[key], value)
                    obs = {
                        "anchor": anchor,
                        "basis": basis,
                        "observation": "Fixture observation.",
                        "limitation": "No behavioral inference from the fixture.",
                    }
                    review = MediaReview(
                        selection=selection,
                        manifest_sha256=manifest["manifest_sha256"],
                        observations=[obs],
                    )
                    self.assertTrue(
                        inspect_media_review(case.parent, case.name, review)[
                            "anchors_checked"
                        ]
                    )
                    invalid_review = MediaReview(
                        selection=selection,
                        manifest_sha256=manifest["manifest_sha256"],
                        observations=[{**obs, "anchor": invalid}],
                    )
                    with self.assertRaises(ValueError):
                        inspect_media_review(case.parent, case.name, invalid_review)
            self.assertEqual((case / "events.jsonl").read_bytes(), events)
            (case / "video.mp4").write_bytes(mp4_metadata_fixture(b"soun"))
            with self.assertRaisesRegex(ValueError, "video track"):
                prepare_media(case.parent, case.name, MediaSelection(path="video.mp4"))
            (case / "video.mp4").write_bytes(mp4_metadata_fixture() + b"\x00")
            with self.assertRaisesRegex(ValueError, "Truncated"):
                prepare_media(case.parent, case.name, MediaSelection(path="video.mp4"))
            with self.assertRaisesRegex(ValueError, "case-relative"):
                prepare_media(
                    case.parent, case.name, MediaSelection(path="../outside.wav")
                )
