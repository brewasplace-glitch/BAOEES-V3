from __future__ import annotations

import argparse
import json
from pathlib import Path

from phoenix.design.tropical_residential.project_orchestration import (
    orchestrate_real_project_delivery as orchestrate_tropical_residential,
)
from phoenix.architecture.nonresidential_real_project_orchestration_v1_0 import (
    orchestrate_real_project_delivery as orchestrate_nonresidential_reuse,
)


def resolve_architectural_route(project):
    metadata = project.get("metadata")
    if isinstance(metadata, dict):
        route = metadata.get("phoenix_architectural_engine_route")
        if isinstance(route, dict) and str(route.get("route", "")).upper() == "NONRESIDENTIAL_REUSE_V1":
            return "NONRESIDENTIAL_REUSE_V1"
    return "TROPICAL_RESIDENTIAL_LEGACY"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Phoenix autonomous architectural real-project A-E compatibility router"
    )
    parser.add_argument("--project-json", required=True)
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--quick-smoke", action="store_true")
    args = parser.parse_args()

    project = json.loads(Path(args.project_json).read_text(encoding="utf-8"))
    route = resolve_architectural_route(project)

    if route == "NONRESIDENTIAL_REUSE_V1":
        result = orchestrate_nonresidential_reuse(
            project,
            Path(args.runtime_root),
            quick_smoke=args.quick_smoke,
        )
    else:
        result = orchestrate_tropical_residential(
            project,
            Path(args.runtime_root),
            quick_smoke=args.quick_smoke,
        )

    payload = result if isinstance(result, dict) else result.to_dict()
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
