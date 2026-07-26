import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from phoenix.release_framework import ReleaseManifestLoader,PhoenixReleaseFramework

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--output",type=Path); args=ap.parse_args()
    m=ReleaseManifestLoader().load_file(ROOT/"configs/phoenix/releases/bb18_release_framework_v1_0.json")
    f=PhoenixReleaseFramework(); plan=f.build_plan(ROOT,m)
    if args.output: f.rollback_journal(m,"SELFTEST-BASE",args.output)
    result={"status":"PASSED" if plan["ready"] else "FAILED","build_block":"BB18",
            "version":"1.0.0",**plan}
    print(json.dumps(result,indent=2)); return 0 if plan["ready"] else 1
if __name__=="__main__": raise SystemExit(main())
