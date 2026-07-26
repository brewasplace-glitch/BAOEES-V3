"""BB19 self-test runner."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from phoenix.structural_design import StructuralDesignEngine


def self_test_model() -> dict:
    return {
        "project_id": "PHX-BB19-SELFTEST",
        "elements": [
            {
                "id": "ELM-FOUND-001",
                "category": "foundation",
                "level_id": "LVL-00",
                "geometry": {"length_m": 6.0},
                "material": {"name": "concrete"},
                "properties": {},
            },
            {
                "id": "ELM-COL-001",
                "category": "column",
                "level_id": "LVL-00",
                "geometry": {"length_m": 3.2},
                "material": {"name": "steel"},
                "properties": {"section": {"name": "SHS150"}},
            },
            {
                "id": "ELM-BEAM-001",
                "category": "beam",
                "level_id": "LVL-00",
                "geometry": {"length_m": 5.0},
                "material": {"name": "steel"},
                "properties": {"section": {"name": "IPE200"}},
            },
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    engine = StructuralDesignEngine()
    model = engine.create_model(self_test_model())
    issues = engine.validate(model)
    errors = [item for item in issues if item.severity in {"error", "critical"}]
    files = []
    if args.output_dir:
        model_path = engine.export_model(model, args.output_dir / "structural_model.json")
        files.append(str(model_path))
        for analysis_engine in ("openseespy", "calculix", "scia"):
            handoff = engine.create_handoff(model, analysis_engine, model_path)
            path = engine.export_handoff(
                handoff,
                args.output_dir / f"handoff_{analysis_engine}.json",
            )
            files.append(str(path))
    passed = len(model.members) == 3 and not errors
    result = {
        "status": "PASSED" if passed else "FAILED",
        "build_block": "BB19",
        "version": "1.0.0",
        "member_count": len(model.members),
        "support_count": len(model.supports),
        "warning_count": sum(item.severity == "warning" for item in issues),
        "error_count": len(errors),
        "structural_model_fingerprint_sha256": model.metadata["structural_model_fingerprint_sha256"],
        "files_created": files,
    }
    print(json.dumps(result, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
