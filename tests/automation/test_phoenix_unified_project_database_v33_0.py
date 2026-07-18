from __future__ import annotations

import gc
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


def project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").exists():
            return parent
    raise RuntimeError("PROJECT-PHOENIX root niet gevonden.")


def load_database_module():
    path = project_root() / "phoenix/database/phoenix_unified_project_database_v33_0.py"
    name = "phoenix_unified_project_database_v33_0_test"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Databasemodule kon niet worden geladen.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


class PhoenixUnifiedProjectDatabaseTests(unittest.TestCase):
    def test_policy(self) -> None:
        data = json.loads(
            (project_root() / "configs/phoenix/unified_project_database_policy_v33_0.json")
            .read_text(encoding="utf-8-sig")
        )
        self.assertEqual(data["policy_version"], "v33.0")
        self.assertTrue(data["require_transactions"])
        self.assertTrue(data["require_version_history"])

    def test_import(self) -> None:
        module = load_database_module()
        self.assertTrue(hasattr(module, "PhoenixUnifiedProjectDatabase"))

    def test_project_revisioning_and_file_release(self) -> None:
        module = load_database_module()
        with tempfile.TemporaryDirectory(prefix="phoenix_v33_revision_") as temp_directory:
            path = Path(temp_directory) / "revision.sqlite3"
            with module.PhoenixUnifiedProjectDatabase(path) as database:
                database.upsert_project({"project_id": "test-project", "name": "Test", "status": "ACTIVE"})
                database.upsert_project({"project_id": "test-project", "name": "Test", "status": "VALIDATED"})
                project = database.get_project("test-project")
                history = database.project_history("test-project")
                self.assertEqual(project["revision"], 2)
                self.assertEqual(project["status"], "VALIDATED")
                self.assertEqual(len(history), 2)
            gc.collect()
            probe = path.with_suffix(".probe.sqlite3")
            path.replace(probe)
            probe.replace(path)

    def test_transaction_rollback_and_file_release(self) -> None:
        module = load_database_module()
        with tempfile.TemporaryDirectory(prefix="phoenix_v33_rollback_") as temp_directory:
            path = Path(temp_directory) / "rollback.sqlite3"
            with module.PhoenixUnifiedProjectDatabase(path) as database:
                with self.assertRaises(RuntimeError):
                    with database.transaction() as connection:
                        connection.execute(
                            """
                            INSERT INTO projects (
                                project_id, name, status, payload_json,
                                fingerprint, revision, created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            ("rollback-test", "Rollback", "ACTIVE", "{}", "hash", 1, "now", "now"),
                        )
                        raise RuntimeError("force rollback")
                with database.connection() as connection:
                    count = connection.execute(
                        "SELECT COUNT(*) FROM projects WHERE project_id = ?",
                        ("rollback-test",),
                    ).fetchone()[0]
                self.assertEqual(count, 0)
            gc.collect()
            path.unlink()
            self.assertFalse(path.exists())

    def test_repeated_integration(self) -> None:
        module = load_database_module()
        with tempfile.TemporaryDirectory(prefix="phoenix_v33_repeat_") as temp_directory:
            path = Path(temp_directory) / "repeat.sqlite3"
            with module.PhoenixUnifiedProjectDatabase(path) as database:
                first = database.integration_test()
                second = database.integration_test()
                third = database.integration_test()
                self.assertEqual(first["status"], "PASS")
                self.assertEqual(second["status"], "PASS")
                self.assertEqual(third["status"], "PASS")
            gc.collect()
            path.unlink()
            self.assertFalse(path.exists())

    def test_closed_engine_rejects_new_connections(self) -> None:
        module = load_database_module()
        with tempfile.TemporaryDirectory(prefix="phoenix_v33_closed_") as temp_directory:
            path = Path(temp_directory) / "closed.sqlite3"
            database = module.PhoenixUnifiedProjectDatabase(path)
            database.close()
            with self.assertRaises(RuntimeError):
                with database.connection():
                    pass
            gc.collect()
            path.unlink()
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
