from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


def project_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".git").exists():
            return parent
    raise RuntimeError("PROJECT-PHOENIX root niet gevonden.")


class PhoenixEngineIntelligenceTests(unittest.TestCase):
    def test_registry(self) -> None:
        root = project_root()
        data = json.loads((root / "configs" / "phoenix" / "capability_registry_v12_0.json").read_text(encoding="utf-8-sig"))
        self.assertEqual(data["registry_version"], "v12.0")
        self.assertGreaterEqual(len(data["engines"]), 3)

    def test_engine_import(self) -> None:
        root = project_root()
        path = root / "apps" / "brewster_engineering_wizard" / "project_analyzer" / "phoenix_engine_intelligence_v12_0.py"
        spec = importlib.util.spec_from_file_location("phoenix_engine_intelligence_v12_0", path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertTrue(hasattr(module, "PhoenixEngineDiscovery"))
        self.assertTrue(hasattr(module, "PhoenixCapabilityRegistry"))
        self.assertTrue(hasattr(module, "PhoenixIntelligentModuleSelector"))


if __name__ == "__main__":
    unittest.main()
