"""Unsupported namespaces never become empty history or permission to overwrite."""

from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4

from product_strategy_agent.adapters.persistence.files.task_journal_store import (
    FileTaskJournalStore,
)
from product_strategy_agent.adapters.persistence.files.hook_run_store import (
    FileHookRunStore,
)
from product_strategy_agent.adapters.persistence.files.host_config_store import (
    FileHostConfigStore,
)
from product_strategy_agent.interfaces.host_config import host_config
from test_file_promises import contents
from test_host_config import prepare, request, config
from test_host_profiles import fixture
from test_journal_directory_bounds import stores


def probes(store, case_scoped):
    identifier = uuid4()
    calls = [lambda: store.pending("case") if case_scoped else store.pending()]
    if isinstance(store, FileTaskJournalStore):
        calls += [
            lambda: store.task("case", identifier),
            lambda: store.recover("case", "task", identifier),
        ]
    elif isinstance(store, FileHookRunStore):
        calls += [lambda: store.read("case", identifier)]
    elif isinstance(store, FileHostConfigStore):
        calls += [lambda: store.load(identifier), store.audit, store.ready]
    else:
        calls += [lambda: store.read(identifier), lambda: store.recover(identifier)]
    return calls


class JournalVersionTests(unittest.TestCase):
    def test_future_mixed_malformed_and_noncanonical_namespaces_preserve_all_bytes(
        self,
    ):
        for shape in ("future_only", "mixed", "version_file", "alias", "unknown_entry"):
            with self.subTest(shape=shape), TemporaryDirectory() as folder:
                for index in range(5):
                    root = Path(folder).resolve() / str(index)
                    root.mkdir()
                    store, journal, scoped = stores(root)[index]
                    with self.subTest(store=type(store).__name__):
                        version = (
                            journal.parent
                            if isinstance(store, FileTaskJournalStore)
                            else journal
                        )
                        version.parent.mkdir(parents=True, exist_ok=True)
                        if shape == "version_file":
                            version.write_bytes(b"PRIVATE-NAMESPACE-SENTINEL")
                        elif shape == "unknown_entry":
                            (version.parent / "PRIVATE-NAMESPACE-NAME").write_bytes(
                                b"unrecognized"
                            )
                        else:
                            unknown = version.parent / (
                                "V1" if shape == "alias" else "v2"
                            )
                            unknown.mkdir()
                            (unknown / "PRIVATE-NAMESPACE-SENTINEL").write_bytes(
                                b"future bytes"
                            )
                            if shape == "mixed":
                                version.mkdir()
                        # Warm the participating lock; failures must preserve the journal itself.
                        if scoped:
                            with store.access("case"):
                                pass
                        before = contents(root)
                        for callback in probes(store, scoped):
                            with self.assertRaisesRegex(
                                ValueError, "unsupported journal namespace"
                            ) as failure:
                                callback()
                            self.assertNotIn("PRIVATE", str(failure.exception))
                        self.assertEqual(contents(root), before)

    def test_missing_and_known_empty_v1_are_supported_without_creating_history(self):
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            for store, journal, scoped in stores(root):
                for existing in (False, True):
                    if existing:
                        journal.mkdir(parents=True, exist_ok=True)
                    packet = store.pending("case") if scoped else store.pending()
                    self.assertFalse(next(iter(packet.values())))
                    self.assertEqual(journal.exists(), existing)

    def test_future_namespace_blocks_apply_replay_and_recovery_but_compatible_backup_replays(
        self,
    ):
        with TemporaryDirectory() as folder:
            root = fixture(folder)
            app = host_config(root)
            command = prepare(app, request())
            receipt = app.apply(command)["receipt"]
            backup = Path(folder) / "compatible-backup"
            shutil.copytree(root, backup)
            future = root / ".psa/host-config/v2"
            future.mkdir()
            (future / "future.bin").write_bytes(b"PRIVATE-FUTURE-BYTES")
            unchanged = contents(root)
            for callback in (
                lambda: app.apply(command),
                lambda: app.plan(request()),
                lambda: app.recover(command.operation_id),
                app.audit,
            ):
                with self.assertRaisesRegex(
                    ValueError, "unsupported journal namespace"
                ):
                    callback()
                self.assertEqual(contents(root), unchanged)
            copied = host_config(backup)
            before = contents(backup)
            self.assertEqual(copied.apply(command)["receipt"], receipt)
            self.assertEqual(copied.recover(command.operation_id)["receipt"], receipt)
            self.assertTrue(copied.audit()["integrity_ok"])
            self.assertEqual(contents(backup), before)
            self.assertEqual(config(backup).read_bytes(), config(root).read_bytes())
