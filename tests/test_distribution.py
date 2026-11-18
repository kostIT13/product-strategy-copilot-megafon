"""Release boundaries: version drift, unwanted files, tampering and unsafe ZIPs."""
import json
from pathlib import Path
import stat
from tempfile import TemporaryDirectory
import unittest
import zipfile

from scripts.release.package import allowed, digest, version_for
from scripts.release.verify import unpack_checked, verify
from product_strategy_agent.domain.release_policy import SLOT_EXAMPLE_FILES


class DistributionChecks(unittest.TestCase):
    def test_slot_archive_accepts_complete_example_and_refuses_partial_or_private_data(self):
        from test_release_hooks import fixture

        root = Path(__file__).resolve().parents[1]
        files = {name: (root / name).read_bytes() for name in SLOT_EXAMPLE_FILES}
        with TemporaryDirectory() as folder:
            output = Path(folder)
            archive = fixture(output / "complete", extra=files)
            extracted = unpack_checked(archive, output / "extracted")
            for name, data in files.items():
                self.assertEqual((extracted / name).read_bytes(), data)
            partial = fixture(output / "partial", extra={"examples/slot-workshop/README.md": b"only the readme"})
            with self.assertRaisesRegex(ValueError, "incomplete Slot"):
                unpack_checked(partial, output / "rejected")
            for name in ("examples/private/notes.md", "examples/slot-workshop/notes.txt",
                         "examples/slot-workshop/materials/.env",
                         "projects/slot-workshop-synthetic/state.json"):
                self.assertFalse(allowed(name), name)

    def test_allowlist_excludes_runtime_and_unrelated_projects(self):
        for name in ('.env', 'src/.env.local', 'knowledge/.env.local', 'backups/db.sql', '.venv/config', 'projects/private/data.md', '../README.md', 'src/__pycache__/cache.pyc'):
            self.assertFalse(allowed(name), name)
        for name in ('README.md', '.env.example', '.gitattributes', 'projects/demo/sources/source.txt', 'knowledge/methods/segmentation.md'):
            self.assertTrue(allowed(name), name)

    def test_version_and_tag_must_match(self):
        root = Path(__file__).resolve().parents[1]
        version = version_for(root)
        self.assertEqual(version_for(root, f'v{version}'), version)
        with self.assertRaises(ValueError):
            version_for(root, 'v999.0.0')

    def test_manifest_detects_tampering_and_unexpected_files(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            archive = root / 'release.zip'
            for contents, extra in ((b'changed', False), (b'original', True)):
                with zipfile.ZipFile(archive, 'w') as bundle:
                    prefix = 'product-strategy-agent-0.1.0/'
                    bundle.writestr(prefix + 'README.md', contents)
                    bundle.writestr(prefix + 'release-manifest.json', json.dumps({'version':'0.1.0', 'files':{'README.md':digest(b'original')}}))
                    if extra:
                        bundle.writestr(prefix + 'unexpected.txt', 'extra')
                with self.assertRaises(ValueError):
                    unpack_checked(archive, root / 'out')

    def test_path_traversal_and_symlinks_are_rejected_before_extracting(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            for name, mode in (('../escape', 0), ('root/../escape', 0), ('root\\escape', 0), ('root/link', stat.S_IFLNK | 0o777)):
                archive = root / 'release.zip'
                with zipfile.ZipFile(archive, 'w') as bundle:
                    info = zipfile.ZipInfo(name)
                    info.external_attr = mode << 16
                    bundle.writestr(info, 'target')
                with self.assertRaises(ValueError):
                    unpack_checked(archive, root / 'out')
                self.assertFalse((root / 'out').exists())

    def test_changed_external_wheel_is_rejected_before_installation(self):
        from test_release_hooks import fixture
        from unittest.mock import patch

        with TemporaryDirectory() as folder:
            root = Path(folder)
            archive = fixture(root)
            next(root.glob("*.whl")).write_bytes(b"changed")
            with patch(
                "subprocess.run", side_effect=AssertionError("must not install")
            ):
                with self.assertRaisesRegex(
                    ValueError, "external distribution differs"
                ):
                    verify(archive, "3.12")
