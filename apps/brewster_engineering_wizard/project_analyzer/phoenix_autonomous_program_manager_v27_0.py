from __future__ import annotations
import argparse, json, sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ENGINE_NAME = "Phoenix Autonomous Program Manager"
ENGINE_VERSION = "v27.0"

def find_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("PROJECT-PHOENIX root niet gevonden.")

ROOT = find_root()
POLICY_PATH = ROOT / "configs/phoenix/program_manager_policy_v27_0.json"
REGISTRY_PATH = ROOT / "configs/phoenix/program_portfolio_registry_v27_0.json"
OUTPUT_DIR = ROOT / "outputs/runtime/v27_0"
PROGRAM_DIR = ROOT / "outputs/program/v27_0"

class PhoenixAutonomousProgramManager:
    def __init__(self) -> None:
        self.policy = self._read_json(POLICY_PATH)
        self.registry = self._read_json(REGISTRY_PATH)

    def self_test(self) -> Dict[str, Any]:
        checks = {
            "policy_exists": POLICY_PATH.is_file(),
            "registry_exists": REGISTRY_PATH.is_file(),
            "python_supported": sys.version_info >= (3, 10),
            "portfolio_registered": bool(self.registry.get("programs")),
            "executive_controller_exists": (
                ROOT / "apps/brewster_engineering_wizard/project_analyzer/phoenix_executive_controller_v26_0.py"
            ).is_file(),
        }
        return self._write_runtime("program_manager_self_test_v27_0.json", {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "checks": checks,
            "status": "PASS" if all(checks.values()) else "FAIL",
        })

    def validate(self, program_id: str) -> Dict[str, Any]:
        errors: List[str] = []
        programs = self.registry.get("programs", {})
        if program_id not in programs:
            errors.append(f"Onbekend programma: {program_id}")
        else:
            seen = set()
            for project in programs[program_id].get("projects", []):
                project_id = project.get("project_id")
                if not project_id:
                    errors.append("Project zonder project_id.")
                    continue
                if project_id in seen:
                    errors.append(f"Dubbel project_id: {project_id}")
                seen.add(project_id)
                if not project.get("workflow_id"):
                    errors.append(f"Workflow ontbreekt voor {project_id}")
                if project.get("priority", 0) < 1:
                    errors.append(f"Ongeldige prioriteit voor {project_id}")
        return self._write_runtime("program_manager_validation_v27_0.json", {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "program_id": program_id,
            "errors": errors,
            "status": "PASS" if not errors else "FAIL",
        })

    def assess(self, program_id: str) -> Dict[str, Any]:
        validation = self.validate(program_id)
        if validation["status"] != "PASS":
            return self._write_runtime("program_manager_assessment_v27_0.json", {
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "program_id": program_id,
                "status": "BLOCKED_INVALID_PROGRAM",
            })
        rows = []
        for project in self.registry["programs"][program_id]["projects"]:
            score = (
                project["priority"] * self.policy["priority_weight"]
                + project.get("risk_score", 0) * self.policy["risk_weight"]
                + (100 - project.get("progress_percent", 0)) * self.policy["remaining_work_weight"]
            )
            rows.append({
                "project_id": project["project_id"],
                "workflow_id": project["workflow_id"],
                "priority": project["priority"],
                "risk_score": project.get("risk_score", 0),
                "progress_percent": project.get("progress_percent", 0),
                "program_score": round(score, 2),
                "status": project.get("status", "PLANNED"),
            })
        rows.sort(key=lambda item: item["program_score"], reverse=True)
        return self._write_program("program_assessment_v27_0.json", {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "program_id": program_id,
            "projects": rows,
            "status": "PASS",
        })

    def plan(self, program_id: str) -> Dict[str, Any]:
        assessment = self.assess(program_id)
        if assessment["status"] != "PASS":
            return assessment
        steps = []
        for sequence, project in enumerate(assessment["projects"], start=1):
            steps.append({
                "sequence": sequence,
                "project_id": project["project_id"],
                "workflow_id": project["workflow_id"],
                "program_score": project["program_score"],
                "requires_go": True,
                "execution_mode": "DRY_RUN",
                "status": "PLANNED",
            })
        return self._write_program("program_plan_v27_0.json", {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "program_id": program_id,
            "steps": steps,
            "automatic_execution": False,
            "status": "PASS",
        })

    def summary(self, program_id: str) -> Dict[str, Any]:
        assessment = self.assess(program_id)
        if assessment["status"] != "PASS":
            return assessment
        projects = assessment["projects"]
        count = len(projects)
        avg_progress = round(sum(x["progress_percent"] for x in projects) / count, 2) if count else 0
        return self._write_runtime("program_manager_summary_v27_0.json", {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "program_id": program_id,
            "project_count": count,
            "average_progress_percent": avg_progress,
            "highest_risk_project": max(projects, key=lambda x: x["risk_score"]) if projects else None,
            "recommended_next_project": projects[0] if projects else None,
            "safe_to_execute_without_go": False,
            "status": "PASS",
        })

    def _read_json(self, path: Path) -> Dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8-sig"))

    def _write_runtime(self, filename: str, data: Dict[str, Any]) -> Dict[str, Any]:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        data["generated_at"] = datetime.now().isoformat(timespec="seconds")
        path = OUTPUT_DIR / filename
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8-sig")
        data["output_path"] = str(path)
        return data

    def _write_program(self, filename: str, data: Dict[str, Any]) -> Dict[str, Any]:
        PROGRAM_DIR.mkdir(parents=True, exist_ok=True)
        data["generated_at"] = datetime.now().isoformat(timespec="seconds")
        path = PROGRAM_DIR / filename
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8-sig")
        data["output_path"] = str(path)
        return data

def main() -> None:
    parser = argparse.ArgumentParser(description=f"{ENGINE_NAME} {ENGINE_VERSION}")
    parser.add_argument("command", choices=["self-test", "validate", "assess", "plan", "summary"])
    parser.add_argument("--program-id", default="project-phoenix-core-program")
    args = parser.parse_args()
    engine = PhoenixAutonomousProgramManager()
    if args.command == "self-test":
        result = engine.self_test()
    elif args.command == "validate":
        result = engine.validate(args.program_id)
    elif args.command == "assess":
        result = engine.assess(args.program_id)
    elif args.command == "plan":
        result = engine.plan(args.program_id)
    else:
        result = engine.summary(args.program_id)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    if result.get("status") in {"FAIL", "BLOCKED_INVALID_PROGRAM"}:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
