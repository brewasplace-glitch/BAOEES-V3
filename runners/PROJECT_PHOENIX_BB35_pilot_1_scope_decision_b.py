"""Validate Moskee Bunschoten authoritative scope decision B."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phoenix.bb35_pilots.moskee_bunschoten.scope_decision_b import (
    MoskeeScopeDecisionBValidator,
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)

    config = json.loads(
        (
            ROOT
            / "configs/projects/"
            "moskee_bunschoten_bb35_pilot_1.json"
        ).read_text(encoding="utf-8")
    )
    decision = json.loads(
        (
            ROOT
            / "inputs/pilots/moskee_bunschoten/"
            "scope_decision_B_v1_1_0.json"
        ).read_text(encoding="utf-8")
    )

    result = MoskeeScopeDecisionBValidator().validate(
        config,
        decision,
    )

    if args.output_dir is not None:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = (
            args.output_dir / "scope_decision_B_validation.json"
        )
        output_path.write_text(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    else:
        output_path = None

    print(json.dumps({
        "status": (
            "PASSED"
            if (
                result["scope_decision_valid"]
                and result["pilot_status"]
                == "BLOCKED_PENDING_INPUTS"
                and not result["bb36_unlock_allowed"]
            )
            else "FAILED"
        ),
        "pilot_id": result["pilot_id"],
        "project_id": result["project_id"],
        "scope_decision": result["scope_decision"],
        "authoritative_dimensions_m": "7.00 x 10.00",
        "extension_storeys": 2,
        "extension_footprint_m2": 70.0,
        "gross_extension_area_m2": 140.0,
        "pilot_status": result["pilot_status"],
        "missing_blocking_input_count": (
            result["missing_blocking_input_count"]
        ),
        "bb36_unlock_allowed": result[
            "bb36_unlock_allowed"
        ],
        "output": str(output_path) if output_path else None,
    }, ensure_ascii=False, indent=2))

    passed = (
        result["scope_decision_valid"]
        and result["pilot_status"] == "BLOCKED_PENDING_INPUTS"
        and not result["bb36_unlock_allowed"]
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
