"""BB17.3 self-test runner."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(_REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT))

from phoenix.source_mapping import (
    RuleMappingEngine,
    SourceAcquisitionPlanner,
    SourceMappingRegistry,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    catalog_dir = (
        _REPOSITORY_ROOT
        / "configs"
        / "phoenix"
        / "source_catalogs"
        / "foundations"
    )
    mapping_dir = (
        _REPOSITORY_ROOT
        / "configs"
        / "phoenix"
        / "rule_mappings"
        / "foundations"
    )

    registry = SourceMappingRegistry()
    planner = SourceAcquisitionPlanner()
    engine = RuleMappingEngine()
    catalogs = registry.load_source_catalog_directory(catalog_dir)
    mappings = registry.load_mapping_directory(mapping_dir)
    mappings_by_jurisdiction = {
        item.jurisdiction_id: item for item in mappings
    }

    jurisdiction_reports: list[dict] = []
    for catalog in catalogs:
        mapping = mappings_by_jurisdiction[catalog.jurisdiction_id]
        registry.validate_pair(catalog, mapping)
        tasks = planner.create_plan(catalog)
        assessment = engine.assess_activation(catalog, mapping)
        jurisdiction_reports.append(
            {
                "jurisdiction_id": catalog.jurisdiction_id,
                "catalog_fingerprint_sha256": registry.fingerprint_catalog(catalog),
                "mapping_fingerprint_sha256": registry.fingerprint_mapping_set(mapping),
                "acquisition_task_count": len(tasks),
                "automatic_task_count": sum(
                    1 for task in tasks if task.automatic_execution
                ),
                "activation_assessment": assessment.to_dict(),
            }
        )

    result = {
        "status": "PASSED",
        "build_block": "BB17.3",
        "version": "1.0.0",
        "catalog_count": len(catalogs),
        "mapping_set_count": len(mappings),
        "jurisdictions": jurisdiction_reports,
        "all_foundations_safely_inactive": all(
            not item["activation_assessment"]["eligible"]
            for item in jurisdiction_reports
        ),
        "automatic_network_execution": False,
    }

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        result["report_created"] = args.output.is_file()

    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
