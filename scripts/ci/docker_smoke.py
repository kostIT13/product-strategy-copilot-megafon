"""Build the runtime image and exercise CLI/MCP/demo without network or secrets."""
from product_strategy_agent.interfaces.mcp.inventory import MAIN_TOOL_COUNT
import argparse
import json
from pathlib import Path
import subprocess
from uuid import uuid4


def smoke(root):
    image = f"psa-ci:{uuid4().hex[:12]}"
    subprocess.run(["docker", "build", "--tag", image, str(root)], check=True, timeout=900)
    base = ["docker", "run", "--rm", "--network", "none", "--read-only",
            "--tmpfs", "/tmp:rw,nosuid,size=128m", "-e", "LLM_API_KEY=",
            "-e", "LLM_BASE_URL=https://provider.invalid/v1", "-e", "LITELLM_LOCAL_MODEL_COST_MAP=True",
            "-e", "DO_NOT_TRACK=1"]
    try:
        for command in (["psa", "doctor"], ["psa-main", "--help"],
                        ["alembic", "upgrade", "head", "--sql"],
                        ["python", "-m", "scripts.ci.container_probe"]):
            result = subprocess.run([*base, image, *command], capture_output=True, timeout=90)
            if result.returncode:
                raise ValueError(f"container command failed: {' '.join(command)} (exit {result.returncode})")
        mounts = [item for name in ("demo", "table-demo") for item in
                  ("-v", f"{root / 'projects' / name}:/fixtures/projects/{name}:ro")]
        subprocess.run([*base, *mounts, image, "python", "-m", "scripts.ci.demo", "--root", "/fixtures"],
                       check=True, timeout=90)
    finally:
        subprocess.run(["docker", "image", "rm", image], check=False, capture_output=True)
    return {"ok": True, "network": "none", "read_only": True, "non_root": True,
            "mcp_tools": MAIN_TOOL_COUNT, "model_calls": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(json.dumps(smoke(args.root.resolve())))


if __name__ == "__main__":
    main()
