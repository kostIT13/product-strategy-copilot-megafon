"""Capability evidence is structural support, never automatic semantic/publication approval."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4
from product_strategy_agent.application.services.promise_check_service import PromiseCheckService
from product_strategy_agent.domain.capabilities.entities import Capability
from product_strategy_agent.domain.capabilities.promises import PromiseCheckRequest, PromiseEvidenceSnapshot, PromiseSource
from product_strategy_agent.domain.evidence.entities import Claim, EvidenceReference


def promise_fixture():
    now = datetime.now(timezone.utc)
    project_id, cap_id, claim_id, source_id = (uuid4() for _ in range(4))
    text = "CSV export is available for pilot accounts with a daily limit.\n"
    source = PromiseSource(source_id, project_id, uuid4(), 1, 1, "synthetic://capabilities", "Fixture",
        "paragraph:1", hashlib.sha256(text.encode()).hexdigest(), text, "extracted", "unassessed",
        ("Pilot only",), {"origin": "synthetic test"})
    claim = Claim(claim_id, project_id, "export-fact", "Pilot CSV export has a daily limit", "fact", "high",
        None, None, "active", now, (EvidenceReference(source_id, 1, source.locator, text.strip()),))
    cap = Capability(cap_id, project_id, "export", "CSV export", "Pilot accounts; daily limit", "available", (claim_id,), now)
    snapshot = PromiseEvidenceSnapshot(project_id, (cap,), (claim,), (source,))
    request = PromiseCheckRequest.model_validate({"candidates": [{"key": "csv-message", "text": "Pilot accounts can export CSV within the daily limit.",
        "support": [{"capability_id": str(cap_id), "claim_ids": [str(claim_id)]}]}]})
    reader = Mock()
    reader.read.return_value = snapshot
    return snapshot, request, reader, PromiseCheckService(reader)


class PromiseCheckTests(unittest.TestCase):
    def test_valid_structure_returns_evidence_limits_and_no_publication_permission(self):
        snapshot, request, reader, service = promise_fixture()
        packet = service.check(" demo ", request)
        self.assertEqual(packet["structural_status"], "eligible_for_human_review")
        self.assertTrue(packet["requires_human_review"])
        self.assertFalse(packet["semantic_alignment_verified"])
        self.assertFalse(packet["source_truthfulness_verified"])
        self.assertFalse(packet["customer_promises_approved"])
        self.assertFalse(packet["publication_approved"])
        self.assertFalse(packet["durable_approval"])
        evidence = packet["candidates"][0]["support"][0]["claims"][0]["evidence"][0]
        self.assertEqual(evidence["source"]["limitations"], ["Pilot only"])
        self.assertNotIn("extracted_text", evidence["source"])
        reader.read.assert_called_once_with("demo", request)

    def test_planned_unavailable_missing_and_foreign_capabilities_are_blocked(self):
        snapshot, request, reader, service = promise_fixture()
        for cap in (replace(snapshot.capabilities[0], status="planned"), replace(snapshot.capabilities[0], status="unavailable"),
                    replace(snapshot.capabilities[0], project_id=uuid4()), None):
            with self.subTest(cap=cap):
                reader.read.return_value = replace(snapshot, capabilities=() if cap is None else (cap,))
                self.assertEqual(service.check("demo", request)["structural_status"], "blocked")

    def test_nonfacts_inactive_unlinked_missing_and_foreign_claims_are_blocked(self):
        snapshot, request, reader, service = promise_fixture()
        claim = snapshot.claims[0]
        cases = [replace(snapshot, claims=(replace(claim, claim_type=kind),)) for kind in ("hypothesis", "interpretation", "forecast", "synthetic")]
        cases.extend((replace(snapshot, claims=(replace(claim, status="withdrawn"),)),
            replace(snapshot, claims=(replace(claim, project_id=uuid4()),)), replace(snapshot, claims=()),
            replace(snapshot, capabilities=(replace(snapshot.capabilities[0], claim_ids=()),))))
        for changed in cases:
            reader.read.return_value = changed
            self.assertEqual(service.check("demo", request)["structural_status"], "blocked")

    def test_every_claim_and_every_evidence_reference_must_pass(self):
        snapshot, request, reader, service = promise_fixture()
        bad = replace(snapshot.claims[0], id=uuid4(), claim_type="hypothesis")
        cap = replace(snapshot.capabilities[0], claim_ids=(snapshot.claims[0].id, bad.id))
        changed = request.model_dump()
        changed["candidates"][0]["support"][0]["claim_ids"].append(bad.id)
        reader.read.return_value = replace(snapshot, claims=(*snapshot.claims, bad), capabilities=(cap,))
        self.assertEqual(service.check("demo", changed)["structural_status"], "blocked")
        reference = replace(snapshot.claims[0].evidence[0], source_id=uuid4())
        reader.read.return_value = replace(snapshot, claims=(replace(snapshot.claims[0], evidence=(*snapshot.claims[0].evidence, reference)),))
        self.assertEqual(service.check("demo", request)["structural_status"], "blocked")

    def test_missing_stale_corrupt_oversized_inactive_and_foreign_sources_are_blocked(self):
        snapshot, request, reader, service = promise_fixture()
        source = snapshot.sources[0]
        cases = [(None, "source_missing_in_project"), (replace(source, latest_revision=2), "source_revision_stale"),
            (replace(source, content_hash="a" * 64), "source_hash_mismatch"),
            (replace(source, extracted_text=None), "source_exceeds_check_limit"),
            (replace(source, status="withdrawn"), "source_not_extracted"),
            (replace(source, project_id=uuid4()), "source_missing_in_project")]
        for changed, reason in cases:
            with self.subTest(reason=reason):
                reader.read.return_value = replace(snapshot, sources=() if changed is None else (changed,))
                self.assertIn(reason, service.check("demo", request)["candidates"][0]["blockers"])

    def test_empty_evidence_fabricated_quote_and_unverified_locator_are_blocked(self):
        snapshot, request, reader, service = promise_fixture()
        claim = snapshot.claims[0]
        for evidence, code in (((), "claim_has_no_evidence"),
            ((replace(claim.evidence[0], quote="Imaginary unlimited export"),), "quote_not_found"),
            ((replace(claim.evidence[0], locator="page:999"),), "locator_not_verified")):
            reader.read.return_value = replace(snapshot, claims=(replace(claim, evidence=evidence),))
            self.assertIn(code, service.check("demo", request)["candidates"][0]["blockers"])

    def test_semantic_overclaim_is_never_automatically_approved_even_with_valid_ids(self):
        _, request, _, service = promise_fixture()
        data = request.model_dump()
        data["candidates"][0]["text"] = "Instant unlimited export of every format for everyone, guaranteed free."
        packet = service.check("demo", data)
        self.assertTrue(packet["candidates"][0]["requires_semantic_review"])
        self.assertFalse(packet["semantic_alignment_verified"])
        self.assertFalse(packet["customer_promises_approved"])
        self.assertFalse(packet["publication_approved"])

    def test_request_validation_blocks_empty_duplicate_oversized_and_unknown_inputs_before_read(self):
        _, request, reader, service = promise_fixture()
        data = request.model_dump()
        invalid = [{"candidates": []}, {"candidates": data["candidates"] * 2},
            {"candidates": [{**data["candidates"][0], "text": " "}]},
            {"candidates": [{**data["candidates"][0], "text": "x" * 2001}]},
            {"candidates": [{**data["candidates"][0], "support": data["candidates"][0]["support"] * 2}]},
            {**data, "publication_approved": True}]
        duplicate = deepcopy(data)
        duplicate["candidates"][0]["support"][0]["claim_ids"] *= 2
        invalid.append(duplicate)
        for value in invalid:
            with self.assertRaises(ValueError):
                service.check("demo", value)
        with self.assertRaises(ValueError):
            service.check(" ", request)
        reader.read.assert_not_called()

    def test_hash_is_stable_but_changes_with_text_and_evidence_state(self):
        snapshot, request, reader, service = promise_fixture()
        first = service.check("demo", request)
        self.assertEqual(first, service.check("demo", request))
        changed = request.model_dump()
        changed["candidates"][0]["text"] += " Another qualifier."
        self.assertNotEqual(first["review_hash"], service.check("demo", changed)["review_hash"])
        reader.read.return_value = replace(snapshot, sources=(replace(snapshot.sources[0], latest_revision=2),))
        self.assertNotEqual(first["review_hash"], service.check("demo", request)["review_hash"])

    def test_cli_has_explicit_blocked_exit_code_and_same_payload(self):
        from product_strategy_agent.interfaces.cli.main import build_parser
        from product_strategy_agent.interfaces.cli.promise_commands import handle_promise_command
        snapshot, request, reader, service = promise_fixture()
        with TemporaryDirectory() as folder:
            path = Path(folder) / "promises.json"
            path.write_text(request.model_dump_json(), encoding="utf-8")
            args = build_parser().parse_args(["promise", "check", "demo", "--input", str(path)])
            with patch("product_strategy_agent.interfaces.cli.promise_commands.build_promise_service", return_value=service), patch("builtins.print") as output:
                self.assertEqual(handle_promise_command(args), 0)
                self.assertEqual(json.loads(output.call_args.args[0]), service.check("demo", request))
                reader.read.return_value = replace(snapshot, capabilities=())
                self.assertEqual(handle_promise_command(args), 3)
                self.assertEqual(json.loads(output.call_args.args[0])["structural_status"], "blocked")

    def test_packet_budget_blocks_instead_of_silently_truncating_evidence(self):
        snapshot, request, reader, service = promise_fixture()
        reader.read.return_value = replace(snapshot, capabilities=(replace(snapshot.capabilities[0], description="x" * 128001),))
        with self.assertRaisesRegex(ValueError, "split the request"):
            service.check("demo", request)

    def test_standalone_composition_does_not_construct_an_llm_provider(self):
        from product_strategy_agent.bootstrap import build_promise_service
        with patch("product_strategy_agent.bootstrap.OpenAICompatibleProvider") as provider:
            self.assertIsInstance(build_promise_service(), PromiseCheckService)
        provider.assert_not_called()


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class PromiseMCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_read_only_mcp_matches_core_and_returns_blockers_without_model_or_writes(self):
        from fastmcp import Client
        from product_strategy_agent.bootstrap import MainServices
        from product_strategy_agent.interfaces.mcp.server import create_server
        snapshot, request, reader, service = promise_fixture()
        agent = Mock()
        async with Client(create_server(MainServices(agent, Mock(), Mock(), Mock(), promises=service))) as client:
            tool = next(item for item in await client.list_tools() if item.name == "psa_main_check_promises")
            self.assertTrue(tool.annotations.read_only_hint)
            self.assertFalse(tool.annotations.open_world_hint)
            args = {"project_key": "demo", "request": request.model_dump(mode="json")}
            self.assertEqual((await client.call_tool(tool.name, args)).data, service.check("demo", request))
            reader.read.return_value = replace(snapshot, capabilities=())
            result = (await client.call_tool(tool.name, args)).data
            self.assertEqual(result["structural_status"], "blocked")
        self.assertFalse(agent.mock_calls)
