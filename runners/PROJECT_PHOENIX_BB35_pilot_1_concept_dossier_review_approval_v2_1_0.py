"""Run BB35 concept dossier review and approval v2.1.0."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phoenix.bb35_pilots.moskee_bunschoten.concept_dossier_review_approval import (
    ConceptDossierReviewApprovalEngine,
    ConceptDossierReviewApprovalExporter,
)


def load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--verify-against-artifacts", type=Path)
    parser.add_argument("--expect-approved", action="store_true")
    args = parser.parse_args(argv)

    report = ConceptDossierReviewApprovalEngine().evaluate(
        dossier_summary=load(
            "artifacts/bb35/pilot_1_moskee_bunschoten/"
            "integrated_concept_dossier_v2_0_2/"
            "01_integrated_concept_dossier_summary.json"
        ),
        release_gate=load(
            "artifacts/bb35/pilot_1_moskee_bunschoten/"
            "integrated_concept_dossier_v2_0_2/"
            "14_release_gate_status.json"
        ),
        config=load(
            "configs/projects/"
            "moskee_bunschoten_concept_dossier_review_approval_v2_1_0.json"
        ),
    )

    temporary = None
    if args.output_dir is None:
        temporary = tempfile.TemporaryDirectory()
        output_dir = Path(temporary.name)
    else:
        output_dir = args.output_dir

    paths = ConceptDossierReviewApprovalExporter().export_all(
        report,
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
                if (
                    expected_root / relative
                ).read_bytes() != (
                    output_dir / relative
                ).read_bytes()
            ]
        artifacts_match = not mismatch_paths

    gates = report["gates"]
    expected_status = (
        report["status"]
        == "CONCEPT_DOSSIER_REVIEWED_PROJECT_LEADER_APPROVED"
        and report["review_check_count"] == 12
        and report["review_checks_passed"] == 12
        and report["all_review_checks_passed"]
        and report["unresolved_project_leader_review_findings"] == 0
        and report["professional_blocker_count"] == 6
        and report["parking_basis_spaces"] == 225
        and report["req107_status"]
        == "CLOSED_PROJECT_LEADER_APPROVED"
        and gates["concept_dossier_review_completed"]
        and gates["project_leader_approval_recorded"]
        and gates["concept_stage_accepted_for_pilot_validation"]
        and gates["professional_evidence_replacement_allowed"]
        and not gates["final_permit_ready_generation_allowed"]
        and gates["bb36_functional_validation_passed"]
        and not gates["bb36_production_release_allowed"]
    )
    if artifacts_match is False:
        expected_status = False

    result = {
        "execution_status": "PASSED" if expected_status else "FAILED",
        "review_status": report["status"],
        "review_id": report["review_id"],
        "dossier_id": report["dossier_id"],
        "review_check_count": report["review_check_count"],
        "review_checks_passed": report["review_checks_passed"],
        "project_leader_approval_recorded": gates[
            "project_leader_approval_recorded"
        ],
        "approval_scope": report["approval"]["approval_scope"],
        "professional_blocker_count": (
            report["professional_blocker_count"]
        ),
        "parking_basis_spaces": report["parking_basis_spaces"],
        "req107_status": report["req107_status"],
        "professional_evidence_replacement_allowed": gates[
            "professional_evidence_replacement_allowed"
        ],
        "final_permit_ready_generation_allowed": gates[
            "final_permit_ready_generation_allowed"
        ],
        "bb36_functional_validation_passed": gates[
            "bb36_functional_validation_passed"
        ],
        "bb36_production_release_allowed": gates[
            "bb36_production_release_allowed"
        ],
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

    if args.expect_approved:
        return 0 if expected_status else 1
    return 0 if expected_status else 2


if __name__ == "__main__":
    raise SystemExit(main())
