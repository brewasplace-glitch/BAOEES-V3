from pathlib import Path
import argparse, json

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--report",required=True);p.add_argument("--acceptance",required=True)
    a=p.parse_args()
    report=json.loads(Path(a.report).read_text(encoding="utf-8"))
    evidence=json.loads(Path(a.acceptance).read_text(encoding="utf-8"))
    engine=report.get("engines",{}).get("opensees",{})
    if evidence.get("status")!="ACCEPTED" or evidence.get("simulated") is not False:
        raise RuntimeError("OpenSees acceptance invalid")
    if evidence.get("analysis_code")!=0:
        raise RuntimeError("OpenSees analysis code is not zero")
    if not engine.get("available"):
        raise RuntimeError(f"Phoenix reports OpenSees unavailable: {engine}")
    print("PHOENIX OPENSEES DETECTION: VERIFIED AVAILABLE")
    print(json.dumps(engine,indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
