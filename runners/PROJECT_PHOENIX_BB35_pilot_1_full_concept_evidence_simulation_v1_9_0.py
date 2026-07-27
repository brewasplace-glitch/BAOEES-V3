"""Run BB35 Pilot 1 full concept evidence simulation v1.9.0."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phoenix.bb35_pilots.moskee_bunschoten.full_concept_evidence_simulation import (
    FullConceptEvidenceSimulationEngine,
    FullConceptEvidenceSimulationExporter,
)


def load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--verify-against-artifacts", type=Path)
    parser.add_argument("--expect-simulation-passed", action="store_true")
    args = parser.parse_args(argv)

    report = FullConceptEvidenceSimulationEngine().evaluate(
        req107_program=load(
            "artifacts/bb35/pilot_1_moskee_bunschoten/"
            "req_107_occupancy_use_decision_v1_6_0/"
            "02_authoritative_occupancy_use_program.json"
        ),
        downstream_summary=load(
            "artifacts/bb35/pilot_1_moskee_bunschoten/"
            "downstream_preparation_decisions_v1_7_0/"
            "01_downstream_decision_summary.json"
        ),
        parallel_summary=load(
            "artifacts/bb35/pilot_1_moskee_bunschoten/"
            "parallel_preparation_workpacks_v1_8_0/"
            "01_parallel_preparation_summary.json"
        ),
        authorization=load(
            "inputs/pilots/moskee_bunschoten/"
            "full_concept_simulation_authorization_v1_9_0.json"
        ),
        config=load(
            "configs/projects/"
            "moskee_bunschoten_full_concept_evidence_simulation_v1_9_0.json"
        ),
    )

    temporary = None
    if args.output_dir is None:
        temporary = tempfile.TemporaryDirectory()
        output_dir = Path(temporary.name)
    else:
        output_dir = args.output_dir

    paths = FullConceptEvidenceSimulationExporter().export_all(report, output_dir)

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
                if (expected_root / relative).read_bytes() != (output_dir / relative).read_bytes()
            ]
        artifacts_match = not mismatch_paths

    expected_status = (
        report["status"] == "FULL_CONCEPT_EVIDENCE_SIMULATION_RUN_PASSED"
        and report["concept_simulation_count"] == 6
        and report["project_leader_closed_request_count"] == 1
        and report["req107_status"] == "CLOSED_PROJECT_LEADER_APPROVED"
        and report["parking_basis_spaces"] == 225
        and report["parking_previous_hypothesis_spaces"] == 300
        and report["remaining_professional_evidence_blockers"] == 6
        and report["all_consistency_checks_passed"]
        and report["end_to_end_workflow_validated"]
        and report["concept_dossier_generation_allowed"]
        and report["bb36_functional_validation_passed"]
        and not report["final_permit_ready_generation_allowed"]
        and not report["bb36_production_release_allowed"]
    )
    if artifacts_match is False:
        expected_status = False

    result = {
        "execution_status": "PASSED" if expected_status else "FAILED",
        "simulation_status": report["status"],
        "requests": report["req_range"],
        "concept_simulation_count": report["concept_simulation_count"],
        "req107_status": report["req107_status"],
        "parking_basis_spaces": report["parking_basis_spaces"],
        "previous_parking_hypothesis_spaces": report["parking_previous_hypothesis_spaces"],
        "remaining_professional_evidence_blockers": report["remaining_professional_evidence_blockers"],
        "consistency_check_count": report["consistency_check_count"],
        "all_consistency_checks_passed": report["all_consistency_checks_passed"],
        "end_to_end_workflow_validated": report["end_to_end_workflow_validated"],
        "concept_dossier_generation_allowed": report["concept_dossier_generation_allowed"],
        "final_permit_ready_generation_allowed": report["final_permit_ready_generation_allowed"],
        "bb36_functional_validation_passed": report["bb36_functional_validation_passed"],
        "bb36_production_release_allowed": report["bb36_production_release_allowed"],
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

    if args.expect_simulation_passed:
        return 0 if expected_status else 1
    return 0 if expected_status else 2


if __name__ == "__main__":
    raise SystemExit(main())
