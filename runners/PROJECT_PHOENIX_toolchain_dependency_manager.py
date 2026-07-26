"""Self-test runner for Phoenix Toolchain & Dependency Manager."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(_REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT))

from phoenix.toolchain import ToolchainDependencyManager


def main() -> int:
    manager = ToolchainDependencyManager()
    report = manager.scan()

    with tempfile.TemporaryDirectory() as tmp:
        report_path = manager.export_report(
            report,
            Path(tmp) / "phoenix_toolchain_report.json",
        )
        result = {
            "status": "PASSED",
            "manager": "Phoenix Toolchain & Dependency Manager",
            "version": manager.VERSION,
            "dependency_count": len(report.results),
            "required_ready": report.required_ready,
            "missing_required": [
                item.name for item in report.missing_required
            ],
            "report_created": report_path.is_file(),
            "fingerprint_sha256": manager.fingerprint(report),
        }
        print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
