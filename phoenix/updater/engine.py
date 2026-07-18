from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from .manifest import UpdateManifest, validate_manifest_files


class PhoenixUpdater:
    VERSION = "v1.1"

    def __init__(self, repository_root: Path) -> None:
        self.root = repository_root.resolve()
        self.updates = self.root / "updates"
        self.incoming = self.updates / "incoming"
        self.installed = self.updates / "installed"
        self.rejected = self.updates / "rejected"
        self.rollback = self.updates / "rollback"
        self.artifacts = self.root / "artifacts/releases/updater_v1_1"

        for directory in (
            self.incoming,
            self.installed,
            self.rejected,
            self.rollback,
            self.artifacts,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    def discover(self) -> list[Path]:
        return sorted(
            (
                path
                for path in self.incoming.iterdir()
                if path.is_dir() and (path / "manifest.json").is_file()
            ),
            key=lambda path: path.name.lower(),
        )

    def next_package(self) -> Path | None:
        packages = self.discover()
        return packages[0] if packages else None

    def inspect(self, package: Path) -> dict[str, Any]:
        manifest = UpdateManifest.load(package / "manifest.json")
        errors = validate_manifest_files(package, manifest)

        return {
            "engine": "Phoenix Updater",
            "version": self.VERSION,
            "update_id": manifest.update_id,
            "package": str(package),
            "errors": errors,
            "status": "PASS" if not errors else "FAIL",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        }

    def apply_next(
        self,
        *,
        run_tests: bool = True,
        commit: bool = True,
        push: bool = True,
    ) -> dict[str, Any]:
        package = self.next_package()
        if package is None:
            return {
                "engine": "Phoenix Updater",
                "version": self.VERSION,
                "status": "PASS",
                "message": "Geen updatepakketten beschikbaar.",
                "packages": [],
            }

        return self.apply(
            package,
            run_tests=run_tests,
            commit=commit,
            push=push,
        )

    def apply(
        self,
        package: Path,
        *,
        run_tests: bool = True,
        commit: bool = False,
        push: bool = False,
    ) -> dict[str, Any]:
        manifest = UpdateManifest.load(package / "manifest.json")
        validation = self.inspect(package)

        if validation["status"] != "PASS":
            self._move_package(package, self.rejected / package.name)
            return validation

        dirty = self._git_status()
        permitted_prefix = f"?? {package.relative_to(self.root).as_posix()}/"
        unexpected = [line for line in dirty if not line.startswith(permitted_prefix)]
        if unexpected:
            raise RuntimeError(
                "Updater geblokkeerd: working tree bevat wijzigingen buiten "
                f"het updatepakket: {unexpected}"
            )

        backup = self.rollback / (
            f"{manifest.update_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        backup.mkdir(parents=True, exist_ok=False)

        changed: list[str] = []

        try:
            for item in manifest.files:
                source = package / item["source"]
                relative_target = Path(item["target"])

                if relative_target.is_absolute() or ".." in relative_target.parts:
                    raise ValueError(f"Onveilig doelpad: {relative_target}")

                target = self.root / relative_target
                backup_target = backup / relative_target

                if target.exists():
                    backup_target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(target, backup_target)

                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                changed.append(relative_target.as_posix())

            test_results = []
            if run_tests:
                for command in manifest.test_commands:
                    completed = subprocess.run(
                        command,
                        cwd=self.root,
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                    test_results.append(
                        {
                            "command": command,
                            "returncode": completed.returncode,
                            "stdout": completed.stdout,
                            "stderr": completed.stderr,
                        }
                    )
                    if completed.returncode != 0:
                        raise RuntimeError(
                            f"Test mislukt: {' '.join(command)}\n"
                            f"{completed.stdout}\n{completed.stderr}"
                        )

            if commit:
                subprocess.run(
                    ["git", "add", "--", *changed],
                    cwd=self.root,
                    check=True,
                )
                subprocess.run(
                    ["git", "commit", "-m", manifest.commit_message],
                    cwd=self.root,
                    check=True,
                )

                if push and manifest.auto_push:
                    branch = subprocess.run(
                        ["git", "branch", "--show-current"],
                        cwd=self.root,
                        text=True,
                        capture_output=True,
                        check=True,
                    ).stdout.strip()
                    subprocess.run(
                        ["git", "push", "origin", branch],
                        cwd=self.root,
                        check=True,
                    )

            destination = self.installed / package.name
            self._move_package(package, destination)

            result = {
                "engine": "Phoenix Updater",
                "version": self.VERSION,
                "update_id": manifest.update_id,
                "changed_files": changed,
                "backup": str(backup),
                "tests": test_results,
                "committed": commit,
                "pushed": push and manifest.auto_push,
                "status": "PASS",
                "generated_at": datetime.now().isoformat(timespec="seconds"),
            }
            self._write_report(manifest.update_id, result)
            return result

        except Exception:
            self._restore_backup(backup, changed)
            raise

    def _restore_backup(self, backup: Path, changed: list[str]) -> None:
        for relative in changed:
            target = self.root / relative
            backup_source = backup / relative

            if backup_source.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup_source, target)
            elif target.exists():
                target.unlink()

    def _git_status(self) -> list[str]:
        completed = subprocess.run(
            ["git", "status", "--porcelain", "-uall"],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=True,
        )
        return [line for line in completed.stdout.splitlines() if line.strip()]

    @staticmethod
    def _move_package(source: Path, destination: Path) -> None:
        if destination.exists():
            shutil.rmtree(destination)
        shutil.move(str(source), str(destination))

    def _write_report(self, update_id: str, result: dict[str, Any]) -> None:
        path = self.artifacts / f"{update_id}.json"
        path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8-sig",
        )
