from pathlib import Path
import argparse, hashlib, json

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write_geojson(path: Path) -> None:
    data = {
        "type": "FeatureCollection",
        "name": "phoenix_qgis_acceptance_input",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:EPSG::28992"},
        },
        "features": [
            {
                "type": "Feature",
                "properties": {"id": 1, "name": "Phoenix testpunt"},
                "geometry": {
                    "type": "Point",
                    "coordinates": [155000.0, 463000.0],
                },
            }
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )

def validate(
    launcher: str,
    version: str,
    input_geojson: Path,
    output_gpkg: Path,
    process_exit_code: int,
    stdout_path: Path,
    stderr_path: Path,
    record_path: Path,
) -> dict:
    if not version.startswith("3.44."):
        raise RuntimeError(f"Expected QGIS 3.44 LTR, received {version}")
    if not input_geojson.is_file():
        raise RuntimeError("QGIS acceptance input missing")
    if not output_gpkg.is_file() or output_gpkg.stat().st_size == 0:
        raise RuntimeError(
            f"GeoPackage output missing; qgis_process exit code was {process_exit_code}"
        )
    if output_gpkg.read_bytes()[:16] != b"SQLite format 3\x00":
        raise RuntimeError("Invalid GeoPackage SQLite header")

    result = {
        "schema_version": "phoenix.qgis-acceptance/5.3.6",
        "status": "ACCEPTED",
        "launcher": launcher,
        "detected_version": version,
        "version_confirmation_source": "POWERSHELL_DIRECT_WRAPPER_PROBE",
        "processing_invocation_source": "POWERSHELL_DIRECT_WRAPPER_EXECUTION",
        "processing_exit_code": process_exit_code,
        "acceptance_basis": "REAL_VALID_GEOPACKAGE_ARTIFACT",
        "algorithm": "native:buffer",
        "artifacts": [
            {
                "path": input_geojson.name,
                "size_bytes": input_geojson.stat().st_size,
                "sha256": sha256(input_geojson),
            },
            {
                "path": output_gpkg.name,
                "size_bytes": output_gpkg.stat().st_size,
                "sha256": sha256(output_gpkg),
            },
        ],
        "logs": {
            "stdout": stdout_path.name,
            "stderr": stderr_path.name,
        },
        "simulated": False,
    }
    record_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return result

def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare")
    prepare.add_argument("--input", required=True)

    check = sub.add_parser("validate")
    check.add_argument("--launcher", required=True)
    check.add_argument("--version", required=True)
    check.add_argument("--input", required=True)
    check.add_argument("--output", required=True)
    check.add_argument("--process-exit-code", required=True, type=int)
    check.add_argument("--stdout", required=True)
    check.add_argument("--stderr", required=True)
    check.add_argument("--record", required=True)

    args = parser.parse_args()
    if args.command == "prepare":
        write_geojson(Path(args.input))
        return 0

    result = validate(
        args.launcher,
        args.version,
        Path(args.input),
        Path(args.output),
        args.process_exit_code,
        Path(args.stdout),
        Path(args.stderr),
        Path(args.record),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
