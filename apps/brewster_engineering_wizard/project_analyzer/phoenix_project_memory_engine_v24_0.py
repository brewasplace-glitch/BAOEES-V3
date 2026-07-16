from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ENGINE_NAME = "Phoenix Autonomous Project Memory Engine"
ENGINE_VERSION = "v24.0"


def find_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("PROJECT-PHOENIX root niet gevonden.")


ROOT = find_root()
POLICY_PATH = ROOT / "configs/phoenix/project_memory_policy_v24_0.json"
SCHEMA_PATH = ROOT / "configs/phoenix/project_memory_schema_v24_0.json"
RUNTIME_ROOT = ROOT / "outputs/runtime"
MEMORY_DIR = ROOT / "outputs/memory/v24_0"
RUNTIME_DIR = ROOT / "outputs/runtime/v24_0"


class PhoenixProjectMemoryEngine:
    def __init__(self) -> None:
        self.policy = self._read_json(POLICY_PATH)
        self.schema = self._read_json(SCHEMA_PATH)

    def self_test(self) -> Dict[str, Any]:
        checks = {
            "policy_exists": POLICY_PATH.is_file(),
            "schema_exists": SCHEMA_PATH.is_file(),
            "runtime_root_exists": RUNTIME_ROOT.exists(),
            "python_supported": sys.version_info >= (3, 10),
            "memory_writable": self._writable(MEMORY_DIR),
        }
        return self._write_runtime(
            "project_memory_self_test_v24_0.json",
            {
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "checks": checks,
                "status": "PASS" if all(checks.values()) else "FAIL",
            },
        )

    def build_snapshot(self, project_id: str) -> Dict[str, Any]:
        records = self._collect_runtime_records()
        status_counts = Counter(item["status"] for item in records)
        engine_counts = Counter(item["engine"] for item in records)

        snapshot = {
            "schema_version": self.schema["schema_version"],
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "project_id": project_id,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "runtime_record_count": len(records),
            "status_counts": dict(status_counts),
            "engine_counts": dict(engine_counts),
            "records": records,
            "fingerprint": self._fingerprint(records),
            "status": "PASS",
        }
        return self._write_memory(
            f"{project_id}_memory_snapshot_v24_0.json",
            snapshot,
        )

    def lessons(self, project_id: str) -> Dict[str, Any]:
        snapshot_path = MEMORY_DIR / f"{project_id}_memory_snapshot_v24_0.json"
        snapshot = (
            self._read_json(snapshot_path)
            if snapshot_path.exists()
            else self.build_snapshot(project_id)
        )

        lessons: List[Dict[str, Any]] = []
        status_counts = snapshot.get("status_counts", {})

        if status_counts.get("PASS", 0) > 0:
            lessons.append({
                "category": "STABILITY",
                "message": "Behoud succesvolle test-, GO- en Git-gates als projectbaseline.",
                "confidence": "HIGH",
            })

        blocked = sum(
            count
            for status, count in status_counts.items()
            if str(status).startswith("BLOCKED")
        )
        if blocked > 0:
            lessons.append({
                "category": "PREFLIGHT",
                "message": "Gebruik eerdere blokkades om preflight-controles en foutmeldingen te verfijnen.",
                "confidence": "MEDIUM",
            })

        failures = sum(
            count
            for status, count in status_counts.items()
            if status in {"FAIL", "FAILED", "FAILED_REQUIRED_TASK", "FAILED_REQUIRED_AGENT"}
        )
        if failures > 0:
            lessons.append({
                "category": "RECOVERY",
                "message": "Koppel terugkerende fouten aan supervisor-, checkpoint- en recoverystrategieën.",
                "confidence": "MEDIUM",
            })

        if not lessons:
            lessons.append({
                "category": "DATA_QUALITY",
                "message": "Verzamel meer runtime-evidence voordat structurele lessen worden toegepast.",
                "confidence": "LOW",
            })

        result = {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "project_id": project_id,
            "snapshot_fingerprint": snapshot.get("fingerprint"),
            "lessons": lessons,
            "automatic_source_changes": False,
            "automatic_commit_push": False,
            "status": "PASS",
        }
        return self._write_memory(
            f"{project_id}_lessons_learned_v24_0.json",
            result,
        )

    def compare(self, left_project_id: str, right_project_id: str) -> Dict[str, Any]:
        left = self._load_or_build(left_project_id)
        right = self._load_or_build(right_project_id)

        left_engines = set(left.get("engine_counts", {}))
        right_engines = set(right.get("engine_counts", {}))

        result = {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "left_project_id": left_project_id,
            "right_project_id": right_project_id,
            "shared_engines": sorted(left_engines & right_engines),
            "left_only_engines": sorted(left_engines - right_engines),
            "right_only_engines": sorted(right_engines - left_engines),
            "same_fingerprint": left.get("fingerprint") == right.get("fingerprint"),
            "status": "PASS",
        }
        return self._write_runtime(
            "project_memory_comparison_v24_0.json",
            result,
        )

    def recommend(self, project_id: str) -> Dict[str, Any]:
        lessons = self.lessons(project_id)
        recommendations = []

        for index, lesson in enumerate(lessons["lessons"], start=1):
            recommendations.append({
                "recommendation_id": f"MEM-{index:03d}",
                "category": lesson["category"],
                "message": lesson["message"],
                "confidence": lesson["confidence"],
                "mode": "PROPOSAL_ONLY",
                "requires_go": True,
            })

        result = {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "project_id": project_id,
            "recommendations": recommendations,
            "automatic_execution": False,
            "automatic_source_changes": False,
            "status": "PASS",
        }
        return self._write_runtime(
            "project_memory_recommendations_v24_0.json",
            result,
        )

    def _collect_runtime_records(self) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        for path in sorted(RUNTIME_ROOT.rglob("*.json")):
            if "v24_0" in path.parts:
                continue
            try:
                data = self._read_json(path)
            except Exception:
                continue

            records.append({
                "path": path.relative_to(ROOT).as_posix(),
                "engine": data.get("engine", "UNKNOWN"),
                "version": data.get("version", "UNKNOWN"),
                "status": data.get("status", "UNKNOWN"),
                "generated_at": data.get("generated_at"),
            })
        return records

    def _load_or_build(self, project_id: str) -> Dict[str, Any]:
        path = MEMORY_DIR / f"{project_id}_memory_snapshot_v24_0.json"
        return self._read_json(path) if path.exists() else self.build_snapshot(project_id)

    def _fingerprint(self, records: List[Dict[str, Any]]) -> str:
        payload = json.dumps(records, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def _read_json(self, path: Path) -> Dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8-sig"))

    def _write_memory(self, filename: str, data: Dict[str, Any]) -> Dict[str, Any]:
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        path = MEMORY_DIR / filename
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8-sig",
        )
        data["output_path"] = str(path)
        return data

    def _write_runtime(self, filename: str, data: Dict[str, Any]) -> Dict[str, Any]:
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        data["generated_at"] = datetime.now().isoformat(timespec="seconds")
        path = RUNTIME_DIR / filename
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8-sig",
        )
        data["output_path"] = str(path)
        return data

    def _writable(self, path: Path) -> bool:
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            return True
        except OSError:
            return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description=f"{ENGINE_NAME} {ENGINE_VERSION}"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("self-test")

    snapshot = sub.add_parser("snapshot")
    snapshot.add_argument("--project-id", default="project-phoenix")

    lessons = sub.add_parser("lessons")
    lessons.add_argument("--project-id", default="project-phoenix")

    compare = sub.add_parser("compare")
    compare.add_argument("--left-project-id", default="project-phoenix")
    compare.add_argument("--right-project-id", default="project-phoenix")

    recommend = sub.add_parser("recommend")
    recommend.add_argument("--project-id", default="project-phoenix")

    args = parser.parse_args()
    engine = PhoenixProjectMemoryEngine()

    if args.command == "self-test":
        result = engine.self_test()
    elif args.command == "snapshot":
        result = engine.build_snapshot(args.project_id)
    elif args.command == "lessons":
        result = engine.lessons(args.project_id)
    elif args.command == "compare":
        result = engine.compare(
            args.left_project_id,
            args.right_project_id,
        )
    else:
        result = engine.recommend(args.project_id)

    print(json.dumps(result, ensure_ascii=True, indent=2))
    if result.get("status") != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
