"""CLI for the Phoenix Runtime Orchestrator Engine."""

from __future__ import annotations

import argparse
from pathlib import Path

from .engine import RuntimeOrchestrator, TaskSpec


def _echo(context):
    context.emit("heartbeat", message="Phoenix runtime is active")
    return {"runtime_id": context.runtime_id, "task_id": context.task_id}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the Phoenix Runtime Orchestrator self-test."
    )
    parser.add_argument(
        "--output",
        default=(
            "outputs/runtime/bb8/"
            "runtime_orchestrator_self_test.json"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    orchestrator = RuntimeOrchestrator(max_workers=2)
    orchestrator.register_many(
        [
            TaskSpec("foundation", _echo, priority=10),
            TaskSpec(
                "integration",
                _echo,
                dependencies=("foundation",),
                priority=20,
            ),
        ]
    )
    snapshot = orchestrator.run()
    RuntimeOrchestrator.write_snapshot(
        snapshot,
        Path(args.output),
    )
    print(
        f"Phoenix Runtime Orchestrator self-test: "
        f"{snapshot.status.upper()}"
    )
    print(f"Evidence SHA-256: {snapshot.evidence_sha256}")
    return 0 if snapshot.status == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
