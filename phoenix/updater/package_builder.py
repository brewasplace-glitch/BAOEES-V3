from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Iterable

from .manifest import sha256_file


class PackageBuilder:
    def __init__(self, repository_root: Path) -> None:
        self.root = repository_root.resolve()
        self.incoming = self.root / "updates/incoming"
        self.incoming.mkdir(parents=True, exist_ok=True)

    def build(
        self,
        *,
        update_id: str,
        version: str,
        description: str,
        source_files: Iterable[str],
        test_commands: list[list[str]],
        commit_message: str,
        auto_push: bool = True,
        overwrite: bool = False,
    ) -> Path:
        update_id = update_id.strip()
        if not update_id:
            raise ValueError("update_id mag niet leeg zijn.")

        package = self.incoming / update_id
        if package.exists():
            if not overwrite:
                raise FileExistsError(f"Updatepakket bestaat al: {package}")
            shutil.rmtree(package)

        payload = package / "payload"
        payload.mkdir(parents=True)

        manifest_files: list[dict[str, str]] = []

        for value in source_files:
            relative = Path(value)
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"Onveilig bronpad: {value}")

            source = self.root / relative
            if not source.is_file():
                raise FileNotFoundError(f"Bronbestand ontbreekt: {relative}")

            target = payload / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

            manifest_files.append(
                {
                    "source": (Path("payload") / relative).as_posix(),
                    "target": relative.as_posix(),
                    "sha256": sha256_file(target),
                }
            )

        manifest = {
            "update_id": update_id,
            "version": version,
            "description": description,
            "files": manifest_files,
            "test_commands": test_commands,
            "commit_message": commit_message,
            "auto_push": auto_push,
        }

        (package / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8-sig",
        )
        return package