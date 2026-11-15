"""Internal fixed read-only worker with an independent deadline if its parent dies."""

import argparse
import os
from pathlib import Path
import threading
from product_strategy_agent.interfaces.hook_preflight import (
    hook_preflight,
    parse_hook_request,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--projects-dir", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, required=True)
    args = parser.parse_args()
    if os.environ.get("PSA_HOOK_WORKER") != "1" or not 1 <= args.timeout <= 120:
        raise SystemExit(2)
    watchdog = threading.Timer(args.timeout, lambda: os._exit(124))
    watchdog.daemon = True
    watchdog.start()
    try:
        with args.request.open("rb") as stream:
            command = parse_hook_request(stream.read(64001))
        result = hook_preflight(args.projects_dir).check(command)
        import json

        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=False)
    finally:
        watchdog.cancel()


if __name__ == "__main__":
    main()
