"""Manifest-driven update planning and state tracking for Project Phoenix."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

PUM_ID = "phoenix.update_manager"
PUM_VERSION = "1.0.0"
SCHEMA_VERSION = "1.0"

class UpdateError(RuntimeError):
    pass

@dataclass(frozen=True)
class UpdateManifest:
    update_id: str
    version: str
    install_files: tuple[str, ...]
    remove_files: tuple[str, ...] = ()
    tests: tuple[str, ...] = ()
    validation_config: str | None = None
    commit_message: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.update_id.strip() or not self.version.strip():
            raise UpdateError("update_id and version are required")
        if not self.install_files and not self.remove_files:
            raise UpdateError("at least one install or remove path is required")
        if set(self.install_files) & set(self.remove_files):
            raise UpdateError("a path cannot be installed and removed")
        for item in (*self.install_files, *self.remove_files):
            p = PurePosixPath(item)
            if p.is_absolute() or ".." in p.parts:
                raise UpdateError(f"unsafe update path: {item}")

@dataclass(frozen=True)
class UpdatePlan:
    schema_version: str
    manager_id: str
    manager_version: str
    update_id: str
    version: str
    install_files: tuple[str, ...]
    remove_files: tuple[str, ...]
    tests: tuple[str, ...]
    validation_config: str | None
    commit_message: str
    evidence_sha256: str
    def to_dict(self) -> dict[str, Any]: return asdict(self)

class PhoenixUpdateManager:
    @staticmethod
    def _canonical(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    @classmethod
    def _digest(cls, value: Any) -> str:
        return sha256(cls._canonical(value).encode("utf-8")).hexdigest()
    def load_manifest(self, path: Path) -> UpdateManifest:
        raw = json.loads(path.read_text(encoding="utf-8"))
        obj = UpdateManifest(
            update_id=str(raw["update_id"]), version=str(raw["version"]),
            install_files=tuple(map(str, raw.get("install_files", []))),
            remove_files=tuple(map(str, raw.get("remove_files", []))),
            tests=tuple(map(str, raw.get("tests", []))),
            validation_config=raw.get("validation_config"),
            commit_message=str(raw.get("commit_message", "")),
            metadata=dict(raw.get("metadata", {})),
        )
        obj.validate(); return obj
    def create_plan(self, manifest: UpdateManifest) -> UpdatePlan:
        manifest.validate()
        core = {
            "schema_version": SCHEMA_VERSION, "manager_id": PUM_ID, "manager_version": PUM_VERSION,
            "update_id": manifest.update_id, "version": manifest.version,
            "install_files": sorted(manifest.install_files), "remove_files": sorted(manifest.remove_files),
            "tests": list(manifest.tests), "validation_config": manifest.validation_config,
            "commit_message": manifest.commit_message,
        }
        return UpdatePlan(**core, evidence_sha256=self._digest(core))
    def write_state(self, destination: Path, *, plan: UpdatePlan, phase: str, commit_sha: str | None = None, push_pending: bool = False, message: str = "") -> Path:
        if phase not in {"planned", "installed", "validated", "committed", "pushed", "failed"}:
            raise UpdateError(f"unsupported phase: {phase}")
        data = {"schema_version": SCHEMA_VERSION, "manager": {"id": PUM_ID, "version": PUM_VERSION},
                "update_id": plan.update_id, "version": plan.version, "phase": phase,
                "commit_sha": commit_sha, "push_pending": bool(push_pending), "message": message,
                "plan_sha256": plan.evidence_sha256}
        data["state_sha256"] = self._digest(data)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(data, indent=2, sort_keys=True)+"\n", encoding="utf-8")
        return destination
