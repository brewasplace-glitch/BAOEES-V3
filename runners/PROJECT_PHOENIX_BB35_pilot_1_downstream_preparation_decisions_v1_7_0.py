"""Run downstream preparation decisions v1.7.0."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phoenix.bb35_pilots.moskee_bunschoten.downstream_preparation_decisions import (
    DownstreamPreparationDecisionsEngine,
    DownstreamPreparationDecisionsExporter,
)


def load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--verify-against-artifacts", type=Path)
    parser.add_argument("--expect-preparation-ready", action="store_true")
    args = parser.parse_args(argv)

    report = DownstreamPreparationDecisionsEngine().evaluate(
        req107_summary=load(
            "artifacts/bb35/pilot_1_moskee_bunschoten/"
            "req_107_occupancy_use_decision_v1_6_0/"
            "01_req107_decision_summary.json"
        ),
        req107_program=load(
            "artifacts/bb35/pilot_1_moskee_bunschoten/"
            "req_107_occupancy_use_decision_v1_6_0/"
            "02_authoritative_occupancy_use_program.json"
        ),
        req107_decision_register=load(
            "artifacts/bb35/pilot_1_moskee_bunschoten/"
            "req_107_occupancy_use_decision_v1_6_0/"
            "03_updated_strategic_decision_register.json"
        ),
        closure_plan=load(
            "artifacts/bb35/pilot_1_moskee_bunschoten/"
            "evidence_validation_closure_plan_v1_5_0/"
            "01_evidence_validation_summary.json"
        ),
        owner_input=load(
            "inputs/pilots/moskee_bunschoten/"
            "downstream_preparation_owner_decisions_v1_7_0.json"
        ),
    )

    temporary = None
    if args.output_dir is None:
        temporary = tempfile.TemporaryDirectory()
        output_dir = Path(temporary.name)
    else:
        output_dir = args.output_dir

    paths = DownstreamPreparationDecisionsExporter().export_all(
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

    basis = report["selected_strategic_basis"]
    expected_status = (
        report["status"]
        == (
            "ALL_STRATEGIC_DECISIONS_OWNER_APPROVED_"
            "DOWNSTREAM_PREPARATION_READY"
        )
        and report["approved_strategic_decision_count"] == 8
        and report["pending_strategic_decision_count"] == 0
        and report["all_strategic_decisions_approved"]
        and basis["kitchen_function"] == "geen_keukenfunctie"
        and basis["installation_sustainability_level"]
        == "wettelijk_minimum"
        and basis["parking_strategy"] == "openbare_capaciteit"
        and basis["execution_phasing"] == "gefaseerde_uitvoering"
        and basis["mosque_remains_in_use_during_construction"]
        and report["workstream_count"] == 3
        and report["parallel_preparation_allowed"]
        and report["professional_evidence_still_required"]
        and not report["final_generation_allowed"]
        and not report["bb36_unlock_allowed"]
    )
    if artifacts_match is False:
        expected_status = False

    result = {
        "execution_status": "PASSED" if expected_status else "FAILED",
        "decision_status": report["status"],
        "approved_strategic_decision_count": (
            report["approved_strategic_decision_count"]
        ),
        "pending_strategic_decision_count": (
            report["pending_strategic_decision_count"]
        ),
        "kitchen_function": basis["kitchen_function"],
        "installation_sustainability_level": (
            basis["installation_sustainability_level"]
        ),
        "parking_strategy": basis["parking_strategy"],
        "execution_phasing": basis["execution_phasing"],
        "mosque_remains_in_use_during_construction": (
            basis["mosque_remains_in_use_during_construction"]
        ),
        "workstream_count": report["workstream_count"],
        "workstream_statuses": {
            request_id: workstream["status"]
            for request_id, workstream
            in sorted(report["workstreams"].items())
        },
        "parallel_preparation_allowed": (
            report["parallel_preparation_allowed"]
        ),
        "professional_evidence_still_required": (
            report["professional_evidence_still_required"]
        ),
        "req107_formal_cosign_still_pending": (
            report["req107_formal_cosign_still_pending"]
        ),
        "remaining_blocking_input_count": (
            report["remaining_blocking_input_count"]
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

    if args.expect_preparation_ready:
        return 0 if expected_status else 1
    return 0 if expected_status else 2


if __name__ == "__main__":
    raise SystemExit(main())
