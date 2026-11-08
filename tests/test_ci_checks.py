"""Negative cases for repository gates: links, file history and evidence replay."""
import json
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest

from scripts.ci.demo import snapshot, strict_evidence, run_demo
from scripts.ci.docs import check_docs, parse_document, REQUIRED
from scripts.ci.repository import check_repository, forbidden_path


class DocumentationChecks(unittest.TestCase):
    def test_reference_links_fences_duplicate_headings_and_unicode(self):
        anchors, links = parse_document('# Пример *текста*\n# Пример текста\n[x][ref]\n\n[ref]: other.md#target\n\n```md\n[x](missing.md)\n```\n')
        self.assertEqual(anchors, {'пример-текста', 'пример-текста-1'})
        self.assertEqual(links, ['other.md#target'])

    def test_broken_target_anchor_escape_and_missing_required_file(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            for name in REQUIRED:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('', encoding='utf-8')
            (root / 'README.md').write_text('[bad](missing.md) [anchor](target.md#absent) [escape](../outside.md)', encoding='utf-8')
            (root / 'target.md').write_text('# Present', encoding='utf-8')
            errors, _ = check_docs(root, ['README.md', 'target.md'])
            self.assertEqual(len(errors), 3)
            (root / 'uv.lock').unlink()
            self.assertTrue(any('required' in error for error in check_docs(root, [])[0]))


class RepositoryChecks(unittest.TestCase):
    def test_local_runtime_policy_allows_only_env_example(self):
        for name in ('.env', 'nested/.env.production', '.ENV.production', 'backups/data.sql', '.venv-ci/config', 'data.sqlite3'):
            self.assertTrue(forbidden_path(name), name)
        self.assertFalse(forbidden_path('.env.example'))
        self.assertFalse(forbidden_path('.environment.md'))

    def test_deleted_env_in_history_is_rejected(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            subprocess.run(['git', 'init', '-q', folder], check=True, capture_output=True)
            (root / '.env').write_text('EXAMPLE=not-a-secret', encoding='utf-8')
            subprocess.run(['git', '-C', folder, 'add', '.env'], check=True, capture_output=True)
            subprocess.run(['git', '-C', folder, '-c', 'user.name=CI', '-c', 'user.email=ci@example.invalid',
                            'commit', '-qm', 'fixture'], check=True, capture_output=True)
            subprocess.run(['git', '-C', folder, 'rm', '-q', '.env'], check=True, capture_output=True)
            self.assertEqual(check_repository(root), [])
            self.assertEqual(check_repository(root, history=True), ['.env'])


class DemoChecks(unittest.TestCase):
    def test_replay_keeps_original_corpus_unchanged(self):
        root = Path(__file__).resolve().parents[1]
        before = snapshot(root / 'projects' / 'demo')
        report = run_demo(root)
        self.assertEqual(report['model_calls'], 0)
        self.assertEqual(len(report['cases']), 2)
        self.assertTrue(all(case['render_revalidated'] for case in report['cases']))
        self.assertEqual(snapshot(root / 'projects' / 'demo'), before)

    def test_bad_quote_and_unverifiable_locator_fail_strict_check(self):
        root = Path(__file__).resolve().parents[1]
        with TemporaryDirectory() as folder:
            project = Path(folder) / 'demo'
            shutil.copytree(root / 'projects' / 'demo', project)
            registry = project / 'claims.jsonl'
            original = registry.read_text(encoding='utf-8')
            claims = [json.loads(line) for line in original.splitlines() if line.strip()]
            cited = next(claim for claim in claims if claim.get('source_ids'))
            for field, value in (('quotes', 'Deliberately wrong quote'), ('source_locators', 'unsupported:1')):
                rows = json.loads(json.dumps(claims))
                row = next(row for row in rows if row['claim_id'] == cited['claim_id'])
                row[field][0] = value
                registry.write_text('\n'.join(json.dumps(item, ensure_ascii=False) for item in rows) + '\n', encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'quote does not match' if field == 'quotes' else 'not supported'):
                    strict_evidence(project)
