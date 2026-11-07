"""Read-only diagnostics for the local CLI environment."""

from __future__ import annotations

import importlib.util
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from product_strategy_agent import __version__
from product_strategy_agent.rendering import DRAFTS

KNOWN_CONFIG_NAMES = ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL", "QWEN_API_KEY", "QWEN_BASE_URL", "QWEN_MODEL")


def doctor_report(base_dir: Path | None = None) -> dict[str, Any]:
    """Return environment status without reading or displaying secret values."""
    root = (base_dir or Path.cwd()).resolve()
    python_supported = sys.version_info >= (3, 11)
    template_names = ("product-strategy.md", "communication-strategy.md", "validation-plan.md")
    templates_ok = all(
        isinstance(DRAFTS.get(name), str)
        and DRAFTS[name].lstrip().startswith("#")
        and len(DRAFTS[name].strip()) > 20
        for name in template_names
    )

    uv_path = shutil.which("uv")
    uv_version = "not installed"
    if uv_path:
        try:
            result = subprocess.run(
                [uv_path, "--version"], capture_output=True, text=True, timeout=3, check=False
            )
            output = (result.stdout or result.stderr).strip()
            uv_version = output.splitlines()[0] if output else "found; version output unavailable"
        except (OSError, subprocess.TimeoutExpired):
            uv_version = "found but version check failed"

    env_names = [name for name in KNOWN_CONFIG_NAMES if name in os.environ]
    env_file = (root / ".env").is_file()
    env_example = (root / ".env.example").is_file()
    fastmcp_installed = importlib.util.find_spec("fastmcp") is not None
    checks = [
        {"name": "python", "ok": python_supported, "version": platform.python_version(), "required": True},
        {"name": "project_templates", "ok": templates_ok, "available": list(template_names), "required": True},
        {"name": "uv", "ok": uv_path is not None, "version": uv_version, "required": False},
        {"name": "fastmcp", "ok": fastmcp_installed, "version": "installed" if fastmcp_installed else "not installed", "required": False},
        {
            "name": "configuration_presence",
            "ok": True,
            "env_file_present": env_file,
            "env_example_present": env_example,
            "known_variable_names_present": env_names,
            "secret_values_read": False,
            "required": False,
        },
    ]
    warnings = [f"Optional component {item['name']} is unavailable" for item in checks if not item["ok"] and not item["required"]]
    return {
        "ok": python_supported and templates_ok,
        "product_strategy_agent_version": __version__,
        "python_executable": str(Path(sys.executable).resolve()),
        "checks": checks,
        "warnings": warnings,
    }


def format_doctor_report(report: dict[str, Any]) -> str:
    lines = [f"doctor: {'ready' if report['ok'] else 'needs attention'}", f"CLI version: {report['product_strategy_agent_version']}"]
    for check in report["checks"]:
        status = "ok" if check["ok"] else ("warning" if not check["required"] else "failed")
        details = []
        for key in ("version", "available", "env_file_present", "env_example_present", "known_variable_names_present"):
            if key in check:
                details.append(f"{key}={check[key]}")
        if check.get("name") == "configuration_presence":
            details.append("secret values not inspected")
        lines.append(f"{status}: {check['name']}" + (f" ({'; '.join(details)})" if details else ""))
    if report["warnings"]:
        lines.extend(f"hint: {warning}" for warning in report["warnings"])
    return "\n".join(lines)
