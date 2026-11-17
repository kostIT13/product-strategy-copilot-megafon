"""The Git index must replay hashed demos with either checkout newline policy."""

from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest

from scripts.ci.demo import CASES, strict_evidence

ROOT = Path(__file__).resolve().parents[1]


def git(root, *args, **kwargs):
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, **kwargs
    )


class DemoCheckoutTests(unittest.TestCase):
    def test_git_checkout_preserves_manifest_and_source_hashes_with_both_autocrlf_modes(
        self,
    ):
        # Use staged/index bytes, never local working-tree copies: that is where
        # Windows autocrlf used to hide the broken Linux fixtures.
        paths = git(
            ROOT,
            "ls-files",
            "-z",
            ".gitattributes",
            "projects/demo",
            "projects/table-demo",
        ).stdout
        self.assertIn(b".gitattributes\0", paths)
        with TemporaryDirectory() as folder:
            repository = Path(folder) / "repo"
            repository.mkdir()
            git(
                ROOT,
                "checkout-index",
                "--stdin",
                "-z",
                "--prefix=" + repository.as_posix() + "/",
                input=paths,
            )
            git(repository, "init", "-q")
            git(repository, "-c", "core.autocrlf=false", "add", ".")
            for mode in ("false", "true"):
                output = Path(folder) / mode
                output.mkdir()
                git(
                    repository,
                    "-c",
                    "core.autocrlf=" + mode,
                    "checkout-index",
                    "--all",
                    "--prefix=" + output.as_posix() + "/",
                )
                for case in CASES:
                    with self.subTest(mode=mode, case=case):
                        self.assertGreater(
                            strict_evidence(output / "projects" / case), 0
                        )


if __name__ == "__main__":
    unittest.main()
