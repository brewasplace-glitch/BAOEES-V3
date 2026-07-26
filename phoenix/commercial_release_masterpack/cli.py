"""CLI for BB31-BB36 framework status export."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .exporters import CommercialReleaseMasterpackExporter


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    report = json.loads(args.report.read_text(encoding="utf-8"))
    paths = CommercialReleaseMasterpackExporter().export_all(
        report,
        args.output_dir,
    )
    print(json.dumps({key: str(value) for key, value in paths.items()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
