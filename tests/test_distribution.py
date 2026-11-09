"""Release boundaries: version drift, unwanted files, tampering and unsafe ZIPs."""
import json
from pathlib import Path
import stat
from tempfile import TemporaryDirectory
import unittest
import zipfile

from scripts.release.package import allowed, digest, version_for
from scripts.release.verify import unpack_checked, verify


class DistributionChecks(unittest.TestCase):
    def test_allowlist_excludes_runtime_and_unrelated_projects(self):
        for name in ('.env', 'src/.env.local', 'knowledge/.env.local', 'backups/db.sql', '.venv/config', 'projects/private/data.md', '../README.md', 'src/__pycache__/cache.pyc'):
            self.assertFalse(allowed(name), name)
        for name in ('README.md', '.env.example', 'projects/demo/sources/source.txt', 'knowledge/methods/segmentation.md'):
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
        with TemporaryDirectory() as folder:
            root = Path(folder)
            names = ('release.zip', 'release-manifest.json', 'package.whl', 'package.tar.gz')
            for name in names:
                (root / name).write_bytes(b'original')
            (root / 'SHA256SUMS').write_text(''.join(f'{digest(b"original")}  {name}\n' for name in names), encoding='utf-8')
            (root / 'package.whl').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'asset checksum mismatch'):
                verify(root / 'release.zip', '3.12')
