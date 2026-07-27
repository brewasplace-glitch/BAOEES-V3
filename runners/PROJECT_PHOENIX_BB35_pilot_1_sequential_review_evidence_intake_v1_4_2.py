"""Run sequential BB35 review and evidence-intake validation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phoenix.bb35_pilots.moskee_bunschoten.sequential_review_evidence_intake import (
    SequentialReviewEvidenceIntakeValidator,
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=ROOT,
    )
    args = parser.parse_args(argv)

    result = SequentialReviewEvidenceIntakeValidator().validate(
        args.repository_root
    )

    passed = (
        result["status"]
        == "REVIEW_COMPLETE_EVIDENCE_INTAKE_PARTIALLY_SATISFIED"
        and result["valid_uploaded_evidence_count"] == 6
        and result["evidence_requests"]
        == {"closed": 1, "partial": 2, "open": 5}
        and result["remaining_blocking_input_count"] == 7
        and not result["final_generation_allowed"]
        and not result["bb36_unlock_allowed"]
    )

    print(json.dumps({
        **result,
        "execution_status": "PASSED" if passed else "FAILED",
    }, ensure_ascii=False, indent=2))

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
