"""Run the BB35 real concept drawings and reports production engine."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phoenix.production.real_drawings_reports import RealConceptProductionEngine

CONFIG_REL = Path("configs/projects/moskee_bunschoten_real_concept_production_v1_0_0.json")


def load_config():
    return json.loads((ROOT / CONFIG_REL).read_text(encoding="utf-8"))


def compare_trees(expected: Path, actual: Path) -> list[str]:
    expected_names = sorted(p.relative_to(expected).as_posix() for p in expected.rglob("*") if p.is_file())
    actual_names = sorted(p.relative_to(actual).as_posix() for p in actual.rglob("*") if p.is_file())
    if expected_names != actual_names:
        return sorted(set(expected_names) ^ set(actual_names))
    return [name for name in expected_names if (expected / name).read_bytes() != (actual / name).read_bytes()]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--verify-against-artifacts", type=Path)
    parser.add_argument("--expect-production-ready", action="store_true")
    args = parser.parse_args(argv)

    temporary = None
    if args.output_dir is None:
        temporary = tempfile.TemporaryDirectory()
        output_dir = Path(temporary.name)
    else:
        output_dir = args.output_dir

    result = RealConceptProductionEngine(load_config()).produce(output_dir)
    summary = result["summary"]
    mismatches = []
    artifacts_match = None
    if args.verify_against_artifacts:
        mismatches = compare_trees(args.verify_against_artifacts, output_dir)
        artifacts_match = not mismatches

    passed = (
        summary["status"] == "REAL_CONCEPT_DRAWINGS_AND_REPORTS_GENERATED"
        and summary["drawing_sheet_count"] == 10
        and summary["drawing_pdf_count"] == 11
        and summary["drawing_svg_count"] == 10
        and summary["drawing_dxf_count"] == 5
        and summary["report_count"] == 6
        and summary["report_pdf_count"] == 6
        and summary["report_docx_count"] == 6
        and summary["cross_check_count"] == 14
        and summary["cross_checks_passed"] == 14
        and summary["all_cross_checks_passed"]
        and summary["concept_issue_package_ready"]
        and summary["professional_evidence_blocker_count"] == 6
        and summary["parking_basis_spaces"] == 225
        and summary["req107_status"] == "CLOSED_PROJECT_LEADER_APPROVED"
        and not summary["final_permit_ready_generation_allowed"]
        and not summary["bb36_production_release_allowed"]
        and artifacts_match is not False
    )
    output = {
        "execution_status": "PASSED" if passed else "FAILED",
        "production_status": summary["status"],
        "issue_id": summary["issue_id"],
        "drawing_sheet_count": summary["drawing_sheet_count"],
        "drawing_pdf_count": summary["drawing_pdf_count"],
        "drawing_svg_count": summary["drawing_svg_count"],
        "drawing_dxf_count": summary["drawing_dxf_count"],
        "report_count": summary["report_count"],
        "report_pdf_count": summary["report_pdf_count"],
        "report_docx_count": summary["report_docx_count"],
        "cross_checks_passed": summary["cross_checks_passed"],
        "professional_evidence_blockers": summary["professional_evidence_blocker_count"],
        "parking_basis_spaces": summary["parking_basis_spaces"],
        "req107_status": summary["req107_status"],
        "concept_issue_package_ready": summary["concept_issue_package_ready"],
        "final_permit_ready_generation_allowed": summary["final_permit_ready_generation_allowed"],
        "bb36_production_release_allowed": summary["bb36_production_release_allowed"],
        "output_file_count": summary["output_file_count"],
        "artifacts_match": artifacts_match,
        "artifact_mismatch_count": len(mismatches),
        "artifact_mismatch_paths": mismatches,
        "output_dir": str(output_dir),
        "next_gate": summary["next_gate"],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))

    if temporary is not None:
        temporary.cleanup()
    if args.expect_production_ready:
        return 0 if passed else 1
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
