from __future__ import annotations
import argparse, json
from pathlib import Path
from .manager import PhoenixUpdateManager
def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--manifest", required=True); p.add_argument("--plan-output", required=True); a=p.parse_args()
    m=PhoenixUpdateManager(); plan=m.create_plan(m.load_manifest(Path(a.manifest)))
    out=Path(a.plan_output); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(plan.to_dict(), indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps(plan.to_dict(), indent=2, sort_keys=True)); return 0
if __name__ == "__main__": raise SystemExit(main())
