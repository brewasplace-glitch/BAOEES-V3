#!/usr/bin/env python3
"""Project Phoenix digital_twin Generic Session Adapter v1.0."""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from phoenix.autonomy.session_adapters import run_adapter

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-file", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expect-session-adapted", action="store_true")
    args = parser.parse_args()
    return run_adapter(
        "digital_twin",
        REPO,
        args.session_file,
        args.workspace,
        args.output_dir,
    )

if __name__ == "__main__":
    raise SystemExit(main())
