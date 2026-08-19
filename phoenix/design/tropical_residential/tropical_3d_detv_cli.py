from __future__ import annotations

import argparse
import json
from pathlib import Path

from .tropical_3d_detv_pipeline import generate_tropical_real_3d_detv_package


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Phoenix Tropical Residential Real 3D + DE TV Presentation Pipeline v1.0"
    )
    ap.add_argument("--input", required=True)
    ap.add_argument("--runtime-root", required=True)
    ap.add_argument("--quick-smoke", action="store_true")
    ns = ap.parse_args()

    project = json.loads(Path(ns.input).read_text(encoding="utf-8"))
    summary = generate_tropical_real_3d_detv_package(
        project,
        Path(ns.runtime_root),
        quick=ns.quick_smoke,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
