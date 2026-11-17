"""Canonical parent aliases must not weaken the case's lexical link boundary."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from product_strategy_agent.adapters.persistence.files.paths import confined


class ConfinedPathTests(unittest.TestCase):
    def test_os_managed_ancestor_alias_uses_the_same_canonical_root(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "alias" / "case"
            root.mkdir(parents=True)
            physical = Path(folder) / "physical"
            original = Path.resolve

            def resolved(path, *args, **kwargs):
                if path.is_relative_to(root.parent):
                    return physical / path.relative_to(root.parent)
                return original(path, *args, **kwargs)

            with patch.object(Path, "resolve", resolved):
                self.assertEqual(
                    confined(root, "sources/current.txt"), root / "sources/current.txt"
                )

    def test_root_and_internal_links_remain_forbidden_even_when_confined(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            for linked in (root, root / "sources"):
                with (
                    self.subTest(linked=linked),
                    patch.object(Path, "is_symlink", lambda path: path == linked),
                    self.assertRaisesRegex(ValueError, "symlinks or junctions"),
                ):
                    confined(root, "sources/current.txt")

    def test_lexical_escape_and_resolved_escape_still_refuse(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ("../outside", str(root / "absolute")):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    confined(root, name)
            original = Path.resolve

            def escaped(path, *args, **kwargs):
                return (
                    root.parent / "outside"
                    if path == root / "source"
                    else original(path, *args, **kwargs)
                )

            with (
                patch.object(Path, "resolve", escaped),
                self.assertRaisesRegex(ValueError, "escaped"),
            ):
                confined(root, "source")


if __name__ == "__main__":
    unittest.main()
