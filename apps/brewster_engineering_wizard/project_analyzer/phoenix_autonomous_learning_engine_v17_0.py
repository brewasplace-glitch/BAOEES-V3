from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

ENGINE_NAME = "Phoenix Autonomous Learning & Self-Optimization Engine"
ENGINE_VERSION = "v17.0"


def find_project_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("PROJECT-PHOENIX repository root niet gevonden.")


ROOT = find_project_root()
POLICY_PATH = ROOT / "configs" / "phoenix" / "autonomous_learning_policy_v17_0.json"
RUNTIME_ROOT = ROOT / "outputs" / "runtime"
OUTPUT_DIR = ROOT / "outputs" / "runtime" / "v17_0"
KNOWLEDGE_DIR = ROOT / "outputs" / "knowledge" / "v17_0"


class PhoenixAutonomousLearningEngine:
    def __init__(self) -> None:
        self.policy = self._read_json(POLICY_PATH)

    def self_test(self) -> Dict[str, Any]:
        checks = {
            "project_root_exists": ROOT.exists(),
            "policy_exists": POLICY_PATH.exists(),
            "runtime_root_exists": RUNTIME_ROOT.exists(),
            "output_writable": self._writable(OUTPUT_DIR),
            "knowledge_writable": self._writable(KNOWLEDGE_DIR),
            "python_version_supported": sys.version_info >= (3, 10),
        }
        result = {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "checks": checks,
            "status": "PASS" if all(checks.values()) else "FAIL",
        }
        return self._write_runtime("learning_self_test_v17_0.json", result)

    def scan(self) -> Dict[str, Any]:
        files = [
            path for path in RUNTIME_ROOT.rglob("*.json")
            if "v17_0" not in path.parts
        ]
        records: List[Dict[str, Any]] = []
        parse_errors: List[str] = []

        for path in sorted(files):
            try:
                data = self._read_json(path)
            except Exception as exc:
                parse_errors.append(f"{path}: {exc}")
                continue

            records.append({
                "path": path.relative_to(ROOT).as_posix(),
                "status": data.get("status", "UNKNOWN"),
                "engine": data.get("engine", "UNKNOWN"),
                "version": data.get("version", "UNKNOWN"),
                "mode": data.get("mode", "UNKNOWN"),
            })

        result = {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "record_count": len(records),
            "parse_error_count": len(parse_errors),
            "records": records,
            "parse_errors": parse_errors,
            "status": "PASS",
        }
        return self._write_runtime("learning_scan_v17_0.json", result)

    def learn(self) -> Dict[str, Any]:
        scan = self.scan()
        records = scan["records"]

        status_counts = Counter(item["status"] for item in records)
        engine_counts = Counter(item["engine"] for item in records)
        mode_counts = Counter(item["mode"] for item in records)

        total = len(records)
        passes = status_counts.get("PASS", 0)
        failures = sum(
            count for status, count in status_counts.items()
            if status in {"FAIL", "FAILED", "FAILED_REQUIRED_TASK", "FAILED_REQUIRED_ENGINE"}
        )
        blocked = sum(
            count for status, count in status_counts.items()
            if str(status).startswith("BLOCKED")
        )

        success_rate = round((passes / total) * 100, 2) if total else 0.0
        failure_rate = round((failures / total) * 100, 2) if total else 0.0
        blocked_rate = round((blocked / total) * 100, 2) if total else 0.0

        recommendations = self._recommendations(
            total=total,
            success_rate=success_rate,
            failure_rate=failure_rate,
            blocked_rate=blocked_rate,
            status_counts=status_counts,
        )

        knowledge = {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "dataset": {
                "records": total,
                "status_counts": dict(status_counts),
                "engine_counts": dict(engine_counts),
                "mode_counts": dict(mode_counts),
            },
            "metrics": {
                "success_rate_percent": success_rate,
                "failure_rate_percent": failure_rate,
                "blocked_rate_percent": blocked_rate,
                "confidence": self._confidence(total),
            },
            "recommendations": recommendations,
            "automatic_source_changes": False,
            "automatic_commit_push": False,
            "status": "PASS",
        }
        return self._write_knowledge("phoenix_learning_snapshot_v17_0.json", knowledge)

    def optimize(self) -> Dict[str, Any]:
        learning = self.learn()
        metrics = learning["metrics"]
        recommendations = learning["recommendations"]

        actions = []
        for index, recommendation in enumerate(recommendations, start=1):
            actions.append({
                "action_id": f"OPT-{index:03d}",
                "description": recommendation["message"],
                "priority": recommendation["priority"],
                "category": recommendation["category"],
                "mode": "PROPOSAL_ONLY",
                "requires_go": True,
                "status": "PROPOSED",
            })

        plan = {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "mode": "DRY_RUN",
            "baseline_metrics": metrics,
            "actions": actions,
            "automatic_execution": False,
            "automatic_source_changes": False,
            "automatic_commit_push": False,
            "status": "PASS",
        }
        return self._write_runtime("optimization_plan_v17_0.json", plan)

    def _recommendations(
        self,
        total: int,
        success_rate: float,
        failure_rate: float,
        blocked_rate: float,
        status_counts: Counter,
    ) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []

        if total < self.policy["minimum_records_for_reliable_learning"]:
            items.append({
                "category": "DATA_QUALITY",
                "priority": 10,
                "message": "Verzamel meer runtime-evidence voordat structurele optimalisaties worden toegepast.",
            })

        if failure_rate > self.policy["failure_rate_warning_percent"]:
            items.append({
                "category": "RELIABILITY",
                "priority": 20,
                "message": "Analyseer falende engines en voeg gerichte hersteltests toe.",
            })

        if blocked_rate > self.policy["blocked_rate_warning_percent"]:
            items.append({
                "category": "PREFLIGHT",
                "priority": 30,
                "message": "Optimaliseer preflight-regels en verbeter foutmeldingen voor geblokkeerde runs.",
            })

        if success_rate >= self.policy["success_rate_good_percent"] and total > 0:
            items.append({
                "category": "STABILITY",
                "priority": 40,
                "message": "Behoud de huidige veilige GO-, test- en Git-gates als stabiele baseline.",
            })

        if not items:
            items.append({
                "category": "GENERAL",
                "priority": 50,
                "message": "Geen urgente optimalisatie nodig; blijf evidence verzamelen.",
            })

        return sorted(items, key=lambda item: item["priority"])

    def _confidence(self, total: int) -> float:
        target = max(1, self.policy["minimum_records_for_reliable_learning"])
        return round(min(1.0, math.log1p(total) / math.log1p(target)), 3)

    def _read_json(self, path: Path) -> Dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8-sig"))

    def _write_runtime(self, filename: str, data: Dict[str, Any]) -> Dict[str, Any]:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        data["generated_at"] = datetime.now().isoformat(timespec="seconds")
        path = OUTPUT_DIR / filename
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8-sig")
        data["output_path"] = str(path)
        return data

    def _write_knowledge(self, filename: str, data: Dict[str, Any]) -> Dict[str, Any]:
        KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
        path = KNOWLEDGE_DIR / filename
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8-sig")
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
    parser = argparse.ArgumentParser(description=f"{ENGINE_NAME} {ENGINE_VERSION}")
    parser.add_argument("command", choices=["self-test", "scan", "learn", "optimize"])
    args = parser.parse_args()

    engine = PhoenixAutonomousLearningEngine()
    if args.command == "self-test":
        result = engine.self_test()
    elif args.command == "scan":
        result = engine.scan()
    elif args.command == "learn":
        result = engine.learn()
    else:
        result = engine.optimize()

    print(json.dumps(result, ensure_ascii=True, indent=2))
    if result.get("status") != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
