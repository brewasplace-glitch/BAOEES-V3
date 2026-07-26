"""Command-line interface for BB23."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import ConstructionDocumentationEngine
from .exporters import ConstructionDocumentationExporter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Assemble a Phoenix construction documentation package."
    )
    parser.add_argument("--project-metadata", type=Path, required=True)
    parser.add_argument("--building-model", type=Path, required=True)
    parser.add_argument("--drawing-manifest", type=Path, required=True)
    parser.add_argument("--structural-report", type=Path, required=True)
    parser.add_argument("--quantity-report", type=Path, required=True)
    parser.add_argument("--cost-report", type=Path, required=True)
    parser.add_argument("--coordination-report", type=Path, required=True)
    parser.add_argument("--revision", default="P01")
    parser.add_argument("--stage", default="concept")
    parser.add_argument("--release", action="store_true")
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    engine = ConstructionDocumentationEngine()
    exporter = ConstructionDocumentationExporter()

    package = engine.assemble(
        _load(args.project_metadata),
        building_model=_load(args.building_model),
        drawing_manifest=_load(args.drawing_manifest),
        structural_report=_load(args.structural_report),
        quantity_report=_load(args.quantity_report),
        cost_report=_load(args.cost_report),
        coordination_report=_load(args.coordination_report),
        revision=args.revision,
        stage=args.stage,
        release_requested=args.release,
    )
    paths = exporter.export_all(package, args.output_dir)

    result = {
        "status": "PASSED",
        "package_status": package.status.value,
        "release_ready": package.release_ready,
        "project_id": package.project_id,
        "package_id": package.package_id,
        "document_count": len(package.document_register),
        "blocking_issue_count": package.blocking_issue_count,
        "package_fingerprint_sha256": engine.fingerprint_package(package),
        "outputs": {
            key: str(path)
            for key, path in sorted(paths.items())
        },
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
