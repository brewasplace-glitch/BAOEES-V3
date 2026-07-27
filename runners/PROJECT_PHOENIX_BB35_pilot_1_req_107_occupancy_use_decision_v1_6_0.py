"""Run REQ-107 occupancy and use decision v1.6.0."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phoenix.bb35_pilots.moskee_bunschoten.req_107_occupancy_use_decision import (
    Req107OccupancyUseDecisionEngine,
    Req107OccupancyUseDecisionExporter,
)


def load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--verify-against-artifacts", type=Path)
    parser.add_argument("--expect-owner-approved", action="store_true")
    args = parser.parse_args(argv)

    report = Req107OccupancyUseDecisionEngine().evaluate(
        closure_summary=load(
            "artifacts/bb35/pilot_1_moskee_bunschoten/"
            "evidence_validation_closure_plan_v1_5_0/"
            "01_evidence_validation_summary.json"
        ),
        closure_register=load(
            "inputs/pilots/moskee_bunschoten/"
            "evidence_closure_plan_register_v1_5_0.json"
        ),
        owner_input=load(
            "inputs/pilots/moskee_bunschoten/"
            "req_107_owner_decision_input_v1_6_0.json"
        ),
    )

    temporary = None
    if args.output_dir is None:
        temporary = tempfile.TemporaryDirectory()
        output_dir = Path(temporary.name)
    else:
        output_dir = args.output_dir

    paths = Req107OccupancyUseDecisionExporter().export_all(
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

    program = report["authoritative_program"]
    scenarios = program["occupancy_scenarios"]
    expected_status = (
        report["status"]
        == "REQ_107_OWNER_DECISION_APPROVED_FORMAL_COSIGN_PENDING"
        and report["req107_strategic_decision_complete"]
        and not report["req107_formal_closure_complete"]
        and report["approved_req107_decision_count"] == 4
        and report["remaining_pending_strategic_decision_count"] == 4
        and scenarios["regular"]["existing_persons"] == 80
        and scenarios["regular"]["future_persons"] == 150
        and scenarios["friday_prayer"]["existing_persons"] == 65
        and scenarios["friday_prayer"]["future_persons"] == 125
        and scenarios["special_peak"]["maximum_persons"] == 200
        and scenarios["special_peak"]["frequency_per_year"] == 1
        and all(report["downstream_preparation_allowed"].values())
        and not any(report["downstream_finalization_allowed"].values())
        and not report["final_generation_allowed"]
        and not report["bb36_unlock_allowed"]
    )

    if artifacts_match is False:
        expected_status = False

    result = {
        "execution_status": "PASSED" if expected_status else "FAILED",
        "pilot_id": report["pilot_id"],
        "project_id": report["project_id"],
        "decision_status": report["status"],
        "program_id": program["program_id"],
        "approved_req107_decision_count": (
            report["approved_req107_decision_count"]
        ),
        "remaining_pending_strategic_decision_count": (
            report["remaining_pending_strategic_decision_count"]
        ),
        "regular_existing_persons": scenarios["regular"][
            "existing_persons"
        ],
        "regular_future_persons": scenarios["regular"][
            "future_persons"
        ],
        "friday_existing_persons": scenarios["friday_prayer"][
            "existing_persons"
        ],
        "friday_future_persons": scenarios["friday_prayer"][
            "future_persons"
        ],
        "special_peak_persons": scenarios["special_peak"][
            "maximum_persons"
        ],
        "special_peak_frequency_per_year": scenarios["special_peak"][
            "frequency_per_year"
        ],
        "opening_schedule_count": len(program["opening_hours"]),
        "req107_formal_cosign_required": (
            report["req107_formal_cosign_required"]
        ),
        "downstream_preparation_allowed": (
            report["downstream_preparation_allowed"]
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

    if args.expect_owner_approved:
        return 0 if expected_status else 1
    return 0 if expected_status else 2


if __name__ == "__main__":
    raise SystemExit(main())
