#!/usr/bin/env python
"""CLI for Project Phoenix Generated Input Validation List v1.0."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from phoenix.autonomy.generated_input_validation_list_v1_0 import (
    ValidationListError,
    write_validation_list,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Generated-input JSON file")
    parser.add_argument("--output", required=True, help="Validation-list JSON output")
    parser.add_argument("--project-id")
    parser.add_argument("--package-id")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.is_file():
        print(f"INPUT_NOT_FOUND={input_path}", file=sys.stderr)
        return 2

    try:
        payload = json.loads(input_path.read_text(encoding="utf-8-sig"))
        result = write_validation_list(
            args.output,
            payload,
            project_id=args.project_id,
            package_id=args.package_id,
        )
    except (json.JSONDecodeError, ValidationListError, OSError) as exc:
        print(f"VALIDATION_LIST_ERROR={exc}", file=sys.stderr)
        return 3

    print("GENERATED_INPUT_VALIDATION_LIST=PASS")
    print(f"OUTPUT={Path(args.output)}")
    print(f"TOTAL_ITEMS={result['summary']['total_items']}")
    print(f"STATUS={result['status']}")
    print(f"SCHEMA_VALIDATION_BACKEND={result['schema_validation_backend']}")
    print("PRODUCTION_RELEASE=LOCKED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
