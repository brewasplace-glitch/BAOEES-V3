"""BB17 self-test runner."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phoenix.building_code import BuildingCodeEngine, CodeProfileRegistry


def model() -> dict:
    return {
        "schema_version":"phoenix.building-model/1.0",
        "project_id":"PHX-BB17-SELFTEST",
        "name":"BB17 self-test",
        "units":"SI",
        "levels":[{"id":"LVL-00","name":"Ground floor","elevation_m":0.0,"height_m":3.0,"metadata":{}}],
        "spaces":[{"id":"SPC-001","name":"Test space","level_id":"LVL-00","area_m2":20.0,"volume_m3":60.0,"usage":"self_test","metadata":{}}],
        "elements":[{"id":"ELM-SLAB-001","name":"Slab","category":"slab","level_id":"LVL-00","geometry":{"length_m":5.0,"width_m":4.0,"thickness_m":0.2},"material":{"name":"concrete"},"properties":{},"source_refs":[]}],
        "relationships":[{"type":"contains","source_id":"LVL-00","target_id":"SPC-001","metadata":{}}],
        "metadata":{"build_block":"BB17","version":"1.0.0"},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    profile_path = ROOT / "configs" / "phoenix" / "building_code_profiles" / "phoenix_building_model_integrity_v1_0.json"
    profile = CodeProfileRegistry().load_file(profile_path)
    engine = BuildingCodeEngine()
    report = engine.evaluate(model(), profile)
    compliant = report.is_compliant_for(profile.fail_severities)
    if args.output:
        engine.export_report(report, profile, args.output)
    result = {
        "status":"PASSED" if compliant else "FAILED",
        "build_block":"BB17",
        "version":"1.0.0",
        "profile_id":profile.id,
        "profile_status":profile.status,
        "compliant":compliant,
        "summary":report.summary,
        "model_fingerprint_sha256":report.model_fingerprint_sha256,
        "report_fingerprint_sha256":engine.fingerprint_report(report, profile),
        "report_created":bool(args.output and args.output.is_file()),
    }
    print(json.dumps(result, indent=2))
    return 0 if compliant else 1


if __name__ == "__main__":
    raise SystemExit(main())
