from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

ENGINE_NAME = "Phoenix Digital Twin"
ENGINE_VERSION = "v32.0"


def find_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("PROJECT-PHOENIX root niet gevonden.")


ROOT = find_root()
POLICY_PATH = ROOT / "configs/phoenix/digital_twin_policy_v32_0.json"
SCHEMA_PATH = ROOT / "configs/phoenix/digital_twin_schema_v32_0.json"
KERNEL_PATH = ROOT / "phoenix/kernel/phoenix_kernel_v31_1.py"
OUTPUT_DIR = ROOT / "outputs/runtime/v32_0"
TWIN_DIR = ROOT / "outputs/digital_twin/v32_0"


def load_kernel_module():
    name = "phoenix_kernel_v31_1_runtime"
    spec = importlib.util.spec_from_file_location(name, KERNEL_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Phoenix Kernel v31.1 kon niet worden geladen.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


class PhoenixDigitalTwin:
    def __init__(self) -> None:
        self.policy = self._read_json(POLICY_PATH)
        self.schema = self._read_json(SCHEMA_PATH)
        self.kernel = load_kernel_module()
        self.events = self.kernel.EventBus()
        self.objects: Dict[str, Dict[str, Any]] = {}
        self.relations: List[Dict[str, str]] = []
        self.changes: List[Dict[str, Any]] = []
        self.version = 0

    def self_test(self) -> Dict[str, Any]:
        checks = {
            "policy_exists": POLICY_PATH.is_file(),
            "schema_exists": SCHEMA_PATH.is_file(),
            "kernel_exists": KERNEL_PATH.is_file(),
            "kernel_loadable": self.kernel is not None,
            "python_supported": sys.version_info >= (3, 10),
        }
        return self._write_runtime(
            "digital_twin_self_test_v32_0.json",
            {
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "checks": checks,
                "status": "PASS" if all(checks.values()) else "FAIL",
            },
        )

    def create_object(
        self,
        object_type: str,
        attributes: Dict[str, Any],
        object_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if object_type not in self.schema["allowed_object_types"]:
            raise RuntimeError(f"Niet-toegestaan objecttype: {object_type}")

        oid = object_id or str(uuid.uuid4())
        if oid in self.objects:
            raise RuntimeError(f"Object bestaat al: {oid}")

        now = datetime.now().isoformat(timespec="seconds")
        record = {
            "object_id": oid,
            "object_type": object_type,
            "attributes": attributes,
            "created_at": now,
            "updated_at": now,
            "revision": 1,
        }
        self.objects[oid] = record
        self._record_change("CREATE", oid, {"after": record})
        self.events.publish("digital_twin.object.created", {"object_id": oid})
        return record

    def update_object(
        self,
        object_id: str,
        attributes: Dict[str, Any],
    ) -> Dict[str, Any]:
        if object_id not in self.objects:
            raise RuntimeError(f"Onbekend object: {object_id}")

        before = json.loads(json.dumps(self.objects[object_id]))
        self.objects[object_id]["attributes"].update(attributes)
        self.objects[object_id]["updated_at"] = datetime.now().isoformat(
            timespec="seconds"
        )
        self.objects[object_id]["revision"] += 1
        after = json.loads(json.dumps(self.objects[object_id]))
        self._record_change("UPDATE", object_id, {"before": before, "after": after})
        self.events.publish("digital_twin.object.updated", {"object_id": object_id})
        return after

    def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
    ) -> Dict[str, str]:
        if source_id not in self.objects or target_id not in self.objects:
            raise RuntimeError("Relatie verwijst naar onbekend object.")
        if relation_type not in self.schema["allowed_relation_types"]:
            raise RuntimeError(f"Niet-toegestaan relatietype: {relation_type}")

        relation = {
            "source_id": source_id,
            "target_id": target_id,
            "relation_type": relation_type,
        }
        if relation not in self.relations:
            self.relations.append(relation)
            self._record_change("RELATE", source_id, relation)
            self.events.publish("digital_twin.relation.created", relation)
        return relation

    def snapshot(self, project_id: str) -> Dict[str, Any]:
        self.version += 1
        snapshot = {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "project_id": project_id,
            "twin_version": self.version,
            "objects": list(self.objects.values()),
            "relations": self.relations,
            "changes": self.changes,
            "event_history": self.events.history,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        }
        snapshot["fingerprint"] = self._fingerprint(snapshot)
        snapshot["status"] = "PASS"

        path = TWIN_DIR / f"{project_id}_digital_twin_v32_0.json"
        TWIN_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2),
            encoding="utf-8-sig",
        )
        snapshot["output_path"] = str(path)
        return snapshot

    def integration_test(self) -> Dict[str, Any]:
        project = self.create_object(
            "project",
            {"name": "Project Phoenix", "status": "ACTIVE"},
            "project-phoenix",
        )
        building = self.create_object(
            "building",
            {"name": "Testgebouw", "discipline": "bouw"},
            "building-001",
        )
        self.add_relation(
            project["object_id"],
            building["object_id"],
            "contains",
        )
        updated = self.update_object(
            building["object_id"],
            {"status": "VALIDATED"},
        )
        snapshot = self.snapshot("project-phoenix")

        checks = {
            "object_creation": len(self.objects) == 2,
            "object_update": updated["revision"] == 2,
            "relation_creation": len(self.relations) == 1,
            "change_log": len(self.changes) == 4,
            "kernel_event_bus": len(self.events.history) == 4,
            "snapshot_written": Path(snapshot["output_path"]).is_file(),
            "fingerprint_present": bool(snapshot["fingerprint"]),
        }

        return self._write_runtime(
            "digital_twin_integration_test_v32_0.json",
            {
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "checks": checks,
                "status": "PASS" if all(checks.values()) else "FAIL",
            },
        )

    def summary(self) -> Dict[str, Any]:
        self_test = self.self_test()
        integration = self.integration_test()

        return self._write_runtime(
            "digital_twin_summary_v32_0.json",
            {
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "self_test_status": self_test["status"],
                "integration_status": integration["status"],
                "kernel_integration": "v31.1",
                "status": (
                    "PASS"
                    if self_test["status"] == "PASS"
                    and integration["status"] == "PASS"
                    else "FAIL"
                ),
            },
        )

    def _record_change(
        self,
        operation: str,
        object_id: str,
        details: Dict[str, Any],
    ) -> None:
        self.changes.append(
            {
                "sequence": len(self.changes) + 1,
                "operation": operation,
                "object_id": object_id,
                "details": details,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            }
        )

    def _fingerprint(self, payload: Dict[str, Any]) -> str:
        raw = json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
        ).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def _read_json(self, path: Path) -> Dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8-sig"))

    def _write_runtime(
        self,
        filename: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        data["generated_at"] = datetime.now().isoformat(timespec="seconds")
        path = OUTPUT_DIR / filename
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8-sig",
        )
        data["output_path"] = str(path)
        return data


def main() -> None:
    parser = argparse.ArgumentParser(
        description=f"{ENGINE_NAME} {ENGINE_VERSION}"
    )
    parser.add_argument(
        "command",
        choices=["self-test", "integration-test", "summary"],
    )
    args = parser.parse_args()
    twin = PhoenixDigitalTwin()

    if args.command == "self-test":
        result = twin.self_test()
    elif args.command == "integration-test":
        result = twin.integration_test()
    else:
        result = twin.summary()

    print(json.dumps(result, ensure_ascii=True, indent=2))
    if result.get("status") != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
