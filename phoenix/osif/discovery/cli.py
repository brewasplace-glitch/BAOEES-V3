"""CLI for Phoenix OSIF application discovery."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from phoenix.osif import ApplicationRegistry
from .catalog import default_candidates
from .service import ApplicationDiscoveryService


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    registry = (
        ApplicationRegistry.read_json(args.registry)
        if args.registry and Path(args.registry).exists()
        else ApplicationRegistry()
    )

    service = ApplicationDiscoveryService()
    report = service.update_registry(
        registry=registry,
        candidates=default_candidates(),
    )
    service.write_report(report, args.output)

    summary = {
        item["application_id"]: item["health_status"]
        for item in report["results"]
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
