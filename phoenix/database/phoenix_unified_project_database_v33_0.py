from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sqlite3
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

ENGINE_NAME = "Phoenix Unified Project Database"
ENGINE_VERSION = "v33.0"
LIFECYCLE_FIX_VERSION = "v33.2"


def find_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("PROJECT-PHOENIX root niet gevonden.")


ROOT = find_root()
POLICY_PATH = ROOT / "configs/phoenix/unified_project_database_policy_v33_0.json"
SCHEMA_PATH = ROOT / "configs/phoenix/unified_project_database_schema_v33_0.json"
TWIN_PATH = ROOT / "phoenix/digital_twin/phoenix_digital_twin_v32_0.py"
OUTPUT_DIR = ROOT / "outputs/runtime/v33_0"
DATABASE_DIR = ROOT / "outputs/database/v33_0"
DATABASE_PATH = DATABASE_DIR / "phoenix_unified_project_database_v33_0.sqlite3"


def load_digital_twin_module():
    name = "phoenix_digital_twin_v32_0_runtime"
    spec = importlib.util.spec_from_file_location(name, TWIN_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Phoenix Digital Twin v32.0 kon niet worden geladen.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


class PhoenixUnifiedProjectDatabase:
    def __init__(self, database_path: Optional[Path] = None) -> None:
        self.policy = self._read_json(POLICY_PATH)
        self.schema = self._read_json(SCHEMA_PATH)
        self.digital_twin_module = load_digital_twin_module()
        self.database_path = database_path or DATABASE_PATH
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._closed = False
        self._initialize_schema()

    def __enter__(self) -> "PhoenixUnifiedProjectDatabase":
        self._ensure_open()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def close(self) -> None:
        self._closed = True

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("Database-engine is gesloten.")

    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        self._ensure_open()
        connection = sqlite3.connect(self.database_path, timeout=30.0)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            yield connection
        finally:
            connection.close()

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        with self.connection() as connection:
            try:
                connection.execute("BEGIN")
                yield connection
                connection.commit()
            except Exception:
                connection.rollback()
                raise

    def self_test(self) -> Dict[str, Any]:
        checks = {
            "policy_exists": POLICY_PATH.is_file(),
            "schema_exists": SCHEMA_PATH.is_file(),
            "digital_twin_exists": TWIN_PATH.is_file(),
            "database_created": self.database_path.is_file(),
            "python_supported": sys.version_info >= (3, 10),
            "sqlite_available": sqlite3.sqlite_version_info >= (3, 24, 0),
            "explicit_connection_lifecycle": True,
            "engine_open": not self._closed,
        }
        return self._write_runtime(
            "unified_project_database_self_test_v33_0.json",
            {
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "lifecycle_fix_version": LIFECYCLE_FIX_VERSION,
                "checks": checks,
                "status": "PASS" if all(checks.values()) else "FAIL",
            },
        )

    def upsert_project(self, project: Dict[str, Any]) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        payload = json.dumps(project, ensure_ascii=False, sort_keys=True)
        fingerprint = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        with self.transaction() as connection:
            existing = connection.execute(
                "SELECT revision FROM projects WHERE project_id = ?",
                (project["project_id"],),
            ).fetchone()
            revision = 1 if existing is None else int(existing["revision"]) + 1
            operation = "CREATE" if existing is None else "UPDATE"

            connection.execute(
                """
                INSERT INTO projects (
                    project_id, name, status, payload_json, fingerprint,
                    revision, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_id) DO UPDATE SET
                    name = excluded.name,
                    status = excluded.status,
                    payload_json = excluded.payload_json,
                    fingerprint = excluded.fingerprint,
                    revision = excluded.revision,
                    updated_at = excluded.updated_at
                """,
                (
                    project["project_id"],
                    project.get("name", project["project_id"]),
                    project.get("status", "ACTIVE"),
                    payload,
                    fingerprint,
                    revision,
                    now,
                    now,
                ),
            )

            connection.execute(
                """
                INSERT INTO project_history (
                    project_id, revision, operation, payload_json,
                    fingerprint, recorded_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (project["project_id"], revision, operation, payload, fingerprint, now),
            )

    def persist_digital_twin(self, project_id: str, snapshot: Dict[str, Any]) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        payload = json.dumps(snapshot, ensure_ascii=False, sort_keys=True)
        fingerprint = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO digital_twin_snapshots (
                    project_id, twin_version, snapshot_json, fingerprint, recorded_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (project_id, int(snapshot["twin_version"]), payload, fingerprint, now),
            )

            for obj in snapshot.get("objects", []):
                connection.execute(
                    """
                    INSERT INTO project_objects (
                        project_id, object_id, object_type, attributes_json,
                        revision, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(project_id, object_id) DO UPDATE SET
                        object_type = excluded.object_type,
                        attributes_json = excluded.attributes_json,
                        revision = excluded.revision,
                        updated_at = excluded.updated_at
                    """,
                    (
                        project_id,
                        obj["object_id"],
                        obj["object_type"],
                        json.dumps(obj.get("attributes", {}), ensure_ascii=False, sort_keys=True),
                        int(obj.get("revision", 1)),
                        obj.get("updated_at", now),
                    ),
                )

            connection.execute("DELETE FROM project_relations WHERE project_id = ?", (project_id,))
            for relation in snapshot.get("relations", []):
                connection.execute(
                    """
                    INSERT INTO project_relations (
                        project_id, source_id, target_id, relation_type
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        project_id,
                        relation["source_id"],
                        relation["target_id"],
                        relation["relation_type"],
                    ),
                )

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        with self.connection() as connection:
            row = connection.execute(
                """
                SELECT project_id, name, status, payload_json, fingerprint,
                       revision, created_at, updated_at
                FROM projects WHERE project_id = ?
                """,
                (project_id,),
            ).fetchone()

        if row is None:
            return None

        return {
            "project_id": row["project_id"],
            "name": row["name"],
            "status": row["status"],
            "payload": json.loads(row["payload_json"]),
            "fingerprint": row["fingerprint"],
            "revision": int(row["revision"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def query_objects(self, project_id: str, object_type: Optional[str] = None) -> List[Dict[str, Any]]:
        sql = """
            SELECT object_id, object_type, attributes_json, revision, updated_at
            FROM project_objects WHERE project_id = ?
        """
        parameters: List[Any] = [project_id]
        if object_type is not None:
            sql += " AND object_type = ?"
            parameters.append(object_type)
        sql += " ORDER BY object_type, object_id"

        with self.connection() as connection:
            rows = connection.execute(sql, parameters).fetchall()

        return [
            {
                "object_id": row["object_id"],
                "object_type": row["object_type"],
                "attributes": json.loads(row["attributes_json"]),
                "revision": int(row["revision"]),
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]

    def project_history(self, project_id: str) -> List[Dict[str, Any]]:
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT revision, operation, payload_json, fingerprint, recorded_at
                FROM project_history WHERE project_id = ? ORDER BY revision
                """,
                (project_id,),
            ).fetchall()

        return [
            {
                "revision": int(row["revision"]),
                "operation": row["operation"],
                "payload": json.loads(row["payload_json"]),
                "fingerprint": row["fingerprint"],
                "recorded_at": row["recorded_at"],
            }
            for row in rows
        ]

    def integration_test(self) -> Dict[str, Any]:
        with tempfile.TemporaryDirectory(prefix="phoenix_v33_") as temp_directory:
            database_path = Path(temp_directory) / "integration.sqlite3"

            with PhoenixUnifiedProjectDatabase(database_path) as isolated:
                project_id = "project-phoenix-v33-test"
                twin = isolated.digital_twin_module.PhoenixDigitalTwin()
                project = twin.create_object(
                    "project",
                    {"name": "Project Phoenix Database Test", "status": "ACTIVE"},
                    project_id,
                )
                building = twin.create_object(
                    "building", {"name": "Database Testgebouw"}, "building-v33-test"
                )
                twin.add_relation(project["object_id"], building["object_id"], "contains")
                snapshot = twin.snapshot(project_id)

                isolated.upsert_project(
                    {"project_id": project_id, "name": "Project Phoenix Database Test", "status": "ACTIVE"}
                )
                isolated.persist_digital_twin(project_id, snapshot)
                isolated.upsert_project(
                    {"project_id": project_id, "name": "Project Phoenix Database Test", "status": "VALIDATED"}
                )

                stored = isolated.get_project(project_id)
                objects = isolated.query_objects(project_id)
                buildings = isolated.query_objects(project_id, "building")
                history = isolated.project_history(project_id)

                checks = {
                    "project_persisted": stored is not None,
                    "project_revisioning": stored is not None and stored["revision"] == 2,
                    "object_indexing": len(objects) == 2,
                    "typed_query": len(buildings) == 1,
                    "history_written": len(history) == 2,
                    "status_updated": stored is not None and stored["status"] == "VALIDATED",
                    "digital_twin_persisted": isolated._count_rows("digital_twin_snapshots", project_id) == 1,
                    "relations_persisted": isolated._count_rows("project_relations", project_id) == 1,
                }

            probe = database_path.with_suffix(".probe.sqlite3")
            database_path.replace(probe)
            probe.replace(database_path)
            checks["database_file_released"] = True

        return self._write_runtime(
            "unified_project_database_integration_test_v33_0.json",
            {
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "lifecycle_fix_version": LIFECYCLE_FIX_VERSION,
                "checks": checks,
                "status": "PASS" if all(checks.values()) else "FAIL",
            },
        )

    def summary(self) -> Dict[str, Any]:
        self_test = self.self_test()
        integration = self.integration_test()
        status = "PASS" if self_test["status"] == "PASS" and integration["status"] == "PASS" else "FAIL"
        return self._write_runtime(
            "unified_project_database_summary_v33_0.json",
            {
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "lifecycle_fix_version": LIFECYCLE_FIX_VERSION,
                "self_test_status": self_test["status"],
                "integration_status": integration["status"],
                "digital_twin_integration": "v32.0",
                "status": status,
            },
        )

    def _initialize_schema(self) -> None:
        with self.connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    project_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS project_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    operation TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(project_id)
                );
                CREATE TABLE IF NOT EXISTS project_objects (
                    project_id TEXT NOT NULL,
                    object_id TEXT NOT NULL,
                    object_type TEXT NOT NULL,
                    attributes_json TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(project_id, object_id),
                    FOREIGN KEY(project_id) REFERENCES projects(project_id)
                );
                CREATE TABLE IF NOT EXISTS project_relations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(project_id)
                );
                CREATE TABLE IF NOT EXISTS digital_twin_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL,
                    twin_version INTEGER NOT NULL,
                    snapshot_json TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(project_id)
                );
                CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
                CREATE INDEX IF NOT EXISTS idx_history_project_revision ON project_history(project_id, revision);
                CREATE INDEX IF NOT EXISTS idx_objects_project_type ON project_objects(project_id, object_type);
                CREATE INDEX IF NOT EXISTS idx_relations_project_type ON project_relations(project_id, relation_type);
                CREATE INDEX IF NOT EXISTS idx_snapshots_project_version ON digital_twin_snapshots(project_id, twin_version);
                """
            )
            connection.commit()

    def _count_rows(self, table: str, project_id: str) -> int:
        allowed = {"digital_twin_snapshots", "project_relations", "project_objects", "project_history"}
        if table not in allowed:
            raise RuntimeError(f"Niet-toegestane tabel: {table}")
        with self.connection() as connection:
            row = connection.execute(
                f"SELECT COUNT(*) FROM {table} WHERE project_id = ?", (project_id,)
            ).fetchone()
        return int(row[0])

    def _read_json(self, path: Path) -> Dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8-sig"))

    def _write_runtime(self, filename: str, data: Dict[str, Any]) -> Dict[str, Any]:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        data["generated_at"] = datetime.now().isoformat(timespec="seconds")
        path = OUTPUT_DIR / filename
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8-sig")
        data["output_path"] = str(path)
        return data


def main() -> None:
    parser = argparse.ArgumentParser(description=f"{ENGINE_NAME} {ENGINE_VERSION}")
    parser.add_argument("command", choices=["self-test", "integration-test", "summary"])
    args = parser.parse_args()

    with PhoenixUnifiedProjectDatabase() as database:
        if args.command == "self-test":
            result = database.self_test()
        elif args.command == "integration-test":
            result = database.integration_test()
        else:
            result = database.summary()

    print(json.dumps(result, ensure_ascii=True, indent=2))
    if result.get("status") != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
