from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class UpdateManifest:
    update_id: str
    version: str
    description: str
    files: list[dict[str, str]]
    test_commands: list[list[str]]
    commit_message: str
    auto_push: bool

    @classmethod
    def load(cls, path: Path) -> "UpdateManifest":
        data = json.loads(path.read_text(encoding="utf-8-sig"))

        required = {
            "update_id",
            "version",
            "description",
            "files",
            "test_commands",
            "commit_message",
        }
        missing = sorted(required.difference(data))
        if missing:
            raise ValueError(f"Manifest mist velden: {', '.join(missing)}")

        return cls(
            update_id=str(data["update_id"]),
            version=str(data["version"]),
            description=str(data["description"]),
            files=list(data["files"]),
            test_commands=list(data["test_commands"]),
            commit_message=str(data["commit_message"]),
            auto_push=bool(data.get("auto_push", True)),
        )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_manifest_files(package_root: Path, manifest: UpdateManifest) -> list[str]:
    errors: list[str] = []

    for item in manifest.files:
        source = package_root / item["source"]
        expected = item["sha256"].lower()

        if not source.is_file():
            errors.append(f"Ontbrekend pakketbestand: {item['source']}")
            continue

        actual = sha256_file(source)
        if actual != expected:
            errors.append(
                f"Checksum mismatch voor {item['source']}: "
                f"verwacht {expected}, gevonden {actual}"
            )

    return errors
