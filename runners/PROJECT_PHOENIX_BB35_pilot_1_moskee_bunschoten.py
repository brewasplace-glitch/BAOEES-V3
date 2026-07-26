"""Run the real-project BB35 Pilot 1 baseline assessment."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phoenix.bb35_pilots.moskee_bunschoten import (
    MoskeeBunschotenPilotEngine,
    MoskeeBunschotenPilotExporter,
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--expect-baseline-hold",
        action="store_true",
    )
    args = parser.parse_args(argv)

    config_path = (
        ROOT / "configs/projects/"
        "moskee_bunschoten_bb35_pilot_1.json"
    )
    evidence_root = (
        ROOT / "inputs/pilots/moskee_bunschoten/source_evidence"
    )
    manifest_path = (
        ROOT / "inputs/pilots/moskee_bunschoten/"
        "evidence_manifest.json"
    )

    config = json.loads(config_path.read_text(encoding="utf-8"))
    evidence_manifest = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )

    report = MoskeeBunschotenPilotEngine().evaluate(
        config=config,
        evidence_manifest=evidence_manifest,
        evidence_root=evidence_root,
    )

    temporary = None
    if args.output_dir is None:
        temporary = tempfile.TemporaryDirectory()
        output_dir = Path(temporary.name)
    else:
        output_dir = args.output_dir

    paths = MoskeeBunschotenPilotExporter().export_all(
        report,
        output_dir,
    )

    expected_hold = (
        report["status"] == "BLOCKED_PENDING_STRATEGIC_DECISION"
        and report["source_evidence_count"]
        == report["source_evidence_valid_count"]
        and report["pilot_started"]
        and not report["pilot_completed"]
        and not report["bb36_unlock_allowed"]
    )

    result = {
        "status": "PASSED" if expected_hold else "FAILED",
        "pilot_id": report["pilot_id"],
        "project_id": report["project_id"],
        "pilot_status": report["status"],
        "real_source_evidence_valid": (
            report["source_evidence_count"]
            == report["source_evidence_valid_count"]
        ),
        "source_evidence_count": report[
            "source_evidence_count"
        ],
        "blocking_issue_count": report[
            "blocking_issue_count"
        ],
        "unresolved_strategic_decision_count": report[
            "unresolved_strategic_decision_count"
        ],
        "ready_deliverable_count": report[
            "ready_deliverable_count"
        ],
        "commercial_deliverable_count": report[
            "commercial_deliverable_count"
        ],
        "bb36_unlock_allowed": report[
            "bb36_unlock_allowed"
        ],
        "next_gate": report["next_gate"],
        "outputs": {
            key: str(value)
            for key, value in sorted(paths.items())
        },
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if temporary is not None:
        temporary.cleanup()

    if args.expect_baseline_hold:
        return 0 if expected_hold else 1
    return 0 if report["status"].startswith("READY_") else 2


if __name__ == "__main__":
    raise SystemExit(main())
