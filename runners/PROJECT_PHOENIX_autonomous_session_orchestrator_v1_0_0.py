#!/usr/bin/env python3
"""Project Phoenix Autonomous Session Orchestrator v1.0."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from phoenix.autonomy.session_orchestrator import AutonomousProjectOrchestrator


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--session-file", type=Path, required=True)
    parser.add_argument("--expect-session-orchestrated", action="store_true")
    args = parser.parse_args()

    orchestrator = AutonomousProjectOrchestrator(REPO)
    return orchestrator.run_session(args.session_file, args.output_dir)


if __name__ == "__main__":
    raise SystemExit(main())
