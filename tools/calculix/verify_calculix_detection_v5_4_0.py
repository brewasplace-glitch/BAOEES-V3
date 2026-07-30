from pathlib import Path
import argparse
import json

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    parser.add_argument("--acceptance", required=True)
    args = parser.parse_args()

    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    acceptance = json.loads(Path(args.acceptance).read_text(encoding="utf-8"))
    engine = report.get("engines", {}).get("calculix", {})

    if acceptance.get("status") != "ACCEPTED":
        raise RuntimeError("CalculiX acceptance is not ACCEPTED")
    if acceptance.get("simulated") is not False:
        raise RuntimeError("CalculiX acceptance is simulated")
    if acceptance.get("acceptance_basis") != "REAL_CCX_DAT_FRD_ARTIFACTS":
        raise RuntimeError("CalculiX acceptance basis is invalid")
    if not engine.get("available"):
        raise RuntimeError(f"Phoenix reports CalculiX unavailable: {engine}")

    executable = str(engine.get("executable") or engine.get("path") or "")
    if "ccx" not in executable.lower():
        raise RuntimeError(f"Unexpected CalculiX executable: {executable}")

    print("PHOENIX CALCULIX DETECTION: VERIFIED AVAILABLE")
    print(json.dumps(engine, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
