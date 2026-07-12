from __future__ import annotations

import argparse
import ast
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ENGINE_NAME = "Phoenix Engine Intelligence"
ENGINE_VERSION = "v12.0"


def find_project_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("PROJECT-PHOENIX repository root niet gevonden.")


PROJECT_ROOT = find_project_root()
ENGINE_DIR = PROJECT_ROOT / "apps" / "brewster_engineering_wizard" / "project_analyzer"
REGISTRY_PATH = PROJECT_ROOT / "configs" / "phoenix" / "capability_registry_v12_0.json"
POLICY_PATH = PROJECT_ROOT / "configs" / "phoenix" / "engine_intelligence_policy_v12_0.json"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "runtime" / "v12_0"


class PhoenixEngineDiscovery:
    def __init__(self, registry: Dict[str, Any], policy: Dict[str, Any]) -> None:
        self.registry = registry
        self.policy = policy

    def discover(self) -> Dict[str, Any]:
        excluded = set(self.policy.get("excluded_filenames", []))
        engines: List[Dict[str, Any]] = []
        for path in sorted(ENGINE_DIR.glob("*.py")):
            if path.name in excluded or path.name.startswith("test_"):
                continue
            metadata = self._metadata(path)
            if not metadata["is_engine"]:
                continue
            metadata["relative_path"] = path.relative_to(PROJECT_ROOT).as_posix()
            metadata["capabilities"] = self._capabilities(path.name, metadata["engine_name"])
            engines.append(metadata)
        return {
            "component": "engine_discovery",
            "engine_count": len(engines),
            "engines": engines,
            "status": "PASS",
        }

    def _metadata(self, path: Path) -> Dict[str, Any]:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        except (SyntaxError, UnicodeError) as exc:
            return {"filename": path.name, "is_engine": False, "parse_error": str(exc)}

        values: Dict[str, str] = {}
        classes: List[str] = []
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in {"ENGINE_NAME", "ENGINE_VERSION"}:
                        try:
                            values[target.id] = ast.literal_eval(node.value)
                        except (ValueError, TypeError):
                            pass
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
        is_engine = bool(values.get("ENGINE_NAME")) or any(name.lower().startswith("phoenix") for name in classes)
        return {
            "filename": path.name,
            "engine_name": values.get("ENGINE_NAME", path.stem),
            "engine_version": values.get("ENGINE_VERSION", "unknown"),
            "classes": classes,
            "is_engine": is_engine,
        }

    def _capabilities(self, filename: str, engine_name: str) -> List[str]:
        result: List[str] = []
        for entry in self.registry.get("engines", []):
            if filename in entry.get("module_patterns", []) or engine_name in entry.get("engine_names", []):
                result.extend(entry.get("capabilities", []))
        return sorted(set(result))


class PhoenixCapabilityRegistry:
    def __init__(self, registry: Dict[str, Any]) -> None:
        self.registry = registry

    def validate(self) -> Dict[str, Any]:
        errors: List[str] = []
        ids = set()
        for entry in self.registry.get("engines", []):
            engine_id = str(entry.get("engine_id", "")).strip()
            if not engine_id:
                errors.append("Engine zonder engine_id.")
                continue
            if engine_id in ids:
                errors.append(f"Dubbele engine_id: {engine_id}")
            ids.add(engine_id)
            if not entry.get("module_patterns"):
                errors.append(f"Geen module_patterns voor {engine_id}.")
            if not entry.get("capabilities"):
                errors.append(f"Geen capabilities voor {engine_id}.")
        return {
            "component": "capability_registry",
            "engine_count": len(ids),
            "errors": errors,
            "status": "PASS" if not errors else "FAIL",
        }

    def resolve(self, capability: str) -> List[Dict[str, Any]]:
        matches = []
        for entry in self.registry.get("engines", []):
            if capability in entry.get("capabilities", []):
                matches.append({
                    "engine_id": entry["engine_id"],
                    "priority": entry.get("priority", 100),
                    "module_patterns": entry.get("module_patterns", []),
                })
        return sorted(matches, key=lambda item: (item["priority"], item["engine_id"]))


class PhoenixIntelligentModuleSelector:
    def __init__(self, registry: PhoenixCapabilityRegistry, discovery: Dict[str, Any]) -> None:
        self.registry = registry
        self.discovered = {item["filename"]: item for item in discovery.get("engines", [])}

    def select(self, capabilities: List[str]) -> Dict[str, Any]:
        selected: Dict[str, Dict[str, Any]] = {}
        unresolved: List[str] = []
        for capability in capabilities:
            candidates = []
            for match in self.registry.resolve(capability):
                discovered = None
                for pattern in match["module_patterns"]:
                    if pattern in self.discovered:
                        discovered = self.discovered[pattern]
                        break
                if discovered:
                    candidates.append((match["priority"], match["engine_id"], discovered))
            if not candidates:
                unresolved.append(capability)
                continue
            _, engine_id, discovered = sorted(candidates, key=lambda item: (item[0], item[1]))[0]
            selected.setdefault(engine_id, {
                "engine_id": engine_id,
                "module": discovered["relative_path"],
                "engine_name": discovered["engine_name"],
                "engine_version": discovered["engine_version"],
                "capabilities": [],
            })
            selected[engine_id]["capabilities"].append(capability)
        return {
            "component": "intelligent_module_selection",
            "mode": "DRY_RUN",
            "selected_engines": sorted(selected.values(), key=lambda item: item["engine_id"]),
            "unresolved_capabilities": unresolved,
            "ready": not unresolved,
            "status": "PASS" if not unresolved else "PARTIAL",
            "automatic_execution": False,
        }


class PhoenixEngineIntelligence:
    def __init__(self) -> None:
        self.registry_data = self._read_json(REGISTRY_PATH)
        self.policy = self._read_json(POLICY_PATH)
        self.discovery_service = PhoenixEngineDiscovery(self.registry_data, self.policy)
        self.registry = PhoenixCapabilityRegistry(self.registry_data)

    def self_test(self) -> Dict[str, Any]:
        checks = {
            "project_root_exists": PROJECT_ROOT.exists(),
            "engine_directory_exists": ENGINE_DIR.exists(),
            "registry_exists": REGISTRY_PATH.exists(),
            "policy_exists": POLICY_PATH.exists(),
            "python_version_supported": sys.version_info >= (3, 10),
        }
        return self._write("engine_intelligence_self_test_v12_0.json", {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "checks": checks,
            "status": "PASS" if all(checks.values()) else "FAIL",
        })

    def discover(self) -> Dict[str, Any]:
        return self._write("engine_discovery_v12_0.json", self.discovery_service.discover())

    def validate_registry(self) -> Dict[str, Any]:
        return self._write("capability_registry_validation_v12_0.json", self.registry.validate())

    def select(self, capabilities: List[str]) -> Dict[str, Any]:
        discovery = self.discovery_service.discover()
        selector = PhoenixIntelligentModuleSelector(self.registry, discovery)
        return self._write("module_selection_plan_v12_0.json", selector.select(capabilities))

    def _read_json(self, path: Path) -> Dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8-sig"))

    def _write(self, filename: str, data: Dict[str, Any]) -> Dict[str, Any]:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        data.setdefault("engine", ENGINE_NAME)
        data.setdefault("version", ENGINE_VERSION)
        data.setdefault("generated_at", datetime.now().isoformat(timespec="seconds"))
        path = OUTPUT_DIR / filename
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8-sig")
        data["report_path"] = str(path)
        return data


def main() -> None:
    parser = argparse.ArgumentParser(description=f"{ENGINE_NAME} {ENGINE_VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")
    sub.add_parser("discover")
    sub.add_parser("validate-registry")
    select = sub.add_parser("select")
    select.add_argument("--capability", action="append", required=True)
    args = parser.parse_args()

    engine = PhoenixEngineIntelligence()
    if args.command == "self-test":
        result = engine.self_test()
    elif args.command == "discover":
        result = engine.discover()
    elif args.command == "validate-registry":
        result = engine.validate_registry()
    else:
        result = engine.select(args.capability)

    print(json.dumps(result, ensure_ascii=True, indent=2))
    if result.get("status") == "FAIL":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
