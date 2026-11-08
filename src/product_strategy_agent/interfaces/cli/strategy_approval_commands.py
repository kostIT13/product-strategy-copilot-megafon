"""Internal strategy approval and portable export; thin application-service dispatch."""
import json
from pathlib import Path
from uuid import UUID
from product_strategy_agent.domain.decisions.strategy_approval import StrategyApprovalCommand


def add_strategy_approval_actions(actions):
    preview = actions.add_parser("preview-approval", help="Review a strategy and its linked critic without writes")
    preview.add_argument("project_key")
    preview.add_argument("strategy_run_id", type=UUID)
    preview.add_argument("critic_run_id", type=UUID)
    approve = actions.add_parser("approve", help="Record explicit human acceptance for internal review only")
    approve.add_argument("project_key")
    approve.add_argument("--input", type=Path, required=True, help="JSON StrategyApprovalCommand confirmed by a human")
    for name in ("approval", "export"):
        command = actions.add_parser(name)
        command.add_argument("project_key")
        command.add_argument("strategy_run_id", type=UUID)


def strategy_approval_action(service, args):
    if args.action == "preview-approval":
        return service.preview(args.project_key, args.strategy_run_id, args.critic_run_id)
    if args.action == "approve":
        command = StrategyApprovalCommand.model_validate_json(args.input.read_text(encoding="utf-8"))
        return service.record(args.project_key, command)
    if args.action == "approval":
        return service.get(args.project_key, args.strategy_run_id)
    return service.export(args.project_key, args.strategy_run_id)
