from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


ENGINE_NAME = "Phoenix Autonomous Release & Git Finalization Engine"
ENGINE_VERSION = "v21.0"


def find_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("PROJECT-PHOENIX root niet gevonden.")


ROOT = find_root()
POLICY_PATH = ROOT / "configs/phoenix/release_finalization_policy_v21_0.json"
OUTPUT_DIR = ROOT / "outputs/runtime/v21_0"


class PhoenixReleaseFinalizationEngine:
    def __init__(self) -> None:
        self.policy = self._read_json(POLICY_PATH)

    def self_test(self) -> Dict[str, Any]:
        checks = {
            "policy_exists": POLICY_PATH.is_file(),
            "git_directory_exists": (ROOT / ".git").exists(),
            "python_supported": sys.version_info >= (3, 10),
            "output_directory_writable": self._writable(OUTPUT_DIR),
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

    def audit(self) -> Dict[str, Any]:
        branch = self._run(["git", "branch", "--show-current"])
        status = self._run(["git", "status", "--porcelain"])
        diff_check = self._run(["git", "diff", "--check"])
        staged = self._run(["git", "diff", "--cached", "--name-only"])
        untracked = self._run(["git", "ls-files", "--others", "--exclude-standard"])

        result = {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "branch": branch["stdout"].strip(),
            "working_tree_clean": not status["stdout"].strip(),
            "diff_check_pass": diff_check["returncode"] == 0,
            "staged_files": [
                line for line in staged["stdout"].splitlines() if line.strip()
            ],
            "untracked_files": [
                line for line in untracked["stdout"].splitlines() if line.strip()
            ],
            "status": (
                "PASS"
                if branch["returncode"] == 0
                and status["returncode"] == 0
                and diff_check["returncode"] == 0
                else "FAIL"
            ),
        }
        return self._write_report("audit", result)

    def release_plan(self, version: str, commit_message: str) -> Dict[str, Any]:
        audit = self.audit()
        plan = {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "target_version": version,
            "commit_message": commit_message,
            "required_gates": [
                "working_tree_clean_before_install",
                "tests_pass",
                "git_diff_check_pass",
                "expected_files_only",
                "commit_success",
                "push_success",
                "working_tree_clean_after_push",
            ],
            "audit": audit,
            "mode": "DRY_RUN",
            "automatic_commit_push": False,
            "status": "PASS" if audit["status"] == "PASS" else "FAIL",
        }
        return self._write_report("release_plan", plan)

    def _run(self, command: List[str]) -> Dict[str, Any]:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        return {
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }

    def _read_json(self, path: Path) -> Dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8-sig"))

    def _write_report(self, name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        data["generated_at"] = datetime.now().isoformat(timespec="seconds")
        path = OUTPUT_DIR / f"release_finalization_{name}_v21_0.json"
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8-sig",
        )
        data["report_path"] = str(path)
        return data

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
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("self-test")
    sub.add_parser("audit")

    plan = sub.add_parser("plan")
    plan.add_argument("--version", default="v21.0")
    plan.add_argument(
        "--commit-message",
        default="feat: Phoenix Core v21.0 Autonomous Release and Git Finalization Engine",
    )

    args = parser.parse_args()
    engine = PhoenixReleaseFinalizationEngine()

    if args.command == "self-test":
        result = engine.self_test()
    elif args.command == "audit":
        result = engine.audit()
    else:
        result = engine.release_plan(args.version, args.commit_message)

    print(json.dumps(result, ensure_ascii=True, indent=2))
    if result.get("status") != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
