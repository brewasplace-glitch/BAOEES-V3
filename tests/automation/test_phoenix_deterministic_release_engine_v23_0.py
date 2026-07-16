from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


def project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").exists():
            return parent
    raise RuntimeError("PROJECT-PHOENIX root niet gevonden.")


class DeterministicReleaseEngineTests(unittest.TestCase):
    def test_policy(self) -> None:
        data = json.loads(
            (
                project_root()
                / "configs/phoenix/deterministic_release_policy_v23_0.json"
            ).read_text(encoding="utf-8-sig")
        )
        self.assertEqual(data["policy_version"], "v23.0")
        self.assertTrue(data["write_all_runtime_reports_before_staging"])
        self.assertFalse(data["allow_post_commit_runtime_writes"])

    def test_import(self) -> None:
        path = (
            project_root()
            / "apps/brewster_engineering_wizard/project_analyzer"
            / "phoenix_deterministic_release_engine_v23_0.py"
        )
        spec = importlib.util.spec_from_file_location(
            "deterministic_release",
            path,
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertTrue(
            hasattr(module, "PhoenixDeterministicReleaseEngine")
        )


if __name__ == "__main__":
    unittest.main()
