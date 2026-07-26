"""CLI for BB17.3 source acquisition and rule mapping."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .acquisition import SourceAcquisitionPlanner
from .mapping import RuleMappingEngine
from .registry import SourceMappingRegistry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect one BB17.3 source catalog and rule mapping set."
    )
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    registry = SourceMappingRegistry()
    catalog = registry.load_source_catalog(args.catalog)
    mapping_set = registry.load_mapping_set(args.mapping)
    registry.validate_pair(catalog, mapping_set)

    planner = SourceAcquisitionPlanner()
    engine = RuleMappingEngine()
    tasks = planner.create_plan(catalog)
    assessment = engine.assess_activation(catalog, mapping_set)
    payload = {
        "schema_version": "phoenix.source-mapping-report/1.0",
        "catalog_id": catalog.id,
        "mapping_set_id": mapping_set.id,
        "acquisition_tasks": [task.to_dict() for task in tasks],
        "activation_assessment": assessment.to_dict(),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
