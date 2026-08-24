#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path

from phoenix.autonomy.package_e_c05_docx_review_bridge_v1_0 import (
    ReviewBridgeError,
    ingest_review_docx,
    prepare_package_e_review,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare")
    prepare.add_argument("--repo", default=r"C:\PROJECT-PHOENIX")
    prepare.add_argument("--project-id", default="PHOENIX-PAT-001")
    prepare.add_argument("--output-dir", required=True)

    ingest = sub.add_parser("ingest")
    ingest.add_argument("--review-docx", required=True)
    ingest.add_argument("--validation-json", required=True)
    ingest.add_argument("--output-json", required=True)
    ingest.add_argument("--evidence-dir")

    args = parser.parse_args()

    try:
        if args.command == "prepare":
            result = prepare_package_e_review(
                args.repo,
                args.project_id,
                args.output_dir,
            )
            print("PACKAGE_E_C05_DOCX_REVIEW_PREP=PASS")
            for key, value in result.items():
                print(f"{key.upper()}={value}")
            print("NEXT_ACTION=REVIEWER_VALIDATES_OR_CORRECTS_DOCX")
            return 0

        result = ingest_review_docx(
            args.review_docx,
            args.validation_json,
            args.output_json,
            args.evidence_dir,
        )
        print("PACKAGE_E_C05_DOCX_REVIEW_INGEST=PASS")
        print(
            "READY_FOR_EXISTING_PACKAGE_E_VALIDATION="
            + ("YES" if result["ready_for_existing_package_e_validation"] else "NO")
        )
        print(
            "UNRESOLVED_REQUIRED_FIELDS="
            + ",".join(result["unresolved_required_review_fields"])
        )
        print(f"OUTPUT_JSON={Path(args.output_json)}")
        return 0
    except (ReviewBridgeError, OSError, ValueError) as exc:
        print(f"PACKAGE_E_C05_DOCX_REVIEW_ERROR={exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
