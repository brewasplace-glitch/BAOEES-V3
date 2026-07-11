from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence


ENGINE_NAME = "Phoenix Update Center"
ENGINE_VERSION = "v9.0"


def find_project_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("PROJECT-PHOENIX repository root niet gevonden.")


PROJECT_ROOT = find_project_root()
POLICY_PATH = PROJECT_ROOT / "configs" / "phoenix" / "update_center_policy_v9_0.json"
REPORT_DIR = PROJECT_ROOT / "outputs" / "runtime"
BACKUP_ROOT = PROJECT_ROOT / "backups" / "update_center"


@dataclass(frozen=True)
class CommandResult:
    command: Sequence[str]
    returncode: int
    stdout: str
    stderr: str


class UpdateCenterError(RuntimeError):
    pass


class PhoenixUpdateCenter:
    def __init__(self, package: Path) -> None:
        self.package = package.resolve()
        self.policy = self.read_json(POLICY_PATH)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.report_path = REPORT_DIR / f"phoenix_update_center_{self.timestamp}.json"
        self.backup_dir = BACKUP_ROOT / self.timestamp

    def inspect(self) -> Dict[str, Any]:
        with self.extracted_package() as package_root:
            manifest = self.load_manifest(package_root)
            validation = self.validate_package(package_root, manifest)
            report = self.base_report("INSPECT")
            report.update(
                {
                    "manifest": manifest,
                    "validation": validation,
                    "status": "VALID" if validation["valid"] else "INVALID",
                }
            )
            self.write_report(report)
            return report

    def apply(self, approval_token: str) -> Dict[str, Any]:
        report = self.base_report("APPLY")
        report["approval_token_received"] = approval_token == self.policy["required_approval_token"]

        if approval_token != self.policy["required_approval_token"]:
            report["status"] = "BLOCKED_NO_GO"
            self.write_report(report)
            return report

        repository = self.repository_preflight()
        report["repository_preflight"] = repository
        if not repository["ready"]:
            report["status"] = "BLOCKED_REPOSITORY_PREFLIGHT"
            self.write_report(report)
            return report

        with self.extracted_package() as package_root:
            manifest = self.load_manifest(package_root)
            validation = self.validate_package(package_root, manifest)
            report["manifest"] = manifest
            report["validation"] = validation

            if not validation["valid"]:
                report["status"] = "BLOCKED_INVALID_PACKAGE"
                self.write_report(report)
                return report

            self.backup_dir.mkdir(parents=True, exist_ok=False)
            rollback_manifest = self.create_backups(package_root, manifest)
            report["rollback_manifest"] = str(rollback_manifest)

            try:
                installed = self.install_files(package_root, manifest)
                report["installed_files"] = installed
                post_validation = self.post_validate(installed)
                report["post_validation"] = post_validation
                report["status"] = (
                    "APPLIED_SAFE_FOR_REVIEW"
                    if post_validation["safe_for_review"]
                    else "APPLIED_REVIEW_REQUIRED"
                )
            except Exception as exc:
                report["status"] = "FAILED"
                report["error"] = str(exc)
                report["rollback_required"] = True

            self.write_report(report)
            return report

    def self_test(self) -> Dict[str, Any]:
        checks = {
            "project_root_exists": PROJECT_ROOT.exists(),
            "git_directory_exists": (PROJECT_ROOT / ".git").exists(),
            "policy_exists": POLICY_PATH.exists(),
            "report_directory_writable": self.directory_writable(REPORT_DIR),
            "backup_directory_writable": self.directory_writable(BACKUP_ROOT),
            "python_version_supported": sys.version_info >= (3, 10),
        }
        result = {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "checks": checks,
            "status": "PASS" if all(checks.values()) else "FAIL",
        }
        return result

    def repository_preflight(self) -> Dict[str, Any]:
        status = self.run(["git", "status", "--porcelain"])
        branch = self.run(["git", "branch", "--show-current"])
        head = self.run(["git", "rev-parse", "HEAD"])
        clean = status.returncode == 0 and not status.stdout.strip()
        return {
            "working_tree_clean": clean,
            "branch": branch.stdout.strip(),
            "head": head.stdout.strip(),
            "ready": clean and branch.returncode == 0 and head.returncode == 0,
        }

    def validate_package(self, package_root: Path, manifest: Dict[str, Any]) -> Dict[str, Any]:
        errors: List[str] = []
        entries = manifest.get("files", [])

        if manifest.get("format_version") != "1.0":
            errors.append("Niet-ondersteunde package format_version.")
        if not isinstance(entries, list) or not entries:
            errors.append("Manifest bevat geen bestanden.")

        allowed_roots = tuple(self.policy["allowed_target_roots"])
        forbidden = tuple(self.policy["forbidden_target_prefixes"])
        seen: set[str] = set()
        checked_files = 0

        for entry in entries:
            relative = str(entry.get("path", "")).replace("\\", "/").strip("/")
            expected = str(entry.get("sha256", "")).lower()
            source = package_root / "files" / Path(relative)

            if not relative:
                errors.append("Leeg doelpad in manifest.")
                continue
            if relative in seen:
                errors.append(f"Dubbel doelpad: {relative}")
                continue
            seen.add(relative)

            if relative.startswith(forbidden):
                errors.append(f"Verboden doelpad: {relative}")
            if not relative.startswith(allowed_roots):
                errors.append(f"Doelpad buiten toegestane roots: {relative}")
            if ".." in Path(relative).parts:
                errors.append(f"Path traversal geblokkeerd: {relative}")
            if not source.is_file():
                errors.append(f"Bronbestand ontbreekt: {relative}")
                continue

            actual = self.sha256(source)
            if actual != expected:
                errors.append(f"Checksum mismatch: {relative}")
            checked_files += 1

        return {
            "valid": not errors,
            "errors": errors,
            "checked_files": checked_files,
            "package_name": manifest.get("package_name", ""),
            "package_version": manifest.get("package_version", ""),
        }

    def load_manifest(self, package_root: Path) -> Dict[str, Any]:
        manifest_path = package_root / "manifest.json"
        if not manifest_path.is_file():
            raise UpdateCenterError("manifest.json ontbreekt.")
        return self.read_json(manifest_path)

    def create_backups(self, package_root: Path, manifest: Dict[str, Any]) -> Path:
        records: List[Dict[str, Any]] = []
        for entry in manifest["files"]:
            relative = Path(str(entry["path"]).replace("\\", "/"))
            target = PROJECT_ROOT / relative
            record: Dict[str, Any] = {
                "path": relative.as_posix(),
                "existed": target.exists(),
                "backup": "",
            }
            if target.is_file():
                backup = self.backup_dir / "files" / relative
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, backup)
                record["backup"] = str(backup)
                record["original_sha256"] = self.sha256(target)
            records.append(record)

        manifest_path = self.backup_dir / "rollback_manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "engine": ENGINE_NAME,
                    "engine_version": ENGINE_VERSION,
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                    "package": str(self.package),
                    "repository_head": self.run(["git", "rev-parse", "HEAD"]).stdout.strip(),
                    "files": records,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8-sig",
        )
        return manifest_path

    def install_files(self, package_root: Path, manifest: Dict[str, Any]) -> List[str]:
        installed: List[str] = []
        for entry in manifest["files"]:
            relative = Path(str(entry["path"]).replace("\\", "/"))
            source = package_root / "files" / relative
            target = PROJECT_ROOT / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            if self.sha256(target) != str(entry["sha256"]).lower():
                raise UpdateCenterError(f"Checksum na installatie ongeldig: {relative.as_posix()}")
            installed.append(relative.as_posix())
        return installed

    def post_validate(self, installed_files: Iterable[str]) -> Dict[str, Any]:
        python_files = [
            PROJECT_ROOT / relative
            for relative in installed_files
            if relative.lower().endswith(".py")
        ]
        python_results: List[Dict[str, Any]] = []

        for path in python_files:
            result = self.run([sys.executable, "-m", "py_compile", str(path)])
            python_results.append(
                {
                    "path": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                    "passed": result.returncode == 0,
                    "stderr": result.stderr,
                }
            )

        diff_check = self.run(["git", "diff", "--check"])
        status = self.run(["git", "status", "--porcelain"])
        all_python_passed = all(item["passed"] for item in python_results)

        return {
            "python_compile": python_results,
            "all_python_passed": all_python_passed,
            "git_diff_check_passed": diff_check.returncode == 0,
            "git_diff_check_output": diff_check.stdout + diff_check.stderr,
            "working_tree_changed": bool(status.stdout.strip()),
            "git_status": status.stdout,
            "safe_for_review": all_python_passed and diff_check.returncode == 0,
            "automatic_commit_push": False,
        }

    def extracted_package(self):
        if not self.package.is_file():
            raise UpdateCenterError(f"Updatepakket bestaat niet: {self.package}")
        if self.package.suffix.lower() != ".zip":
            raise UpdateCenterError("Alleen ZIP-updatepakketten zijn toegestaan.")

        class PackageContext:
            def __init__(self, outer: "PhoenixUpdateCenter") -> None:
                self.outer = outer
                self.temp: tempfile.TemporaryDirectory[str] | None = None
                self.root: Path | None = None

            def __enter__(self) -> Path:
                self.temp = tempfile.TemporaryDirectory(prefix="phoenix_update_center_")
                temp_root = Path(self.temp.name)
                with zipfile.ZipFile(self.outer.package, "r") as archive:
                    for info in archive.infolist():
                        candidate = (temp_root / info.filename).resolve()
                        if not str(candidate).startswith(str(temp_root.resolve()) + os.sep):
                            raise UpdateCenterError("Onveilig pad in ZIP geblokkeerd.")
                    archive.extractall(temp_root)

                manifest_candidates = list(temp_root.rglob("manifest.json"))
                if len(manifest_candidates) != 1:
                    raise UpdateCenterError("Updatepakket moet exact één manifest.json bevatten.")
                self.root = manifest_candidates[0].parent
                return self.root

            def __exit__(self, exc_type, exc, tb) -> None:
                if self.temp is not None:
                    self.temp.cleanup()

        return PackageContext(self)

    def base_report(self, mode: str) -> Dict[str, Any]:
        return {
            "engine": ENGINE_NAME,
            "engine_version": ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "mode": mode,
            "package": str(self.package),
            "project_root": str(PROJECT_ROOT),
            "automatic_commit_push": False,
        }

    def write_report(self, report: Dict[str, Any]) -> None:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        self.report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8-sig",
        )
        report["report_path"] = str(self.report_path)

    def read_json(self, path: Path) -> Dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8-sig"))

    def sha256(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def run(self, command: Sequence[str]) -> CommandResult:
        completed = subprocess.run(
            list(command),
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        return CommandResult(command, completed.returncode, completed.stdout, completed.stderr)

    def directory_writable(self, path: Path) -> bool:
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / f".phoenix_probe_{os.getpid()}"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            return True
        except OSError:
            return False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=f"{ENGINE_NAME} {ENGINE_VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)

    inspect_parser = sub.add_parser("inspect", help="Valideer een updatepakket zonder wijzigingen.")
    inspect_parser.add_argument("--package", required=True)

    apply_parser = sub.add_parser("apply", help="Pas een gevalideerd updatepakket gecontroleerd toe.")
    apply_parser.add_argument("--package", required=True)
    apply_parser.add_argument("--approval-token", default="")

    sub.add_parser("self-test", help="Test de Update Center-installatie.")
    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.command == "self-test":
        result = PhoenixUpdateCenter(Path(__file__)).self_test()
    else:
        center = PhoenixUpdateCenter(Path(args.package))
        if args.command == "inspect":
            result = center.inspect()
        else:
            result = center.apply(args.approval_token)

    print(json.dumps(result, ensure_ascii=True, indent=2))

    failed_statuses = {
        "FAIL",
        "INVALID",
        "BLOCKED_NO_GO",
        "BLOCKED_REPOSITORY_PREFLIGHT",
        "BLOCKED_INVALID_PACKAGE",
        "FAILED",
    }
    if result.get("status") in failed_statuses:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
