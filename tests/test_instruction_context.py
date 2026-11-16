"""Deliver actual stage-scoped canon, detect adapter drift and keep case state untouched."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from scripts.sync_harness import sync
from scripts.release.package import allowed
from product_strategy_agent.cli import init_project
from product_strategy_agent.application.services.instruction_context_service import instruction_context

ROOT = Path(__file__).resolve().parents[1]


def canon(folder):
    root = Path(folder) / "repository"
    root.mkdir()
    for name in ("agent", "knowledge", ".agents"):
        shutil.copytree(ROOT / name, root / name)
    shutil.copy2(ROOT / "AGENTS.md", root / "AGENTS.md")
    return root


class InstructionContextTests(unittest.TestCase):
    def test_navigation_is_loaded_hashed_and_missing_material_fails_without_case_writes(self):
        with TemporaryDirectory() as folder:
            root = canon(folder)
            manifest_path = root / "agent/harness.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest.update(bundle_version="1.1.0", navigation=["agent/README.md", "agent/automation.md"])
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            (root / "agent/automation.md").write_text("Synthetic navigation only.\n", encoding="utf-8")
            project = init_project("case", root / "projects")
            before = {str(path): path.read_bytes() for path in project.rglob("*") if path.is_file()}
            sync(root, write=True)
            first = instruction_context(project, root)
            paths = {item["path"] for item in first["instructions"]}
            self.assertTrue({"agent/README.md", "agent/automation.md"} <= paths)
            self.assertEqual(first["bundle_version"], "1.1.0")
            navigation = root / "agent/automation.md"
            navigation.write_text(navigation.read_text(encoding="utf-8") + "\nChanged automation policy.\n", encoding="utf-8")
            self.assertNotEqual(first["context_hash"], instruction_context(project, root)["context_hash"])
            self.assertFalse(sync(root)["ok"])
            navigation.unlink()
            with self.assertRaises(FileNotFoundError):
                instruction_context(project, root)
            with self.assertRaises(FileNotFoundError):
                sync(root)
            self.assertEqual(before, {str(path): path.read_bytes() for path in project.rglob("*") if path.is_file()})

    def test_navigation_rejects_role_autoload_escape_duplicates_and_preserves_legacy_manifest(self):
        with TemporaryDirectory() as folder:
            root = canon(folder)
            project = init_project("case", root / "projects")
            manifest_path = root / "agent/harness.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for navigation in (["../private.md"], ["agent/roles/critic.md"],
                               ["agent/README.md"] * 2, [["agent/README.md"]]):
                with self.subTest(navigation=navigation):
                    manifest_path.write_text(json.dumps({**manifest, "navigation": navigation}), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        instruction_context(project, root)
                    with self.assertRaises(ValueError):
                        sync(root)
            legacy = {key: value for key, value in manifest.items() if key != "navigation"}
            legacy["bundle_version"] = "1.0.0"
            manifest_path.write_text(json.dumps(legacy), encoding="utf-8")
            packet = instruction_context(project, root)
            self.assertEqual(packet["bundle_version"], "1.0.0")
            self.assertFalse(any(item["path"] in {"agent/README.md", "agent/automation.md"} for item in packet["instructions"]))

    def test_role_guidance_is_canonical_but_does_not_auto_load_in_case_context(self):
        with TemporaryDirectory() as folder:
            root = canon(folder)
            project = init_project("case", root / "projects")
            sync(root, write=True)
            path = root / "agent/roles/critic.md"
            path.write_text(path.read_text(encoding="utf-8") + "\nChanged role guidance.\n", encoding="utf-8")
            self.assertFalse(sync(root)["ok"])
            sync(root, write=True)
            self.assertTrue(sync(root)["ok"])
            packet = instruction_context(project, root)
            self.assertFalse(any(row["path"].startswith("agent/roles/") for row in packet["instructions"]))
            self.assertFalse(any(row["path"].startswith("agent/hosts/") for row in packet["instructions"]))
            self.assertFalse(packet["host_loading_verified"])

    def test_stage_selects_full_versioned_materials_without_writes(self):
        with TemporaryDirectory() as folder:
            root = canon(folder)
            project = init_project("case", root / "projects")
            before = {str(path): path.read_bytes() for path in project.rglob("*") if path.is_file()}
            packet = instruction_context(project, root)
            self.assertEqual(packet["stage"], "intake")
            self.assertEqual({item["id"] for item in packet["knowledge"]}, {"M-SEGMENT-01", "C-EVIDENCE-01"})
            for item in [*packet["instructions"], *packet["knowledge"]]:
                self.assertEqual(item["text"], (root / item["path"]).read_bytes().decode("utf-8"))
                self.assertEqual(item["sha256"], hashlib.sha256((root / item["path"]).read_bytes()).hexdigest())
            self.assertEqual(before, {str(path): path.read_bytes() for path in project.rglob("*") if path.is_file()})
            self.assertFalse(packet["host_loading_verified"])
            self.assertEqual(packet["model_calls"], 0)

    def test_context_changes_with_state_and_selected_knowledge_and_survives_copy(self):
        with TemporaryDirectory() as folder:
            root = canon(folder)
            project = init_project("case", root / "projects")
            first = instruction_context(project, root)
            copied = Path(folder) / "copy" / "case"
            shutil.copytree(project, copied)
            self.assertEqual(first, instruction_context(copied, root))
            state = json.loads((project / "state.json").read_text())
            state["status"] = "options"
            (project / "state.json").write_text(json.dumps(state))
            second = instruction_context(project, root)
            self.assertNotEqual(first["context_hash"], second["context_hash"])
            self.assertIn("M-OPTIONS-01", {item["id"] for item in second["knowledge"]})
            material = root / second["knowledge"][0]["path"]
            material.write_text(material.read_text(encoding="utf-8") + "\nChanged guidance\n", encoding="utf-8")
            self.assertNotEqual(second["context_hash"], instruction_context(project, root)["context_hash"])

    def test_missing_material_corrupt_state_and_escaped_catalog_fail_closed(self):
        with TemporaryDirectory() as folder:
            root = canon(folder)
            project = init_project("case", root / "projects")
            catalog = json.loads((root / "knowledge/catalog.json").read_text(encoding="utf-8"))
            broken = deepcopy(catalog)
            next(item for item in broken["documents"] if item["id"] == "M-SEGMENT-01")["path"] = "../private.md"
            (root / "knowledge/catalog.json").write_text(json.dumps(broken), encoding="utf-8")
            with self.assertRaises(ValueError):
                instruction_context(project, root)
            (root / "knowledge/catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
            (root / ".agents/skills/psa-research/SKILL.md").unlink()
            with self.assertRaises(FileNotFoundError):
                instruction_context(project, root)
            (project / "state.json").write_text('{"schema_version": 99, "status": "intake"}')
            with self.assertRaises(ValueError):
                instruction_context(project, root)

    def test_sync_check_detects_canon_changes_generated_edits_and_stale_copies(self):
        with TemporaryDirectory() as folder:
            root = canon(folder)
            self.assertFalse(sync(root)["ok"])
            self.assertTrue(sync(root, write=True)["ok"])
            self.assertTrue(sync(root)["ok"])
            path = root / "AGENTS.md"
            path.write_text(path.read_text(encoding="utf-8") + "\nChanged canon\n", encoding="utf-8")
            self.assertFalse(sync(root)["ok"])
            self.assertTrue(sync(root, write=True)["ok"])
            derived = root / ".claude/skills/psa-options/SKILL.md"
            derived.write_text(derived.read_text(encoding="utf-8") + "drift", encoding="utf-8")
            self.assertIn(".claude/skills/psa-options/SKILL.md", sync(root)["differences"])
            sync(root, write=True)
            extra = root / ".claude/skills/psa-retired/SKILL.md"
            extra.parent.mkdir()
            extra.write_text("retired")
            self.assertEqual(sync(root)["stale"], [".claude/skills/psa-retired/SKILL.md"])

    def test_unmanaged_adapter_is_not_overwritten(self):
        with TemporaryDirectory() as folder:
            root = canon(folder)
            (root / "CLAUDE.md").write_text("User instructions")
            with self.assertRaises(ValueError):
                sync(root, write=True)
            self.assertEqual((root / "CLAUDE.md").read_text(), "User instructions")

    def test_real_cli_context_from_another_directory_uses_explicit_roots(self):
        with TemporaryDirectory() as folder:
            project = init_project("case", Path(folder) / "cases")
            output = subprocess.check_output([sys.executable, "-m", "product_strategy_agent.cli", "context", "case",
                "--projects-dir", str(project.parent), "--instructions-root", str(ROOT)], cwd=folder)
            packet = json.loads(output)
            self.assertEqual(packet, instruction_context(project, ROOT))

    def test_distribution_allows_only_intended_hidden_instruction_files(self):
        for path in ("AGENTS.md", "CLAUDE.md", "agent/harness.json", "agent/hosts/catalog.json", ".agents/skills/psa-research/SKILL.md",
                     ".claude/skills/psa-research/SKILL.md", ".cursor/rules/product-strategy.mdc", ".codex/README.md"):
            self.assertTrue(allowed(path), path)
        for path in (".codex/auth.json", ".claude/settings.local.json", ".agents/.env", ".cursor/mcp.json"):
            self.assertFalse(allowed(path), path)
