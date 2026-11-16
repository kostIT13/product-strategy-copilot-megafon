"""Lazy directory budgets and real link refusal preserve all journal bytes."""

from pathlib import Path
import os
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from product_strategy_agent.adapters.persistence.files.directory_bounds import (
    bounded_entries,
)
from product_strategy_agent.adapters.persistence.files.host_acceptance_store import (
    FileHostAcceptanceStore,
)
from product_strategy_agent.adapters.persistence.files.host_review_store import (
    FileHostReviewStore,
)
from product_strategy_agent.adapters.persistence.files.host_config_store import (
    FileHostConfigStore,
)
from product_strategy_agent.adapters.persistence.files.hook_run_store import (
    FileHookRunStore,
)
from product_strategy_agent.adapters.persistence.files.task_journal_store import (
    FileTaskJournalStore,
)


class Scan:
    def __init__(self, size, marker=False):
        self.size, self.marker = size, marker
        self.visited = 0
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.closed = True

    def __iter__(self):
        if self.marker:
            self.visited += 1
            yield SimpleNamespace(name="ACTIVE.json")
        for index in range(self.size):
            self.visited += 1
            yield SimpleNamespace(name=f"{index:032x}.json")


def stores(root):
    case = root / "case"
    case.mkdir()
    (case / "state.json").write_bytes(b"{}")
    return [
        (FileTaskJournalStore(root), case / ".psa/workflow/subagents/v1/tasks", True),
        (FileHookRunStore(root), case / ".psa/workflow/hooks/v1", True),
        (FileHostAcceptanceStore(root), root / ".psa/host-acceptance/v1", False),
        (FileHostReviewStore(root), root / ".psa/host-acceptance/reviews/v1", False),
        (FileHostConfigStore(root), root / ".psa/host-config/v1", False),
    ]


class DirectoryBoundTests(unittest.TestCase):
    def test_scan_stops_on_first_excess_entry_and_closes_without_truncation(self):
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            for marker in (False, True):
                scan = Scan(1000000, marker)
                with patch("os.scandir", return_value=scan):
                    with self.assertRaisesRegex(ValueError, "limit"):
                        bounded_entries(root, 1000, ignore=("ACTIVE.json",))
                self.assertEqual(scan.visited, 1001 + int(marker))
                self.assertTrue(scan.closed)
            scan = Scan(1000, True)
            with patch("os.scandir", return_value=scan):
                self.assertEqual(
                    len(bounded_entries(root, 1000, ignore=("ACTIVE.json",))), 1000
                )
            self.assertTrue(scan.closed)

    def test_all_pending_adapters_refuse_oversized_history_before_opening_records(self):
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            for store, journal, case_scoped in stores(root):
                with self.subTest(store=type(store).__name__):
                    journal.mkdir(parents=True)
                    scan = Scan(1000000)
                    original = os.scandir
                    with patch(
                        "os.scandir",
                        side_effect=lambda path: (
                            scan if Path(path) == journal else original(path)
                        ),
                    ):
                        with self.assertRaises(ValueError):
                            store.pending("case") if case_scoped else store.pending()
                    self.assertEqual(scan.visited, 1001)
                    self.assertTrue(scan.closed)
                    self.assertEqual(list(journal.iterdir()), [])

    def test_real_external_link_including_final_record_is_rejected_without_reading_target(
        self,
    ):
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve() / "workspace"
            root.mkdir()
            external = Path(folder).resolve() / "external"
            external.mkdir()
            sentinel = external / "PRIVATE-CONTENT.json"
            sentinel.write_bytes(b"not a journal record")
            for store, journal, case_scoped in stores(root):
                with self.subTest(store=type(store).__name__):
                    journal.mkdir(parents=True)
                    # A final-looking name used to be skipped by pending() without confinement.
                    link = journal / (uuid4().hex + ".json")
                    if os.name == "nt":
                        import _winapi

                        _winapi.CreateJunction(str(external), str(link))
                    else:
                        link.symlink_to(external, target_is_directory=True)
                    try:
                        with self.assertRaisesRegex(
                            ValueError, "root|symlink|junction"
                        ):
                            store.pending("case") if case_scoped else store.pending()
                        self.assertEqual(sentinel.read_bytes(), b"not a journal record")
                        self.assertEqual(len(list(external.iterdir())), 1)
                    finally:
                        link.rmdir() if os.name == "nt" else link.unlink()

    def test_ignored_marker_and_internal_links_still_receive_path_checks(self):
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            target = root / "inside"
            target.mkdir()
            link = root / "ACTIVE.json"
            if os.name == "nt":
                import _winapi

                _winapi.CreateJunction(str(target), str(link))
            else:
                link.symlink_to(target, target_is_directory=True)
            try:
                with self.assertRaisesRegex(ValueError, "symlink|junction"):
                    bounded_entries(root, 1000, ignore=("ACTIVE.json",))
            finally:
                link.rmdir() if os.name == "nt" else link.unlink()
