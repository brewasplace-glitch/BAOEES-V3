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

    qgis = report.get("engines", {}).get("qgis", {})
    if acceptance.get("status") != "ACCEPTED":
        raise RuntimeError("QGIS acceptance evidence is not ACCEPTED")
    if acceptance.get("simulated") is not False:
        raise RuntimeError("QGIS acceptance evidence is simulated")
    if acceptance.get("acceptance_basis") != "REAL_VALID_GEOPACKAGE_ARTIFACT":
        raise RuntimeError("QGIS acceptance basis is not a real GeoPackage artifact")
    if not str(acceptance.get("detected_version", "")).startswith("3.44."):
        raise RuntimeError("QGIS acceptance version is not 3.44 LTR")
    if not qgis.get("available"):
        raise RuntimeError(f"Phoenix still reports QGIS unavailable: {qgis}")

    executable = str(qgis.get("executable") or qgis.get("path") or "")
    if "qgis_process-qgis-ltr.bat" not in executable.lower():
        raise RuntimeError(f"Unexpected QGIS launcher: {executable}")

    notes = " ".join(str(x) for x in qgis.get("notes", []))
    if "real accepted GeoPackage evidence" not in notes:
        raise RuntimeError(
            "Detector report does not record the evidence-based availability basis"
        )

    print("QGIS EVIDENCE-BASED AVAILABILITY: VERIFIED")
    print(json.dumps(qgis, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
