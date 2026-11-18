"""Source judgement is snapshot-bound, recoverable and never approval."""

from contextlib import redirect_stdout
from io import StringIO
import json
import importlib.util
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import uuid4

from product_strategy_agent.cli import init_project, main
from product_strategy_agent.ledger import add_claim
from product_strategy_agent.application.services.source_quality_service import (
    inspect_source_quality,
)
from product_strategy_agent.sources import add_local_source
from product_strategy_agent.rendering import render_project
from product_strategy_agent.adapters.persistence.files.workflow_repository import (
    FileWorkflowStore,
)
from product_strategy_agent.adapters.persistence.files.source_reader import (
    FileWebSourceReader,
)
from product_strategy_agent.application.services.source_lifecycle_service import (
    SourceLifecycleService,
)
from product_strategy_agent.domain.projects.source_lifecycle import SourceWithdrawal
from product_strategy_agent.application.services.source_assessment_service import (
    SourceAssessmentService,
)
from product_strategy_agent.application.services.source_import_service import (
    SourceImportService,
)
from product_strategy_agent.application.services.workflow_recovery_service import (
    WorkflowRecoveryService,
)
from product_strategy_agent.domain.projects.source_assessment import SourceAssessment
from product_strategy_agent.domain.projects.source_import import SourceImport


class SourceAssessmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "projects"
        self.case = init_project("case", self.root)
        self.file = Path(self.temp.name) / "notes.txt"
        self.file.write_text("Synthetic interview notes.", encoding="utf-8")
        self.source = add_local_source(self.case, self.file)
        self.store = FileWorkflowStore(self.root)
        self.service = SourceAssessmentService(self.store)

    def request(self, **changes):
        current = self.service.inspect("case", self.source["source_id"])
        return dict(
            operation_id=str(uuid4()),
            source_id=current["source_id"],
            expected_workflow_version=current["workflow_version"],
            expected_content_hash=current["content_hash"],
            expected_source_record_hash=current["source_record_hash"],
            assessed_by="Synthetic reviewer",
            author=None,
            publisher_or_owner=None,
            published_at=None,
            reliability="low",
            reason="Uncorroborated synthetic interview",
            limitations=["Single interview"],
            unknowns=["Author and date unknown"],
            **changes,
        )

    def test_quality_tracks_used_sources_and_same_content_invalidation(self):
        identifier = self.source["source_id"]
        unused_file = self.file.with_name("unused.txt")
        unused_file.write_text("Unused fixture.", encoding="utf-8")
        unused = add_local_source(self.case, unused_file)
        claim = add_claim(
            self.case,
            "Fixture contains notes.",
            "fact",
            [identifier],
            ["line:1"],
            ["Synthetic interview notes."],
        )

        def report():
            return inspect_source_quality(self.store, "case")

        self.assertEqual(report()["used_sources_needing_attention"], [identifier])
        self.service.record("case", self.request())
        quality = report()
        self.assertEqual(quality["sources"][0]["active_claim_ids"], [claim["claim_id"]])
        self.assertEqual(quality["sources"][0]["assessment_status"], "recorded")
        self.assertEqual(
            quality["sources"][0]["unknown_metadata"],
            ["author", "publisher_or_owner", "published_at"],
        )
        self.assertEqual(quality["sources"][1]["source_id"], unused["source_id"])
        self.assertEqual(quality["used_sources_needing_attention"], [])
        add_local_source(self.case, self.file)
        add_local_source(self.case, self.file)
        before = (self.case / "events.jsonl").read_bytes()
        pending = report()
        self.assertEqual(pending["sources"][0]["assessment_status"], "invalidated")
        self.assertEqual(pending["used_sources_needing_attention"], [identifier])
        self.assertIsNotNone(pending["sources"][0]["invalidated_by_revision_or_import"])
        self.assertEqual((self.case / "events.jsonl").read_bytes(), before)
        self.service.record("case", self.request())
        self.assertEqual(report()["used_sources_needing_attention"], [])

    def test_record_inspect_replay_and_render_preserve_evidence_and_human_state(self):
        command = self.request()
        before = json.loads((self.case / "state.json").read_bytes())
        unchanged = {
            name: (self.case / name).read_bytes()
            for name in [
                "claims.jsonl",
                "decision-log.jsonl",
                self.source["extracted_text_path"],
            ]
        }
        result = self.service.record("case", command)
        self.assertEqual(self.service.record("case", command), result)
        self.assertIsNone(self.source["publisher_or_owner"])
        self.assertEqual(result["limitations"], self.source["limitations"])
        self.assertFalse(result["source_assessment"]["independently_verified"])
        current = self.service.inspect("case", self.source["source_id"])
        self.assertEqual(current["assessment_status"], "recorded")
        after = json.loads((self.case / "state.json").read_bytes())
        for key in before.keys() - {"updated_at", "workflow_version"}:
            self.assertEqual(before[key], after[key])
        for name, data in unchanged.items():
            self.assertEqual((self.case / name).read_bytes(), data)
        render_project(self.case)
        self.assertIn(
            "Uncorroborated synthetic interview",
            (self.case / "03_evidence.md").read_text(encoding="utf-8"),
        )

    def test_known_metadata_keeps_access_date_and_changes_review_fingerprint(self):
        from product_strategy_agent.domain.projects.semantic_review import content_hash

        def review_hash():
            with self.store.access("case"):
                snapshot = self.store.capture("case")
            return content_hash(
                "strategy",
                json.loads(snapshot["state"]),
                [
                    json.loads(line)
                    for line in snapshot["events"].splitlines()
                    if line.strip()
                ],
                snapshot["inputs"],
            )

        before = review_hash()
        result = self.service.record(
            "case",
            {
                **self.request(),
                "author": "Synthetic Author",
                "publisher_or_owner": "Fixture Publisher",
                "published_at": "2024-02-29",
                "reliability": "high",
                "unknowns": [],
            },
        )
        self.assertEqual(result["published_at"], "2024-02-29")
        self.assertEqual(result["accessed_at"], self.source["accessed_at"])
        self.assertNotEqual(review_hash(), before)
        self.assertFalse(result["source_assessment"]["independently_verified"])

    def test_bundle_semantics_refuse_rehashed_forged_result(self):
        from hashlib import sha256
        from product_strategy_agent.adapters.persistence.files.workflow_bundle import (
            load,
        )

        request = SourceAssessment.model_validate(self.request())
        self.service.record("case", request)
        folder = self.store._folder(self.case, request.operation_id)
        result_path = folder / "assessment-result.json"
        value = json.loads(result_path.read_bytes())
        value["reliability"] = "high"
        result_path.write_text(json.dumps(value), encoding="utf-8")
        manifest_path = folder / "manifest.json"
        manifest = json.loads(manifest_path.read_bytes())
        manifest["files"]["assessment-result.json"] = sha256(
            result_path.read_bytes()
        ).hexdigest()
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(ValueError):
            load(folder, "case", request.operation_id)

    def test_stale_request_and_conflicting_uuid_refused(self):
        first, stale = self.request(), self.request()
        self.service.record("case", first)
        for request in [stale, {**first, "reason": "Different request"}]:
            with self.assertRaises(ValueError):
                self.service.record("case", request)
        self.assertEqual(len((self.case / "events.jsonl").read_text().splitlines()), 2)

    def test_bad_metadata_and_snapshot_refused_without_writes(self):
        request = self.request()
        before = (self.case / "sources.jsonl").read_bytes()
        for changes in [
            {"published_at": "2026-02-30"},
            {"published_at": "20261117"},
            {"unknowns": []},
            {"assessed_by": " "},
            {"approval_granted": True},
            {"expected_content_hash": "0" * 64},
            {"expected_source_record_hash": "0" * 64},
        ]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.service.record("case", {**request, **changes})
        self.assertEqual((self.case / "sources.jsonl").read_bytes(), before)
        (self.case / self.source["extracted_text_path"]).write_text("Tampered\n")
        with self.assertRaises(ValueError):
            self.service.inspect("case", self.source["source_id"])

    def test_reimport_invalidates_even_same_bytes_and_old_replay_does_not_restore(self):
        request = self.request()
        recorded = self.service.record("case", request)
        imported = add_local_source(self.case, self.file)
        self.assertTrue(imported["source_assessment_review_required"])
        self.assertEqual(imported["reliability"], "unassessed")
        self.assertEqual(self.service.record("case", request), recorded)
        self.assertEqual(
            self.service.inspect("case", self.source["source_id"])["assessment_status"],
            "unassessed",
        )
        events = [
            json.loads(line)
            for line in (self.case / "events.jsonl").read_bytes().splitlines()
        ]
        self.assertEqual(
            events[-1]["assessment_invalidated"]["operation_id"],
            request["operation_id"],
        )

    def test_crash_after_registry_recovers_exactly_once(self):
        request = SourceAssessment.model_validate(self.request())
        original = FileWorkflowStore._replace

        def interrupt(store, case, name, data):
            original(store, case, name, data)
            if name == "sources.jsonl":
                raise OSError("simulated interruption")

        with (
            patch.object(FileWorkflowStore, "_replace", interrupt),
            self.assertRaises(OSError),
        ):
            self.service.record("case", request)
        recovery = WorkflowRecoveryService(self.store)
        result = recovery.recover("case", request.operation_id)
        self.assertEqual(recovery.recover("case", request.operation_id), result)
        self.assertEqual(self.service.record("case", request), result)
        events = [
            json.loads(line)
            for line in (self.case / "events.jsonl").read_bytes().splitlines()
        ]
        self.assertEqual(
            sum(event["event_type"] == "source_assessed" for event in events), 1
        )

    def test_legacy_receipt_replays_without_acquisition_or_metadata_upgrade(self):
        command = SourceImport(
            operation_id=uuid4(), input_kind="local_text", locator=str(self.file)
        )
        with self.store.access("case"):
            snapshot = self.store.capture("case")
            material, text = FileWebSourceReader(self.case).read(command)
            snapshot = self.store.capture_source("case", snapshot, material, text)
            legacy = self.store.commit_source(
                "case", command, snapshot, material, text, "2026-11-17T12:00:00Z"
            )
        self.assertEqual(legacy["publisher_or_owner"], self.file.parent.name)
        request = self.request()
        self.service.record("case", request)
        reader = FileWebSourceReader(self.case)
        with patch.object(
            reader, "read", side_effect=AssertionError("must not acquire")
        ):
            self.assertEqual(
                SourceImportService(self.store, reader).run("case", command), legacy
            )
        self.assertEqual(
            self.service.inspect("case", self.source["source_id"])["assessment_status"],
            "recorded",
        )

    def test_withdrawn_source_refuses_assessment(self):
        request = self.request()
        SourceLifecycleService(self.store).withdraw(
            "case",
            SourceWithdrawal(
                operation_id=uuid4(),
                source_id=self.source["source_id"],
                withdrawn_by="Synthetic reviewer",
                reason="Withdraw synthetic fixture",
            ),
        )
        with self.assertRaises(ValueError):
            self.service.inspect("case", self.source["source_id"])
        with self.assertRaises(ValueError):
            self.service.record("case", request)

    def test_cli_read_write_parity(self):
        request = self.request()
        path = Path(self.temp.name) / "assessment.json"
        path.write_text(json.dumps(request), encoding="utf-8")
        with (
            patch.object(
                sys,
                "argv",
                [
                    "psa",
                    "source",
                    "assess",
                    "case",
                    "--projects-dir",
                    str(self.root),
                    "--input",
                    str(path),
                ],
            ),
            redirect_stdout(StringIO()) as output,
        ):
            main()
        self.assertEqual(
            json.loads(output.getvalue()), self.service.record("case", request)
        )
        with (
            patch.object(
                sys,
                "argv",
                [
                    "psa",
                    "source",
                    "assessment",
                    "case",
                    self.source["source_id"],
                    "--projects-dir",
                    str(self.root),
                ],
            ),
            redirect_stdout(StringIO()) as output,
        ):
            main()
        self.assertEqual(json.loads(output.getvalue())["assessment_status"], "recorded")


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class SourceAssessmentMCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_stdio_read_write_replay_and_annotations(self):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport

        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            case = init_project("case", root)
            source = Path(folder) / "notes.txt"
            source.write_text("Synthetic material.", encoding="utf-8")
            row = add_local_source(case, source)
            service = SourceAssessmentService(FileWorkflowStore(root))
            transport = StdioTransport(
                command=sys.executable,
                args=["-m", "product_strategy_agent.mcp_server"],
                cwd=str(Path(__file__).resolve().parents[1]),
                env={"PYTHONUTF8": "1"},
            )
            async with Client(transport) as client:
                tools = {tool.name: tool for tool in await client.list_tools()}
                self.assertTrue(
                    tools["psa_source_assessment"].annotations.model_dump(
                        by_alias=True
                    )["readOnlyHint"]
                )
                self.assertFalse(
                    tools["psa_assess_source"].annotations.model_dump(by_alias=True)[
                        "readOnlyHint"
                    ]
                )
                args = dict(
                    project_id="case",
                    source_id=row["source_id"],
                    projects_dir=str(root),
                )
                inspected = (await client.call_tool("psa_source_assessment", args)).data
                self.assertEqual(inspected, service.inspect("case", row["source_id"]))
                request = dict(
                    operation_id=str(uuid4()),
                    source_id=row["source_id"],
                    expected_workflow_version=inspected["workflow_version"],
                    expected_content_hash=inspected["content_hash"],
                    expected_source_record_hash=inspected["source_record_hash"],
                    assessed_by="Fixture reviewer",
                    author=None,
                    publisher_or_owner=None,
                    published_at=None,
                    reliability="low",
                    reason="Synthetic material",
                    limitations=["Synthetic"],
                    unknowns=["Metadata unknown"],
                )
                result = (
                    await client.call_tool(
                        "psa_assess_source",
                        dict(
                            project_id="case", projects_dir=str(root), request=request
                        ),
                    )
                ).data
                self.assertEqual(result, service.record("case", request))
                quality_args = dict(project_id="case", projects_dir=str(root))
                quality = (
                    await client.call_tool("psa_source_quality", quality_args)
                ).data
                self.assertEqual(
                    quality, inspect_source_quality(FileWorkflowStore(root), "case")
                )
                self.assertTrue(
                    tools["psa_source_quality"].annotations.model_dump(by_alias=True)[
                        "readOnlyHint"
                    ]
                )
                failure = await client.call_tool(
                    "psa_assess_source",
                    dict(
                        project_id="case",
                        projects_dir=str(root),
                        request={**request, "reason": "PRIVATE-CANARY"},
                    ),
                    raise_on_error=False,
                )
                self.assertTrue(failure.is_error)
                self.assertNotIn("PRIVATE-CANARY", str(failure.content))
