from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ENGINE_NAME = "Phoenix Deterministic Runtime & Release Finalization Engine"
ENGINE_VERSION = "v23.0"


def find_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("PROJECT-PHOENIX root niet gevonden.")


ROOT = find_root()
POLICY_PATH = ROOT / "configs/phoenix/deterministic_release_policy_v23_0.json"
OUTPUT_DIR = ROOT / "outputs/runtime/v23_0"


class PhoenixDeterministicReleaseEngine:
    def __init__(self) -> None:
        self.policy = self._read_json(POLICY_PATH)

    def self_test(self) -> Dict[str, Any]:
        checks = {
            "policy_exists": POLICY_PATH.is_file(),
            "git_repository_exists": (ROOT / ".git").exists(),
            "python_supported": sys.version_info >= (3, 10),
            "runtime_writable": self._writable(OUTPUT_DIR),
        }
        return self._write_report(
            "self_test",
            {
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "checks": checks,
                "status": "PASS" if all(checks.values()) else "FAIL",
            },
        )

    def inventory(self) -> Dict[str, Any]:
        files: List[Dict[str, Any]] = []
        for path in sorted(OUTPUT_DIR.rglob("*")):
            if not path.is_file():
                continue
            files.append(
                {
                    "path": path.relative_to(ROOT).as_posix(),
                    "size_bytes": path.stat().st_size,
                    "sha256": self._sha256(path),
                }
            )

        return self._write_report(
            "inventory",
            {
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "files": files,
                "file_count": len(files),
                "status": "PASS",
            },
        )

    def audit(self) -> Dict[str, Any]:
        status = self._run(["git", "status", "--porcelain"])
        diff_check = self._run(["git", "diff", "--check"])
        branch = self._run(["git", "branch", "--show-current"])

        return self._write_report(
            "audit",
            {
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "branch": branch["stdout"].strip(),
                "working_tree_clean": not status["stdout"].strip(),
                "diff_check_pass": diff_check["returncode"] == 0,
                "status": (
                    "PASS"
                    if status["returncode"] == 0
                    and diff_check["returncode"] == 0
                    and branch["returncode"] == 0
                    else "FAIL"
                ),
            },
        )

    def finalize_plan(self) -> Dict[str, Any]:
        required_gates = [
            "all_runtime_reports_written_before_staging",
            "syntax_tests_pass",
            "unit_tests_pass",
            "self_test_pass",
            "inventory_generated",
            "git_diff_check_pass",
            "expected_files_only",
            "commit_success",
            "push_success",
            "working_tree_clean_after_push",
        ]
        return self._write_report(
            "finalize_plan",
            {
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "required_gates": required_gates,
                "post_commit_file_writes_allowed": False,
                "automatic_commit_push": True,
                "status": "PASS",
            },
        )

    def _run(self, command: List[str]) -> Dict[str, Any]:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        return {
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }

    def _read_json(self, path: Path) -> Dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8-sig"))

    def _write_report(self, name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        data["generated_at"] = datetime.now().isoformat(timespec="seconds")
        path = OUTPUT_DIR / f"deterministic_release_{name}_v23_0.json"
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8-sig",
        )
        data["report_path"] = str(path)
        return data

    def _sha256(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _writable(self, path: Path) -> bool:
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            return True
        except OSError:
            return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description=f"{ENGINE_NAME} {ENGINE_VERSION}"
    )
    parser.add_argument(
        "command",
        choices=["self-test", "inventory", "audit", "plan"],
    )
    args = parser.parse_args()

    engine = PhoenixDeterministicReleaseEngine()
    if args.command == "self-test":
        result = engine.self_test()
    elif args.command == "inventory":
        result = engine.inventory()
    elif args.command == "audit":
        result = engine.audit()
    else:
        result = engine.finalize_plan()

    print(json.dumps(result, ensure_ascii=True, indent=2))
    if result.get("status") != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
