from __future__ import annotations
import argparse, json, sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set

ENGINE_NAME = "Phoenix Autonomous AI Planning Engine"
ENGINE_VERSION = "v14.0"

def root() -> Path:
    p = Path.cwd().resolve()
    for c in [p, *p.parents]:
        if (c / ".git").exists():
            return c
    raise RuntimeError("PROJECT-PHOENIX root niet gevonden.")

ROOT = root()
POLICY = ROOT / "configs/phoenix/ai_planner_policy_v14_0.json"
TEMPLATES = ROOT / "configs/phoenix/ai_planner_templates_v14_0.json"
CAPS = ROOT / "configs/phoenix/capability_registry_v12_0.json"
OUT = ROOT / "outputs/runtime/v14_0"

class PlannerError(RuntimeError):
    pass

class Planner:
    def __init__(self):
        self.policy = self.read(POLICY)
        self.templates = self.read(TEMPLATES)
        self.capabilities = self.read(CAPS)

    def self_test(self) -> Dict[str, Any]:
        checks = {
            "policy_exists": POLICY.exists(),
            "templates_exist": TEMPLATES.exists(),
            "capability_registry_exists": CAPS.exists(),
            "python_supported": sys.version_info >= (3, 10),
            "templates_valid": bool(self.templates.get("templates")),
        }
        return self.save("self_test", {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "checks": checks,
            "status": "PASS" if all(checks.values()) else "FAIL",
        })

    def plan(self, project_id: str, objective: str, capabilities: List[str], constraints: List[str]) -> Dict[str, Any]:
        template = self.select_template(capabilities)
        ordered = self.resolve(template["tasks"])
        tasks = []
        for index, task in enumerate(ordered, start=1):
            item = dict(task)
            item["sequence"] = index
            item["status"] = "PLANNED"
            tasks.append(item)

        available = {
            capability
            for engine in self.capabilities.get("engines", [])
            for capability in engine.get("capabilities", [])
        }
        unresolved = sorted(set(capabilities) - available)

        return self.save("plan", {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "mode": "DRY_RUN",
            "project_id": project_id,
            "objective": objective,
            "constraints": constraints,
            "requested_capabilities": capabilities,
            "template_id": template["template_id"],
            "tasks": tasks,
            "unresolved_capabilities": unresolved,
            "ready": not unresolved,
            "status": "PASS" if not unresolved else "PARTIAL",
            "automatic_execution": False,
            "automatic_commit_push": False,
        })

    def validate(self, plan_path: Path) -> Dict[str, Any]:
        plan = self.read(plan_path)
        errors = []
        ids = [task["task_id"] for task in plan.get("tasks", [])]
        if len(ids) != len(set(ids)):
            errors.append("Dubbele task_id gevonden.")
        try:
            self.resolve(plan.get("tasks", []))
        except PlannerError as exc:
            errors.append(str(exc))
        return self.save("validation", {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "plan_path": str(plan_path),
            "errors": errors,
            "status": "PASS" if not errors else "FAIL",
        })

    def select_template(self, capabilities: List[str]) -> Dict[str, Any]:
        best = None
        best_score = -1
        for template in self.templates.get("templates", []):
            score = len(set(capabilities) & set(template.get("capabilities", [])))
            if score > best_score:
                best = template
                best_score = score
        if best is None:
            raise PlannerError("Geen planningtemplate beschikbaar.")
        return best

    def resolve(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        by_id = {task["task_id"]: task for task in tasks}
        visiting: Set[str] = set()
        visited: Set[str] = set()
        ordered: List[Dict[str, Any]] = []

        def visit(task_id: str) -> None:
            if task_id in visited:
                return
            if task_id in visiting:
                raise PlannerError(f"Circulaire taakafhankelijkheid: {task_id}")
            if task_id not in by_id:
                raise PlannerError(f"Onbekende task_id: {task_id}")
            visiting.add(task_id)
            for dep in by_id[task_id].get("dependencies", []):
                visit(dep)
            visiting.remove(task_id)
            visited.add(task_id)
            ordered.append(by_id[task_id])

        for task_id in by_id:
            visit(task_id)
        return ordered

    def read(self, path: Path) -> Dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8-sig"))

    def save(self, name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        OUT.mkdir(parents=True, exist_ok=True)
        data["generated_at"] = datetime.now().isoformat(timespec="seconds")
        path = OUT / f"ai_planner_{name}_v14_0.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8-sig")
        data["output_path"] = str(path)
        return data

def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")
    plan = sub.add_parser("plan")
    plan.add_argument("--project-id", default="phoenix-core-v14")
    plan.add_argument("--objective", required=True)
    plan.add_argument("--capability", action="append", required=True)
    plan.add_argument("--constraint", action="append", default=[])
    validate = sub.add_parser("validate")
    validate.add_argument("--plan-path", required=True)
    args = parser.parse_args()

    planner = Planner()
    if args.command == "self-test":
        result = planner.self_test()
    elif args.command == "plan":
        result = planner.plan(args.project_id, args.objective, args.capability, args.constraint)
    else:
        result = planner.validate(Path(args.plan_path))

    print(json.dumps(result, ensure_ascii=True, indent=2))
    if result.get("status") == "FAIL":
        raise SystemExit(1)

if __name__ == "__main__":
    main()
