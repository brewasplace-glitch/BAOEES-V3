"""Run BB35 professional evidence replacement programme v2.2.0."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phoenix.bb35_pilots.moskee_bunschoten.professional_evidence_replacement_programme import (
    ProfessionalEvidenceReplacementProgrammeEngine,
    ProfessionalEvidenceReplacementProgrammeExporter,
)


def load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--verify-against-artifacts", type=Path)
    parser.add_argument("--expect-programme-ready", action="store_true")
    args = parser.parse_args(argv)

    config = load(
        "configs/projects/"
        "moskee_bunschoten_professional_evidence_replacement_programme_v2_2_0.json"
    )
    report = ProfessionalEvidenceReplacementProgrammeEngine().evaluate(
        review_summary=load(
            "artifacts/bb35/pilot_1_moskee_bunschoten/"
            "concept_dossier_review_project_leader_approval_v2_1_0/"
            "01_review_approval_summary.json"
        ),
        orchestrator_summary=load(
            "artifacts/bb35/pilot_1_moskee_bunschoten/"
            "unified_model_driven_production_orchestrator_v1_0_0/"
            "01_orchestrator_summary.json"
        ),
        release_gate=load(
            "artifacts/bb35/pilot_1_moskee_bunschoten/"
            "unified_model_driven_production_orchestrator_v1_0_0/"
            "14_release_gate_status.json"
        ),
        config=config,
    )

    temporary = None
    if args.output_dir is None:
        temporary = tempfile.TemporaryDirectory()
        output_dir = Path(temporary.name)
    else:
        output_dir = args.output_dir

    paths = ProfessionalEvidenceReplacementProgrammeExporter().export_all(
        report,
        config,
        output_dir,
    )

    mismatch_paths = []
    artifacts_match = None
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
                if (expected_root / relative).read_bytes()
                != (output_dir / relative).read_bytes()
            ]
        artifacts_match = not mismatch_paths

    gates = report["gates"]
    expected_status = (
        report["status"]
        == "PROFESSIONAL_EVIDENCE_REPLACEMENT_PROGRAMME_READY"
        and report["replacement_request_count"] == 6
        and report["workpack_count"] == 6
        and report["excluded_closed_request"] == "REQ-107"
        and report["req107_status"] == "CLOSED_PROJECT_LEADER_APPROVED"
        and report["parking_basis_spaces"] == 225
        and report["gate_checks_passed"] == report["gate_check_count"] == 12
        and gates["programme_ready"]
        and gates["adviser_issue_allowed"]
        and gates["evidence_intake_allowed"]
        and not gates["evidence_validation_complete"]
        and not gates["all_professional_evidence_accepted"]
        and not gates["final_permit_ready_generation_allowed"]
        and not gates["bb36_production_release_allowed"]
    )
    if artifacts_match is False:
        expected_status = False

    result = {
        "execution_status": "PASSED" if expected_status else "FAILED",
        "status": report["status"],
        "programme_id": report["programme_id"],
        "replacement_requests": report["replacement_requests"],
        "workpack_count": report["workpack_count"],
        "gate_check_count": report["gate_check_count"],
        "gate_checks_passed": report["gate_checks_passed"],
        "req107_status": report["req107_status"],
        "parking_basis_spaces": report["parking_basis_spaces"],
        "professional_evidence_blocker_count": report["professional_evidence_blocker_count"],
        "professional_evidence_accepted_count": report["professional_evidence_accepted_count"],
        "evidence_intake_allowed": gates["evidence_intake_allowed"],
        "final_permit_ready_generation_allowed": gates["final_permit_ready_generation_allowed"],
        "bb36_production_release_allowed": gates["bb36_production_release_allowed"],
        "artifacts_match": artifacts_match,
        "artifact_mismatch_count": len(mismatch_paths),
        "artifact_mismatch_paths": mismatch_paths,
        "output_file_count": sum(1 for path in output_dir.rglob("*") if path.is_file()),
        "outputs": {key: str(value) for key, value in sorted(paths.items())},
        "next_gate": report["next_gate"],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if temporary is not None:
        temporary.cleanup()

    if args.expect_programme_ready:
        return 0 if expected_status else 1
    return 0 if expected_status else 2


if __name__ == "__main__":
    raise SystemExit(main())
