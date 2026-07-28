from __future__ import annotations
from dataclasses import asdict
from pathlib import Path
import json
from .engines import ADAPTERS, create_adapter

def detect_all() -> dict:
    detections = {}
    for engine_id in sorted(ADAPTERS):
        adapter = create_adapter(engine_id)
        detections[engine_id] = asdict(adapter.detect())
        detections[engine_id]["spec"] = asdict(adapter.spec)
    return {
        "schema_version": "phoenix.open-source-engine-registry/5.0.0",
        "policy": "ADAPT_EXISTING_ENGINE_DO_NOT_REIMPLEMENT",
        "engines": detections,
    }

def write_detection_report(path: Path) -> dict:
    report = detect_all()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return report
