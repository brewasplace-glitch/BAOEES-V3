"""Run the Moskee Bunschoten verified-input gate."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phoenix.bb35_pilots.moskee_bunschoten.verified_inputs import (
    MoskeeBunschotenVerifiedInputsGate,
)
from phoenix.bb35_pilots.moskee_bunschoten.verified_inputs_exporters import (
    MoskeeBunschotenVerifiedInputsExporter,
)


def load(relative: str):
    return json.loads(
        (ROOT / relative).read_text(encoding="utf-8")
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--expect-external-evidence-hold",
        action="store_true",
    )
    args = parser.parse_args(argv)

    report = MoskeeBunschotenVerifiedInputsGate().evaluate(
        config=load(
            "configs/projects/"
            "moskee_bunschoten_bb35_pilot_1.json"
        ),
        register=load(
            "inputs/pilots/moskee_bunschoten/"
            "verified_inputs_register_v1_2_0.json"
        ),
        baseline_manifest=load(
            "inputs/pilots/moskee_bunschoten/"
            "evidence_manifest.json"
        ),
        baseline_evidence_root=(
            ROOT
            / "inputs/pilots/moskee_bunschoten/"
            "source_evidence"
        ),
        administrative_manifest=load(
            "inputs/pilots/moskee_bunschoten/"
            "administrative_evidence_manifest_v1_2_0.json"
        ),
        administrative_evidence_root=(
            ROOT
            / "inputs/pilots/moskee_bunschoten/"
            "verified_inputs/administrative_evidence"
        ),
    )

    temporary = None
    if args.output_dir is None:
        temporary = tempfile.TemporaryDirectory()
        output_dir = Path(temporary.name)
    else:
        output_dir = args.output_dir

    paths = MoskeeBunschotenVerifiedInputsExporter().export_all(
        report,
        output_dir,
    )

    expected_hold = (
        report["status"]
        == "BLOCKED_PENDING_EXTERNAL_TECHNICAL_EVIDENCE"
        and report["valid_evidence_count"]
        == report["evidence_count"]
        and report["concept_generation_allowed"]
        and not report["final_generation_allowed"]
        and not report["bb36_unlock_allowed"]
    )

    print(json.dumps({
        "status": "PASSED" if expected_hold else "FAILED",
        "pilot_id": report["pilot_id"],
        "project_id": report["project_id"],
        "gate_status": report["status"],
        "authoritative_scope": (
            "7.00 x 10.00 m, two storeys, 140 m² gross"
        ),
        "valid_evidence_count": report[
            "valid_evidence_count"
        ],
        "evidence_count": report["evidence_count"],
        "verified_fact_count": report[
            "verified_fact_count"
        ],
        "pending_input_count": report[
            "pending_input_count"
        ],
        "concept_generation_allowed": report[
            "concept_generation_allowed"
        ],
        "final_generation_allowed": report[
            "final_generation_allowed"
        ],
        "bb36_unlock_allowed": report[
            "bb36_unlock_allowed"
        ],
        "next_gate": report["next_gate"],
        "outputs": {
            key: str(value)
            for key, value in sorted(paths.items())
        },
    }, ensure_ascii=False, indent=2))

    if temporary is not None:
        temporary.cleanup()

    if args.expect_external_evidence_hold:
        return 0 if expected_hold else 1
    return 0 if report["verified_inputs_gate_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
