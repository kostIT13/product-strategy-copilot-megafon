"""Render only a disabled Codex stdio fragment; never read or write live settings."""

import hashlib
import json
from pathlib import Path

DOCS = [
    "https://learn.chatgpt.com/docs/extend/mcp?surface=cli",
    "https://learn.chatgpt.com/docs/config-file/config-reference",
]
TOOLS = ["psa_status", "psa_validate", "psa_verify", "psa_coverage"]


class CodexConfigPreview:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def render(self, interpreter):
        executable = Path(interpreter)
        if not executable.is_absolute() or not executable.is_file():
            raise ValueError("preview requires an existing absolute interpreter path")
        values = {
            "command": str(executable.resolve()),
            "args": ["-m", "product_strategy_agent.mcp_server"],
            "cwd": str(self.root),
            "enabled": False,
            "required": False,
            "enabled_tools": TOOLS,
            "default_tools_approval_mode": "prompt",
            "supports_parallel_tool_calls": False,
        }

        def toml(value):
            return json.dumps(value, ensure_ascii=False)

        content = "[mcp_servers.psa]\n" + "".join(
            f"{name} = {toml(value)}\n" for name, value in values.items()
        )
        return {
            "adapter_id": "codex-mcp-stdio-preview-v1",
            "target_hint": ".codex/config.toml",
            "kind": "fragment",
            "content": content,
            "sha256": hashlib.sha256(content.encode()).hexdigest(),
            "documentation": DOCS,
            "documentation_checked_at": "2026-11-15",
            "existing_config_inspected": False,
            "merge_required": True,
            "interpreter_runtime_verified": False,
        }
