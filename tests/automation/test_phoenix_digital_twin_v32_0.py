from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


def project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").exists():
            return parent
    raise RuntimeError("PROJECT-PHOENIX root niet gevonden.")


def load_twin():
    path = project_root() / "phoenix/digital_twin/phoenix_digital_twin_v32_0.py"
    name = "phoenix_digital_twin_v32_0_test"
    spec = importlib.util.spec_from_file_location(name, path)

    if spec is None or spec.loader is None:
        raise RuntimeError("Digital Twin-module kon niet worden geladen.")

    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module

    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)

    return module


class PhoenixDigitalTwinTests(unittest.TestCase):
    def test_policy(self) -> None:
        data = json.loads(
            (
                project_root()
                / "configs/phoenix/digital_twin_policy_v32_0.json"
            ).read_text(encoding="utf-8-sig")
        )
        self.assertEqual(data["policy_version"], "v32.0")
        self.assertEqual(data["kernel_version"], "v31.1")
        self.assertTrue(data["require_change_log"])

    def test_schema(self) -> None:
        data = json.loads(
            (
                project_root()
                / "configs/phoenix/digital_twin_schema_v32_0.json"
            ).read_text(encoding="utf-8-sig")
        )
        self.assertIn("project", data["allowed_object_types"])
        self.assertIn("contains", data["allowed_relation_types"])

    def test_import(self) -> None:
        module = load_twin()
        self.assertTrue(hasattr(module, "PhoenixDigitalTwin"))

    def test_object_graph(self) -> None:
        module = load_twin()
        twin = module.PhoenixDigitalTwin()

        project = twin.create_object(
            "project",
            {"name": "Test"},
            "project-test",
        )
        building = twin.create_object(
            "building",
            {"name": "Gebouw"},
            "building-test",
        )
        twin.add_relation(
            project["object_id"],
            building["object_id"],
            "contains",
        )

        self.assertEqual(len(twin.objects), 2)
        self.assertEqual(len(twin.relations), 1)

    def test_versioning(self) -> None:
        module = load_twin()
        twin = module.PhoenixDigitalTwin()
        twin.create_object(
            "element",
            {"name": "Kolom"},
            "element-test",
        )
        updated = twin.update_object(
            "element-test",
            {"status": "VALIDATED"},
        )
        self.assertEqual(updated["revision"], 2)


if __name__ == "__main__":
    unittest.main()
