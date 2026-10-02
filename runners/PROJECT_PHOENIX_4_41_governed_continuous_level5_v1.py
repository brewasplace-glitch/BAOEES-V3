#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from phoenix.autonomy import GovernedContinuousLevel5Service


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--expected-baseline")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--scheduled-window", action="store_true")
    mode.add_argument("--status", action="store_true")
    mode.add_argument("--scheduler-spec", action="store_true")
    args = parser.parse_args()
    repo = Path(args.repo_root).resolve()
    service = GovernedContinuousLevel5Service(repo, Path(args.runtime_root), policy_root=repo)
    if args.scheduled_window:
        if not args.expected_baseline: parser.error("--expected-baseline is required")
        result = service.run_window(args.expected_baseline)
    elif args.scheduler_spec:
        result = service.scheduler_spec()
    else:
        result = service.status()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
