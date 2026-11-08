"""Reconstruct immutable decision/selection context without a fresh retrieval or model call."""
from dataclasses import asdict
import json
from uuid import UUID
from product_strategy_agent.application.services.agent_context import prepare_request, restore_contexts, review_target_hash
from product_strategy_agent.domain.decisions.selection import SelectionCommand, fingerprint, run_fingerprint, option_description


def json_entity(value):
    return json.loads(json.dumps(asdict(value), default=str, ensure_ascii=False))


class StrategyPlanContext:
    def __init__(self, agent, selection, inputs, decisions, options):
        self.agent, self.selection, self.inputs = agent, selection, inputs
        self.decisions, self.options = decisions, options

    def _records(self, project_id, receipt):
        command = SelectionCommand.model_validate(receipt["command"])
        if fingerprint(command.model_dump(mode="json")) != receipt["request_hash"]:
            raise ValueError("selection command hash changed")
        decision = self.decisions.get_by_id(UUID(receipt["decision_id"]))
        if decision is None or decision.project_id != project_id:
            raise ValueError("recorded decision is missing from this project")
        selected = UUID(receipt["option_ids"][command.selected])
        expected_dispositions = {receipt["option_ids"][command.selected]: "selected",
            **{receipt["option_ids"][key]: "rejected" for key in command.rejected},
            **{receipt["option_ids"][key]: "deferred" for key in command.deferred}}
        if (decision.selected_option_id != selected or decision.key != command.decision_key or decision.owner != command.owner
                or decision.rationale != command.rationale or decision.review_trigger != command.review_trigger
                or {str(item.option_id): item.disposition for item in decision.alternatives} != expected_dispositions
                or len(decision.alternatives) != 3 or decision.basis_claim_ids):
            raise ValueError("canonical decision differs from the recorded human selection")
        option = self.options.get_by_id(selected)
        proposal = next(item for item in receipt["review_snapshot"]["draft"]["options"] if item["option_id"] == command.selected)
        assumptions = tuple(f"{item['text']} Validate: {item['validation_question']}" for item in proposal["assumptions"])
        if (option is None or option.project_id != project_id or option.name != proposal["name"]
                or option.key != f"ai-{command.source_run_id.hex}-{command.selected.lower()}"
                or option.description != option_description(proposal) or option.risks != tuple(proposal["risks"])
                or option.assumptions != assumptions or option.strengths or option.claim_links or option.status != "proposed"
                or decision.risks != tuple(proposal["risks"])
                or decision.assumptions != tuple(item["text"] for item in proposal["assumptions"])):
            raise ValueError("selected canonical option differs from the reviewed proposal")
        return command, decision, option, proposal

    def create(self, project_key, source_run_id, question):
        project = self.selection.project(project_key)
        receipt = self.selection.get(project_key, source_run_id)
        command, decision, option, proposal = self._records(project.id, receipt)
        preview = self.selection.preview(project_key, source_run_id, command.critic_run_id)
        fields = ("source_hash", "critic_hash", "source_fingerprint", "contexts", "draft", "critic", "critic_verdict")
        if any(preview[key] != receipt["review_snapshot"][key] for key in fields):
            raise ValueError("selection inputs changed after human review")
        if command.source_run_id != source_run_id or command.source_hash != preview["source_hash"] or command.critic_hash != preview["critic_hash"]:
            raise ValueError("selection references do not match reviewed runs")
        snapshot = {"version": 1, "source_run_id": str(source_run_id), "receipt_hash": fingerprint(receipt),
            "source_fingerprint": preview["source_fingerprint"], "critic_hash": preview["critic_hash"],
            "contexts": preview["contexts"], "decision": json_entity(decision), "selected_option": json_entity(option),
            "selected_proposal": proposal, "critic": preview["critic"], "critic_verdict": preview["critic_verdict"],
            "options_stage_gaps": preview["draft"]["gaps"], "options_stage_caveats": preview["draft"]["caveats"],
            "options_stage_comparison": next(item for item in preview["draft"]["comparison"] if item["option_id"] == command.selected),
            "human_review": {"review_note": command.review_note, "critic_resolution": command.critic_resolution}}
        digest = review_target_hash(snapshot)
        return self._prepared(project.id, source_run_id, digest, snapshot, question, require_current=True)

    def stale_sources(self, project_id, references):
        stale = []
        for reference in references:
            current = self.agent.sources.get_revision(UUID(reference["source_id"]))
            if current is None or current.project_id != project_id or current.revision.revision != reference["revision"]:
                stale.append(reference["source_id"])
        return stale

    def _prepared(self, project_id, source_run_id, digest, snapshot, question, *, require_current):
        question = question.strip()
        if not question or len(question) > 4000:
            raise ValueError("question must contain 1-4000 characters")
        if not isinstance(snapshot, dict) or snapshot.get("version") != 1 or snapshot.get("source_run_id") != str(source_run_id) or review_target_hash(snapshot) != digest:
            raise ValueError("strategy input snapshot hash mismatch")
        receipt = self.selection.store.get(project_id, source_run_id)
        if receipt is None or fingerprint(receipt) != snapshot["receipt_hash"]:
            raise ValueError("recorded selection changed")
        command, decision, option, _ = self._records(project_id, receipt)
        if json_entity(decision) != snapshot["decision"] or json_entity(option) != snapshot["selected_option"]:
            raise ValueError("canonical strategy inputs changed")
        for run_id, expected in ((source_run_id, snapshot["source_fingerprint"]), (command.critic_run_id, snapshot["critic_hash"])):
            run = self.agent.runs.get(project_id, run_id)
            if run is None or run.status != "succeeded" or run_fingerprint(run) != expected:
                raise ValueError("reviewed strategy inputs changed")
        contexts = restore_contexts(self.agent.sources, project_id, snapshot["contexts"])
        if require_current and self.stale_sources(project_id, snapshot["contexts"]):
            raise ValueError("sources changed since selection; record a fresh reviewed decision before generation")
        return prepare_request(project_id, question, f"decision:{decision.id}", self.agent.provider.model, contexts,
            "strategy_plan", input_run_id=source_run_id, input_hash=digest, review_target=snapshot)

    def restore(self, project_id, source_run_id, digest, question, *, require_current=False):
        snapshot = self.inputs.get(project_id, digest)
        if snapshot is None:
            raise ValueError("strategy input snapshot is missing in this project")
        return self._prepared(project_id, source_run_id, digest, snapshot, question, require_current=require_current)
