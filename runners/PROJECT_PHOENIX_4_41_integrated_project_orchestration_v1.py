from __future__ import annotations

import argparse
import json
from pathlib import Path

from phoenix.autonomy import IntegratedProjectOrchestrationService


def main() -> int:
    parser = argparse.ArgumentParser(description="Governed Phoenix integrated project orchestration")
    parser.add_argument("--repo-root", type=Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--synthetic-proof", action="store_true")
    group.add_argument("--request", type=Path)
    args = parser.parse_args()
    service = IntegratedProjectOrchestrationService.from_repo(args.repo_root)
    if args.synthetic_proof:
        result = service.synthetic_proof()
    else:
        result = service.run(json.loads(args.request.read_text(encoding="utf-8-sig")))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
