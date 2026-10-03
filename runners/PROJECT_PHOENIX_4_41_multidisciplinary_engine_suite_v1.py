from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
import json
import sys


def main() -> int:
    parser = ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--synthetic-proof", action="store_true")
    parser.add_argument("--project-json", type=Path)
    args = parser.parse_args()

    root = args.repo_root.resolve()
    sys.path.insert(0, str(root))
    from phoenix.autonomy.multidisciplinary_engine_suite import MultidisciplinaryEngineSuiteService

    service = MultidisciplinaryEngineSuiteService.from_repo(root)
    if args.probe:
        value = {
            "schema": "PHOENIX_PHASE17_ENGINE_SUITE_PROBE_V1",
            "status": "PASS",
            "engine_count": len(service.descriptors),
            "engine_keys": [x.key for x in sorted(service.descriptors, key=lambda x: x.order)],
            "backends": service.backend_probe(),
            "automatic_engine_activation": False,
            "repository_mutation": False,
        }
    elif args.synthetic_proof:
        value = service.synthetic_proof()
    elif args.project_json:
        value = service.plan(json.loads(args.project_json.read_text(encoding="utf-8-sig")))
    else:
        parser.error("select --probe, --synthetic-proof, or --project-json")
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
