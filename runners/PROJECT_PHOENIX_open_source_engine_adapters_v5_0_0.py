from pathlib import Path
import argparse, json, sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phoenix.adapters.open_source.registry import write_detection_report
from phoenix.adapters.open_source.orchestrator import execute_job

def main() -> int:
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="command",required=True)
    d=sub.add_parser("detect")
    d.add_argument("--output",default="outputs/runtime/open_source_engines_v5_0_0/detection_report.json")
    r=sub.add_parser("run")
    r.add_argument("--job",required=True)
    r.add_argument("--dry-run",action="store_true")
    args=p.parse_args()
    if args.command=="detect":
        report=write_detection_report(Path(args.output))
        for key,value in report["engines"].items():
            print(f'{key}: {"AVAILABLE" if value["available"] else "NOT FOUND"}')
        print("REPORT:",Path(args.output).resolve())
        return 0
    envelope=execute_job(Path(args.job),dry_run=args.dry_run)
    print(json.dumps(envelope,indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
