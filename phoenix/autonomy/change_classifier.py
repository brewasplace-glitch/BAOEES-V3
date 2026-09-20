from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable
import hashlib
import json
import re


def _canonical(obj: Any) -> bytes:
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _under(path: str, root: str) -> bool:
    return path.casefold().startswith(root.casefold())


def normalize_repository_path(
    value: str,
    *,
    windows_reserved_names: Iterable[str] = (),
) -> str:
    raw = str(value)
    if not raw or "\x00" in raw:
        raise PermissionError("PHASE10_PATH_EMPTY_OR_NUL_DENY")
    raw = raw.replace("\\", "/")
    if raw.startswith("/") or raw.startswith("//") or re.match(r"^[A-Za-z]:", raw):
        raise PermissionError("PHASE10_ABSOLUTE_PATH_DENY")
    parts = raw.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise PermissionError("PHASE10_PATH_TRAVERSAL_OR_EMPTY_SEGMENT_DENY")
    reserved = {str(x).upper() for x in windows_reserved_names}
    normalized: list[str] = []
    for part in parts:
        if part != part.rstrip(" ."):
            raise PermissionError("PHASE10_WINDOWS_TRAILING_DOT_SPACE_DENY")
        if ":" in part:
            raise PermissionError("PHASE10_ALTERNATE_DATA_STREAM_DENY")
        stem = part.partition(".")[0].upper()
        if stem in reserved:
            raise PermissionError("PHASE10_WINDOWS_RESERVED_NAME_DENY")
        normalized.append(part)
    return "/".join(normalized)


@dataclass(frozen=True)
class ChangeRecord:
    status: str
    path: str
    size: int
    sha256: str
    is_symlink: bool = False

    @classmethod
    def from_file(cls, status: str, path: str, absolute_path: Path) -> "ChangeRecord":
        target = Path(absolute_path)
        if target.is_symlink():
            return cls(status, path, 0, "0" * 64, True)
        data = target.read_bytes()
        return cls(status, path, len(data), hashlib.sha256(data).hexdigest(), False)


@dataclass(frozen=True)
class ChangeClassification:
    lane: str
    approval_required: bool
    automatic_fast_forward_promotion: bool
    paths: tuple[str, ...]
    total_bytes: int
    manifest_sha256: str


class RepositoryChangeClassifier:
    def __init__(self, cycle_policy: dict[str, Any], protected_policy: dict[str, Any]):
        self.cycle_policy = dict(cycle_policy)
        self.protected_policy = dict(protected_policy)
        if self.cycle_policy.get("schema") != "PHOENIX_REPOSITORY_IMPROVEMENT_CYCLE_POLICY_V1":
            raise RuntimeError("Phase-10 repository cycle policy schema invalid")
        if self.cycle_policy.get("fail_closed") is not True:
            raise RuntimeError("Phase-10 repository cycle policy must fail closed")
        if self.protected_policy.get("schema") != "PHOENIX_PROTECTED_REPOSITORY_PATHS_V1":
            raise RuntimeError("Phase-10 protected path policy schema invalid")
        self.reserved = tuple(self.protected_policy.get("windows_reserved_names", ()))

    @classmethod
    def from_repo(cls, repo_root: Path) -> "RepositoryChangeClassifier":
        cfg = Path(repo_root) / "configs" / "phoenix"
        return cls(
            json.loads(
                (cfg / "repository_improvement_cycle_policy_v1.json").read_text(
                    encoding="utf-8-sig"
                )
            ),
            json.loads(
                (cfg / "protected_repository_paths_v1.json").read_text(
                    encoding="utf-8-sig"
                )
            ),
        )

    def normalize(self, path: str) -> str:
        return normalize_repository_path(path, windows_reserved_names=self.reserved)

    def _assert_unprotected(self, path: str) -> None:
        low = path.casefold()
        for root in self.protected_policy.get("protected_roots", ()):
            normalized_root = self.normalize(str(root).rstrip("/")) + "/"
            if low.startswith(normalized_root.casefold()):
                raise PermissionError(f"PHASE10_PROTECTED_ROOT_DENY:{path}")
        exact = {
            self.normalize(str(x)).casefold()
            for x in self.protected_policy.get("protected_exact_paths", ())
        }
        if low in exact:
            raise PermissionError(f"PHASE10_PROTECTED_EXACT_PATH_DENY:{path}")
        for suffix in self.protected_policy.get("protected_suffixes", ()):
            if low.endswith(str(suffix).casefold()):
                raise PermissionError(f"PHASE10_PROTECTED_SECRET_SUFFIX_DENY:{path}")

    def _validate_lane(
        self,
        records: tuple[ChangeRecord, ...],
        lane: dict[str, Any],
    ) -> ChangeClassification:
        roots = tuple(
            self.normalize(str(x).rstrip("/")) + "/" for x in lane["allowed_roots"]
        )
        extensions = {str(x).casefold() for x in lane["allowed_extensions"]}
        total = 0
        paths: list[str] = []
        material: list[dict[str, Any]] = []
        for record in records:
            path = self.normalize(record.path)
            if not any(_under(path, root) for root in roots):
                raise PermissionError(f"PHASE10_LANE_PATH_SCOPE_DENY:{path}")
            if PurePosixPath(path).suffix.casefold() not in extensions:
                raise PermissionError(f"PHASE10_EXTENSION_DENY:{path}")
            if record.size < 0 or record.size > int(lane["max_file_bytes"]):
                raise PermissionError(f"PHASE10_FILE_SIZE_DENY:{path}")
            total += int(record.size)
            paths.append(path)
            material.append(
                {
                    "status": record.status,
                    "path": path,
                    "size": int(record.size),
                    "sha256": str(record.sha256),
                }
            )
        if len(records) > int(lane["max_files"]):
            raise PermissionError("PHASE10_FILE_COUNT_DENY")
        if total > int(lane["max_total_bytes"]):
            raise PermissionError("PHASE10_TOTAL_SIZE_DENY")
        material.sort(key=lambda x: x["path"].casefold())
        return ChangeClassification(
            lane=str(lane["id"]),
            approval_required=bool(lane["approval_required"]),
            automatic_fast_forward_promotion=bool(
                lane["automatic_fast_forward_promotion"]
            ),
            paths=tuple(sorted(paths, key=str.casefold)),
            total_bytes=total,
            manifest_sha256=hashlib.sha256(_canonical(material)).hexdigest(),
        )

    def classify(self, changes: Iterable[ChangeRecord]) -> ChangeClassification:
        records = tuple(changes)
        if not records:
            raise PermissionError("PHASE10_EMPTY_CHANGESET_DENY")
        allowed_status = {str(x) for x in self.cycle_policy["allowed_status_codes"]}
        normalized_seen: set[str] = set()
        normalized_records: list[ChangeRecord] = []
        for record in records:
            path = self.normalize(record.path)
            folded = path.casefold()
            if folded in normalized_seen:
                raise PermissionError("PHASE10_CASE_COLLISION_DENY")
            normalized_seen.add(folded)
            if record.status not in allowed_status:
                raise PermissionError(f"PHASE10_STATUS_DENY:{record.status}")
            if record.is_symlink:
                raise PermissionError(f"PHASE10_SYMLINK_OR_JUNCTION_DENY:{path}")
            if not re.fullmatch(r"[a-f0-9]{64}", str(record.sha256)):
                raise PermissionError(f"PHASE10_CONTENT_SHA256_INVALID:{path}")
            self._assert_unprotected(path)
            normalized_records.append(
                ChangeRecord(record.status, path, record.size, record.sha256, False)
            )

        normalized_tuple = tuple(normalized_records)
        lane_a = self.cycle_policy["lane_a"]
        lane_a_roots = tuple(
            self.normalize(str(x).rstrip("/")) + "/" for x in lane_a["allowed_roots"]
        )
        if all(any(_under(r.path, root) for root in lane_a_roots) for r in normalized_tuple):
            return self._validate_lane(normalized_tuple, lane_a)

        lane_b = self.cycle_policy["lane_b"]
        required_source = (
            self.normalize(str(lane_b["required_source_root"]).rstrip("/")) + "/"
        )
        if not any(_under(r.path, required_source) for r in normalized_tuple):
            raise PermissionError("PHASE10_LANE_B_EXECUTABLE_SOURCE_REQUIRED")
        return self._validate_lane(normalized_tuple, lane_b)
