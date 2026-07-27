"""Run BB35 Evidence Validation & Closure Plan v1.5.0."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phoenix.bb35_pilots.moskee_bunschoten.evidence_validation_closure_plan import (
    EvidenceValidationClosurePlanEngine,
    EvidenceValidationClosurePlanExporter,
)


def load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--verify-against-artifacts", type=Path)
    parser.add_argument("--expect-plan-ready", action="store_true")
    args = parser.parse_args(argv)

    report = EvidenceValidationClosurePlanEngine().evaluate(
        intake_report=load(
            "artifacts/bb35/pilot_1_moskee_bunschoten/"
            "uploaded_evidence_intake_v1_4_1/"
            "01_uploaded_evidence_intake_report.json"
        ),
        verified_register=load(
            "inputs/pilots/moskee_bunschoten/"
            "verified_inputs_register_v1_2_0.json"
        ),
        review_summary=load(
            "artifacts/bb35/pilot_1_moskee_bunschoten/"
            "concept_review_evidence_acquisition_v1_4_0/"
            "01_concept_review_summary.json"
        ),
        closure_register=load(
            "inputs/pilots/moskee_bunschoten/"
            "evidence_closure_plan_register_v1_5_0.json"
        ),
        config=load(
            "configs/projects/"
            "moskee_bunschoten_"
            "evidence_validation_closure_plan_v1_5_0.json"
        ),
    )

    temporary = None
    if args.output_dir is None:
        temporary = tempfile.TemporaryDirectory()
        output_dir = Path(temporary.name)
    else:
        output_dir = args.output_dir

    paths = EvidenceValidationClosurePlanExporter().export_all(
        report,
        output_dir,
    )

    artifacts_match = None
    mismatch_paths = []
    if args.verify_against_artifacts:
        expected_root = args.verify_against_artifacts
        expected = sorted(
            path.relative_to(expected_root).as_posix()
            for path in expected_root.rglob("*")
            if path.is_file()
        )
        actual = sorted(
            path.relative_to(output_dir).as_posix()
            for path in output_dir.rglob("*")
            if path.is_file()
        )
        if expected != actual:
            mismatch_paths = sorted(set(expected) ^ set(actual))
        else:
            mismatch_paths = [
                relative
                for relative in expected
                if (
                    expected_root / relative
                ).read_bytes() != (
                    output_dir / relative
                ).read_bytes()
            ]
        artifacts_match = not mismatch_paths

    expected_status = (
        report["status"]
        == "EVIDENCE_VALIDATION_COMPLETE_CLOSURE_PLAN_READY"
        and report["closure_item_count"] == 7
        and report["remaining_blocking_input_count"] == 7
        and report["strategic_decision_count"] == 8
        and report["professional_work_order_count"] == 6
        and report["critical_path_root"] == "REQ-107"
        and report["critical_path_downstream_requests"]
        == ["REQ-105", "REQ-106", "REQ-108"]
        and not report["final_generation_allowed"]
        and not report["bb36_unlock_allowed"]
    )

    if artifacts_match is False:
        expected_status = False

    result = {
        "execution_status": "PASSED" if expected_status else "FAILED",
        "pilot_id": report["pilot_id"],
        "project_id": report["project_id"],
        "plan_status": report["status"],
        "closure_item_count": report["closure_item_count"],
        "remaining_blocking_input_count": (
            report["remaining_blocking_input_count"]
        ),
        "strategic_decision_count": (
            report["strategic_decision_count"]
        ),
        "professional_work_order_count": (
            report["professional_work_order_count"]
        ),
        "internal_automation_action_count": (
            report["internal_automation_action_count"]
        ),
        "acceptance_criterion_count": (
            report["acceptance_criterion_count"]
        ),
        "critical_path_root": report["critical_path_root"],
        "critical_path_downstream_requests": (
            report["critical_path_downstream_requests"]
        ),
        "recommended_execution_order": (
            report["recommended_execution_order"]
        ),
        "closure_execution_allowed": (
            report["closure_execution_allowed"]
        ),
        "final_generation_allowed": (
            report["final_generation_allowed"]
        ),
        "bb36_unlock_allowed": report["bb36_unlock_allowed"],
        "artifacts_match": artifacts_match,
        "artifact_mismatch_count": len(mismatch_paths),
        "artifact_mismatch_paths": mismatch_paths,
        "output_file_count": sum(
            1 for path in output_dir.rglob("*") if path.is_file()
        ),
        "outputs": {
            key: str(value)
            for key, value in sorted(paths.items())
        },
        "next_gate": report["next_gate"],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if temporary is not None:
        temporary.cleanup()

    if args.expect_plan_ready:
        return 0 if expected_status else 1
    return 0 if expected_status else 2


if __name__ == "__main__":
    raise SystemExit(main())
