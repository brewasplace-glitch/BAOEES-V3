from __future__ import annotations

import argparse
import json
from pathlib import Path

from phoenix.design.tropical_residential.project_orchestration import (
    orchestrate_real_project_delivery,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Phoenix autonomous architectural real-project A-E delivery"
    )
    parser.add_argument("--project-json", required=True)
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--quick-smoke", action="store_true")
    args = parser.parse_args()

    project = json.loads(Path(args.project_json).read_text(encoding="utf-8"))
    result = orchestrate_real_project_delivery(
        project,
        Path(args.runtime_root),
        quick_smoke=args.quick_smoke,
    )
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
