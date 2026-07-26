"""BB18.1 self-test runner."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from phoenix.architectural_drawing import ArchitecturalDrawingEngine


def self_test_model() -> dict:
    return {
        "project_id": "PHX-BB18.1-SELFTEST",
        "name": "Architectural Drawing Engine Self-Test",
        "levels": [{"id": "LVL-00", "name": "Ground floor", "elevation_m": 0.0}],
        "spaces": [{"id": "SPC-001", "name": "Test room", "level_id": "LVL-00"}],
        "elements": [{
            "id": "ELM-WALL-001",
            "name": "Test wall",
            "category": "wall",
            "level_id": "LVL-00",
            "geometry": {"x_m": 0, "y_m": 0, "length_m": 5, "thickness_m": 0.2},
        }],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    engine = ArchitecturalDrawingEngine()
    model = self_test_model()
    package = engine.create_package(model)
    files = []
    if args.output_dir:
        manifest = engine.export_manifest(package, args.output_dir / "drawing_package.json")
        plan = engine.export_plan_svg(model, "LVL-00", args.output_dir / "A101_ground_floor.svg")
        files = [str(manifest), str(plan)]
    passed = len(package.sheets) == 9 and len({sheet.id for sheet in package.sheets}) == 9
    result = {
        "status": "PASSED" if passed else "FAILED",
        "build_block": "BB18.1",
        "version": "1.0.0",
        "sheet_count": len(package.sheets),
        "package_fingerprint_sha256": package.metadata["package_fingerprint_sha256"],
        "files_created": files,
    }
    print(json.dumps(result, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
