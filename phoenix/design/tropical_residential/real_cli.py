from __future__ import annotations

import argparse
import json
from pathlib import Path

from .real_pipeline import generate_real_spatial_ifc_package


def main() -> int:
    ap=argparse.ArgumentParser(description="Phoenix Tropical Residential Real Spatial Layout + Authoritative IFC v1.0")
    ap.add_argument("--input",required=True)
    ap.add_argument("--output",required=True)
    ap.add_argument("--run-freecad-if-available",action="store_true")
    ap.add_argument("--run-blender-if-available",action="store_true")
    ns=ap.parse_args()
    project=json.loads(Path(ns.input).read_text(encoding="utf-8"))
    summary=generate_real_spatial_ifc_package(
        project,Path(ns.output),
        run_freecad_if_available=ns.run_freecad_if_available,
        run_blender_if_available=ns.run_blender_if_available,
    )
    print(json.dumps(summary,indent=2,ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
