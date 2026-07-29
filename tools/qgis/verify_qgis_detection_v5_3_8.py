from pathlib import Path
import argparse
import json

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    parser.add_argument("--expected-launcher", required=True)
    args = parser.parse_args()

    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    qgis = report.get("engines", {}).get("qgis", {})
    if not qgis.get("available"):
        raise RuntimeError(f"Phoenix detector still reports QGIS unavailable: {qgis}")

    executable = str(qgis.get("executable") or qgis.get("path") or "")
    if args.expected_launcher.lower() not in executable.lower():
        raise RuntimeError(
            f"Unexpected QGIS executable in detector report: {executable}"
        )

    print("PHOENIX QGIS DETECTION VERIFIED")
    print(json.dumps(qgis, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
