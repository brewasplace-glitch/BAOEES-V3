"""Run BB35 Pilot 1 uploaded evidence intake v1.4.1."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phoenix.bb35_pilots.moskee_bunschoten.uploaded_evidence_intake import (
    UploadedEvidenceIntakeEngine,
    UploadedEvidenceIntakeExporter,
)


def load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--expect-partial-satisfaction", action="store_true")
    args = parser.parse_args(argv)

    report = UploadedEvidenceIntakeEngine().evaluate(
        manifest=load(
            "inputs/pilots/moskee_bunschoten/"
            "uploaded_evidence_manifest_v1_4_1.json"
        ),
        register=load(
            "inputs/pilots/moskee_bunschoten/"
            "verified_inputs_register_v1_2_0.json"
        ),
        evidence_root=(
            ROOT / "inputs/pilots/moskee_bunschoten/"
            "uploaded_evidence/v1_4_1"
        ),
    )

    temporary = None
    if args.output_dir is None:
        temporary = tempfile.TemporaryDirectory()
        output_dir = Path(temporary.name)
    else:
        output_dir = args.output_dir

    paths = UploadedEvidenceIntakeExporter().export_all(report, output_dir)

    expected = (
        report["status"] == "EVIDENCE_ACQUISITION_PARTIALLY_SATISFIED"
        and report["valid_file_count"] == 6
        and report["closed_request_count"] == 1
        and report["partial_request_count"] == 2
        and report["open_request_count"] == 5
        and report["remaining_blocking_input_count"] == 7
        and not report["final_generation_allowed"]
        and not report["bb36_unlock_allowed"]
    )

    print(json.dumps({
        "status": "PASSED" if expected else "FAILED",
        "pilot_id": report["pilot_id"],
        "project_id": report["project_id"],
        "intake_status": report["status"],
        "valid_file_count": report["valid_file_count"],
        "received_file_count": report["received_file_count"],
        "closed_request_count": report["closed_request_count"],
        "partial_request_count": report["partial_request_count"],
        "open_request_count": report["open_request_count"],
        "remaining_blocking_input_count": (
            report["remaining_blocking_input_count"]
        ),
        "verified_project_fact_count": (
            report["verified_project_fact_count"]
        ),
        "final_generation_allowed": report["final_generation_allowed"],
        "bb36_unlock_allowed": report["bb36_unlock_allowed"],
        "next_gate": report["next_gate"],
        "outputs": {
            key: str(value) for key, value in sorted(paths.items())
        },
    }, ensure_ascii=False, indent=2))

    if temporary is not None:
        temporary.cleanup()

    if args.expect_partial_satisfaction:
        return 0 if expected else 1
    return 0 if expected else 2


if __name__ == "__main__":
    raise SystemExit(main())
