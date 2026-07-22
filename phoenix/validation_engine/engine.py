"""Phoenix Validation Engine.

PVE performs deterministic repository and release-quality validation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import importlib
import json
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence


PVE_ID = "phoenix.validation_engine"
PVE_VERSION = "1.0.5"
SCHEMA_VERSION = "1.0"


class ValidationError(RuntimeError):
    """Raised when validation input is invalid."""


@dataclass(frozen=True)
class ValidationCheck:
    check_id: str
    passed: bool
    message: str
    details: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class ValidationReport:
    schema_version: str
    engine_id: str
    engine_version: str
    project_id: str
    passed: bool
    checks: tuple[ValidationCheck, ...]
    evidence_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "engine_id": self.engine_id,
            "engine_version": self.engine_version,
            "project_id": self.project_id,
            "passed": self.passed,
            "checks": [asdict(item) for item in self.checks],
            "evidence_sha256": self.evidence_sha256,
        }


class PhoenixValidationEngine:
    """Validate repository structure, JSON, imports and release manifests."""

    @staticmethod
    def _canonical_json(value: Any) -> str:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )

    @classmethod
    def _digest(cls, value: Any) -> str:
        return sha256(cls._canonical_json(value).encode("utf-8")).hexdigest()

    @staticmethod
    def _safe_relative(path: str) -> str:
        candidate = PurePosixPath(path)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ValidationError(f"Unsafe relative path: {path!r}")
        return candidate.as_posix()

    def validate_required_paths(
        self,
        repo_root: Path,
        required_paths: Sequence[str],
    ) -> ValidationCheck:
        missing: list[str] = []
        for item in required_paths:
            relative = self._safe_relative(item)
            if not (repo_root / relative).exists():
                missing.append(relative)
        return ValidationCheck(
            check_id="required_paths",
            passed=not missing,
            message="All required paths exist." if not missing else "Required paths are missing.",
            details={"missing": missing},
        )

    def validate_json_files(
        self,
        repo_root: Path,
        json_paths: Sequence[str],
    ) -> ValidationCheck:
        failures: list[dict[str, str]] = []
        for item in json_paths:
            relative = self._safe_relative(item)
            path = repo_root / relative
            if not path.is_file():
                failures.append({"path": relative, "error": "file_missing"})
                continue
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                failures.append({"path": relative, "error": str(exc)})
        return ValidationCheck(
            check_id="json_files",
            passed=not failures,
            message="All JSON files are valid." if not failures else "Invalid JSON files detected.",
            details={"failures": failures},
        )

    def validate_imports(self, modules: Sequence[str]) -> ValidationCheck:
        failures: list[dict[str, str]] = []
        for module in modules:
            try:
                importlib.import_module(module)
            except Exception as exc:
                failures.append({"module": module, "error": str(exc)})
        return ValidationCheck(
            check_id="python_imports",
            passed=not failures,
            message="All Python imports succeeded." if not failures else "Python import failures detected.",
            details={"failures": failures},
        )

    def validate_release_manifest(
        self,
        repo_root: Path,
        manifest_path: str,
    ) -> ValidationCheck:
        relative = self._safe_relative(manifest_path)
        path = repo_root / relative
        failures: list[str] = []

        if not path.is_file():
            failures.append("manifest_missing")
        else:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                failures.append(f"manifest_invalid_json:{exc}")
                payload = {}

            for key in ("release_id", "version"):
                if not str(payload.get(key, "")).strip():
                    failures.append(f"missing_{key}")

            include_files = payload.get("include_files")
            if include_files is not None:
                if not isinstance(include_files, list):
                    failures.append("include_files_not_list")
                else:
                    for item in include_files:
                        try:
                            safe = self._safe_relative(str(item))
                        except ValidationError as exc:
                            failures.append(str(exc))
                            continue
                        if not (repo_root / safe).is_file():
                            failures.append(f"missing_include:{safe}")

        return ValidationCheck(
            check_id="release_manifest",
            passed=not failures,
            message="Release manifest is valid." if not failures else "Release manifest validation failed.",
            details={"failures": failures},
        )

    def run(
        self,
        *,
        project_id: str,
        repo_root: Path,
        required_paths: Sequence[str] = (),
        json_paths: Sequence[str] = (),
        import_modules: Sequence[str] = (),
        release_manifest: str | None = None,
    ) -> ValidationReport:
        if not project_id.strip():
            raise ValidationError("project_id must not be empty.")
        if not repo_root.is_dir():
            raise ValidationError(f"Repository root does not exist: {repo_root}")

        checks: list[ValidationCheck] = [
            self.validate_required_paths(repo_root, required_paths),
            self.validate_json_files(repo_root, json_paths),
            self.validate_imports(import_modules),
        ]
        if release_manifest:
            checks.append(self.validate_release_manifest(repo_root, release_manifest))

        core = {
            "schema_version": SCHEMA_VERSION,
            "engine_id": PVE_ID,
            "engine_version": PVE_VERSION,
            "project_id": project_id,
            "passed": all(item.passed for item in checks),
            "checks": [asdict(item) for item in checks],
        }
        return ValidationReport(
            schema_version=SCHEMA_VERSION,
            engine_id=PVE_ID,
            engine_version=PVE_VERSION,
            project_id=project_id,
            passed=core["passed"],
            checks=tuple(checks),
            evidence_sha256=self._digest(core),
        )
