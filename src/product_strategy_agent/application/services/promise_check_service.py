"""Read-only promise preflight for CLI/MCP; independent of any model/API pipeline."""
import json
from product_strategy_agent.application.ports.promise_evidence_reader import PromiseEvidenceReader
from product_strategy_agent.application.services.promise_evidence_checks import check_candidate
from product_strategy_agent.domain.capabilities.promises import PromiseCheckRequest
from product_strategy_agent.domain.decisions.selection import fingerprint


class PromiseCheckService:
    def __init__(self, reader: PromiseEvidenceReader):
        self.reader = reader

    def check(self, project_key: str, request: PromiseCheckRequest):
        request = PromiseCheckRequest.model_validate(request)
        project_key = project_key.strip()
        if not project_key:
            raise ValueError("project key must not be empty")
        snapshot = self.reader.read(project_key, request)
        results = [check_candidate(candidate, snapshot) for candidate in request.candidates]
        packet = {"format_version": 1, "project_id": str(snapshot.project_id),
            "request": request.model_dump(mode="json"), "candidates": results,
            "structural_status": "blocked" if any(item["blockers"] for item in results) else "eligible_for_human_review",
            "requires_human_review": True, "semantic_alignment_verified": False,
            "source_truthfulness_verified": False, "publication_approved": False,
            "customer_promises_approved": False, "workflow_approval_granted": False,
            "scope": "read_only_preflight", "durable_approval": False,
            "review_questions": ["Does each exact promise follow from the capability and cited factual claims?",
                "Are audience, format, limits, timing and conditions narrower than or equal to the evidence?",
                "Are source origin, reliability, limitations and contradictory evidence acceptable?"]}
        serialized = json.dumps(packet, ensure_ascii=False, sort_keys=True, default=str)
        if len(serialized) > 128000:
            raise ValueError("promise evidence packet exceeds the 128000-character limit; split the request")
        packet = json.loads(serialized)
        return {**packet, "review_hash": fingerprint(packet)}
