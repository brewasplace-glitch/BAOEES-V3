"""Run Project Phoenix reinforced-concrete beam design engine v1.0.0."""
from __future__ import annotations
import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phoenix.structural.reinforced_concrete_beam import (
    ReinforcedConcreteBeamDesignEngine,
    ReinforcedConcreteBeamDesignExporter,
)

DEFAULT_INPUT = ROOT / "configs/structural/reinforced_concrete_beam_example_v1_0_0.json"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-json", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--verify-against-artifacts", type=Path)
    parser.add_argument("--expect-design-valid", action="store_true")
    args = parser.parse_args(argv)

    input_path = args.input_json
    if not input_path.is_absolute():
        input_path = ROOT / input_path
    config = json.loads(input_path.read_text(encoding="utf-8"))
    result = ReinforcedConcreteBeamDesignEngine().evaluate(config)

    temporary = None
    if args.output_dir is None:
        temporary = tempfile.TemporaryDirectory()
        output_dir = Path(temporary.name)
    else:
        output_dir = args.output_dir

    paths = ReinforcedConcreteBeamDesignExporter(result).export_all(output_dir)
    mismatch_paths = []
    artifacts_match = None
    if args.verify_against_artifacts:
        expected_root = args.verify_against_artifacts
        if not expected_root.is_absolute():
            expected_root = ROOT / expected_root
        expected = sorted(
            p.relative_to(expected_root).as_posix()
            for p in expected_root.rglob("*") if p.is_file()
        )
        actual = sorted(
            p.relative_to(output_dir).as_posix()
            for p in output_dir.rglob("*") if p.is_file()
        )
        if expected != actual:
            mismatch_paths = sorted(set(expected) ^ set(actual))
        else:
            mismatch_paths = [
                rel for rel in expected
                if (expected_root / rel).read_bytes() != (output_dir / rel).read_bytes()
            ]
        artifacts_match = not mismatch_paths

    valid = (
        result["status"] == "PRELIMINARY_DESIGN_CHECKS_PASSED"
        and result["metrics"]["technical_check_count"] == 13
        and result["metrics"]["technical_checks_passed"] == 13
        and result["metrics"]["all_technical_checks_passed"]
        and result["metrics"]["professional_review_required"]
        and not result["metrics"]["final_structural_release_allowed"]
        and len(paths) == 18
    )
    if artifacts_match is False:
        valid = False

    output = {
        "execution_status": "PASSED" if valid else "FAILED",
        "design_status": result["status"],
        "project_id": result["project_id"],
        "beam_id": result["beam_id"],
        "span_m": result["geometry"]["span_m"],
        "section_mm": f"{result['geometry']['width_mm']:.0f}x{result['geometry']['height_mm']:.0f}",
        "uls_max_moment_knm": result["analysis"]["uls_max_moment_knm"],
        "uls_max_shear_kn": result["analysis"]["uls_max_abs_shear_kn"],
        "bottom_reinforcement": result["detailing"]["bottom_reinforcement"],
        "stirrups": result["detailing"]["stirrups"],
        "estimated_deflection_mm": result["serviceability"]["estimated_deflection_mm"],
        "estimated_crack_width_mm": result["serviceability"]["estimated_crack_width_mm"],
        "technical_checks_passed": result["metrics"]["technical_checks_passed"],
        "technical_check_count": result["metrics"]["technical_check_count"],
        "professional_review_required": result["metrics"]["professional_review_required"],
        "final_structural_release_allowed": result["metrics"]["final_structural_release_allowed"],
        "artifacts_match": artifacts_match,
        "artifact_mismatch_count": len(mismatch_paths),
        "artifact_mismatch_paths": mismatch_paths,
        "output_file_count": sum(1 for p in output_dir.rglob("*") if p.is_file()),
        "outputs": {key: str(value) for key, value in sorted(paths.items())},
        "next_gate": result["next_gate"],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    if temporary is not None:
        temporary.cleanup()
    if args.expect_design_valid:
        return 0 if valid else 1
    return 0 if valid else 2


if __name__ == "__main__":
    raise SystemExit(main())
