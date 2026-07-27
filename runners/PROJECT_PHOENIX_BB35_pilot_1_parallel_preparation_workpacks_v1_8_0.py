"""Run BB35 parallel preparation workpacks v1.8.0."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phoenix.bb35_pilots.moskee_bunschoten.parallel_preparation_workpacks import (
    ParallelPreparationWorkpacksEngine,
    ParallelPreparationWorkpacksExporter,
)


def load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--verify-against-artifacts", type=Path)
    parser.add_argument("--expect-workpacks-ready", action="store_true")
    args = parser.parse_args(argv)

    report = ParallelPreparationWorkpacksEngine().evaluate(
        downstream_summary=load(
            "artifacts/bb35/pilot_1_moskee_bunschoten/"
            "downstream_preparation_decisions_v1_7_0/"
            "01_downstream_decision_summary.json"
        ),
        downstream_basis=load(
            "artifacts/bb35/pilot_1_moskee_bunschoten/"
            "downstream_preparation_decisions_v1_7_0/"
            "03_authoritative_downstream_preparation_basis.json"
        ),
        occupancy_program=load(
            "artifacts/bb35/pilot_1_moskee_bunschoten/"
            "req_107_occupancy_use_decision_v1_6_0/"
            "02_authoritative_occupancy_use_program.json"
        ),
        config=load(
            "configs/projects/"
            "moskee_bunschoten_parallel_preparation_workpacks_v1_8_0.json"
        ),
    )

    temporary = None
    if args.output_dir is None:
        temporary = tempfile.TemporaryDirectory()
        output_dir = Path(temporary.name)
    else:
        output_dir = args.output_dir

    paths = ParallelPreparationWorkpacksExporter().export_all(
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

    expected_status = (
        report["status"]
        == (
            "PARALLEL_PREPARATION_WORKPACKS_GENERATED_"
            "EXTERNAL_EVIDENCE_PENDING"
        )
        and report["workpack_count"] == 3
        and report["parallel_execution_allowed"]
        and report["all_strategic_decisions_approved"]
        and report["professional_evidence_still_required"]
        and report["req107_formal_cosign_still_pending"]
        and report["parking_provisional_capacity_spaces"] == 300
        and report["parking_measurement_count"] == 5
        and report["aerius_phase_template_count"] == 5
        and not report["final_generation_allowed"]
        and not report["bb36_unlock_allowed"]
    )
    if artifacts_match is False:
        expected_status = False

    result = {
        "execution_status": "PASSED" if expected_status else "FAILED",
        "plan_status": report["status"],
        "workpack_count": report["workpack_count"],
        "workpack_statuses": {
            request_id: workpack["workpack_status"]
            for request_id, workpack
            in sorted(report["workpacks"].items())
        },
        "parallel_execution_allowed": (
            report["parallel_execution_allowed"]
        ),
        "parking_provisional_capacity_spaces": (
            report["parking_provisional_capacity_spaces"]
        ),
        "parking_hypothesis_status": (
            report["parking_hypothesis_status"]
        ),
        "parking_measurement_count": (
            report["parking_measurement_count"]
        ),
        "aerius_phase_template_count": (
            report["aerius_phase_template_count"]
        ),
        "professional_evidence_still_required": (
            report["professional_evidence_still_required"]
        ),
        "req107_formal_cosign_still_pending": (
            report["req107_formal_cosign_still_pending"]
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

    if args.expect_workpacks_ready:
        return 0 if expected_status else 1
    return 0 if expected_status else 2


if __name__ == "__main__":
    raise SystemExit(main())
