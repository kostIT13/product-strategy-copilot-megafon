"""Advisory CLI control capabilities from a bound historical diagnostic."""


def control_policy(packet):
    kind, phase = packet["kind"], packet["publication"]
    pending = phase in {"prepared", "result_prepared", "execution_unknown"}
    missing = phase == "not_found"
    prerequisites = [
        "inspect_selected_pending",
        "confirm_no_active_writer",
        "explicit_recovery_instruction",
    ]
    if missing:
        recovery = {
            "availability": "not_applicable",
            "reason": "operation_not_found",
            "effect": None,
            "prerequisites": [],
        }
    elif not pending:
        recovery = {
            "availability": "not_applicable",
            "reason": "publication_already_recorded",
            "effect": None,
            "prerequisites": [],
        }
    else:
        effect = "publish_captured_artifact"
        if kind == "hook":
            effect = (
                "record_interrupted_without_execution"
                if phase == "execution_unknown"
                else "publish_captured_completion"
            )
        recovery = {
            "availability": "requires_explicit_instruction",
            "reason": "unfinished_publication",
            "effect": effect,
            "prerequisites": prerequisites,
        }

    if missing:
        replay = {"availability": "not_applicable", "effect": None}
        attempt = {
            "availability": "not_applicable",
            "effect": None,
            "prerequisites": ["verify_kind_and_uuid"],
        }
    elif pending:
        replay = {"availability": "blocked_pending_resolution", "effect": None}
        attempt = {
            "availability": "blocked_pending_resolution",
            "effect": None,
            "prerequisites": prerequisites,
        }
    else:
        replay = {
            "availability": "exact_request_only",
            "effect": "historical_receipt_without_execution",
        }
        effect = {
            "task": "new_task_uuid",
            "result": "new_task_and_result_uuids",
            "review": "new_review_operation_uuid",
            "hook": "new_hook_request_uuid",
        }[kind]
        requirements = [
            "review_recorded_outcome",
            "fresh_scope_and_binding",
            "explicit_new_attempt_instruction",
        ]
        if kind in {"task", "result"}:
            requirements += [
                "review_budget_and_material_permissions",
                "explicit_dispatch_permission_if_needed",
            ]
        if packet["recorded_outcome"] == "budget_exceeded":
            requirements += ["resolve_reported_budget_overrun"]
        if kind == "review":
            requirements += ["ready_verdict_requires_current_snapshot"]
        attempt = {
            "availability": "requires_new_request",
            "effect": effect,
            "prerequisites": requirements,
        }

    return {
        "format_version": "psa-operation-controls-v1",
        "package_version": packet["package_version"],
        "project_id": packet["project_id"],
        "kind": kind,
        "operation_id": packet["operation_id"],
        "scope": "cli_journal_controls_only",
        "diagnostic_binding": {
            "publication": phase,
            "record_hash": packet["record_hash"],
            "completion_hash": packet["completion_hash"],
            "freshness": "not_checked",
        },
        "controls": {
            "inspect": {
                "availability": "read_only",
                "effect": "inspect_recorded_metadata",
            },
            "resume_case_context": {
                "availability": "read_only_cli_command",
                "effect": "show_saved_case_status_without_execution",
                "prerequisites": ["canonical_case_state_valid", "case_lock_available"],
            },
            "recover_publication": recovery,
            "same_uuid_replay": replay,
            "new_attempt": attempt,
            "resume_execution": {
                "availability": "not_supported_by_cli",
                "reason": "no_owned_agent_checkpoint_executor",
            },
            "cancel_execution": {
                "availability": "not_supported_by_cli",
                "reason": "no_generic_process_cancel_endpoint",
            },
        },
        "owned_hook_timeout": "fixed_worker_deadline_only"
        if kind == "hook"
        else "not_applicable",
        "native_host_controls": "not_verified",
        "native_host_assessed": False,
        "host_acceptance_required_for_native_controls": True,
        "recorded_outcome_is_not_control_evidence": True,
        "policy_only": True,
        "policy_is_write_enforcement": False,
        "authorization_evaluated": False,
        "authorization_granted": False,
        "actions_executed": False,
        "workflow_approval_granted": False,
        "native_activation_allowed": False,
    }
