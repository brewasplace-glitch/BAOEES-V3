from __future__ import annotations

import argparse
import datetime as _dt
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Iterable


SCHEMA_VERSION = "1.0"
DECISIONS = ("REUSE", "REPAIR", "EXTEND", "BUILD")
DECISION_EXIT = {"BUILD": 0, "REUSE": 20, "REPAIR": 21, "EXTEND": 22}


class GateError(RuntimeError):
    pass


def _run(
    repo: Path,
    args: list[str],
    *,
    allow_codes: Iterable[int] = (0,),
) -> subprocess.CompletedProcess[str]:
    cp = subprocess.run(
        args,
        cwd=str(repo),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if cp.returncode not in set(allow_codes):
        raise GateError(
            f"command failed ({cp.returncode}): {' '.join(args)}\n"
            f"stdout:\n{cp.stdout}\nstderr:\n{cp.stderr}"
        )
    return cp


def _git(repo: Path, args: list[str], *, allow_codes: Iterable[int] = (0,)) -> subprocess.CompletedProcess[str]:
    return _run(repo, ["git", *args], allow_codes=allow_codes)


def _safe_rel_path(value: str) -> str:
    raw = str(value or "").strip().replace("\\", "/")
    if not raw:
        raise GateError("empty repository-relative path is not allowed")
    p = Path(raw)
    if p.is_absolute() or ".." in p.parts:
        raise GateError(f"unsafe repository-relative path: {value!r}")
    return raw


def _as_list(spec: dict[str, Any], key: str) -> list[str]:
    value = spec.get(key, [])
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(x, str) for x in value):
        raise GateError(f"{key} must be a JSON list of strings")
    return [x.strip() for x in value if x.strip()]


def validate_spec(spec: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(spec, dict):
        raise GateError("capability spec must be a JSON object")

    capability_id = str(spec.get("capability_id", "")).strip()
    if not capability_id:
        raise GateError("capability_id is required")
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{3,160}", capability_id):
        raise GateError("capability_id contains unsupported characters")

    normalized = {
        "schema_version": SCHEMA_VERSION,
        "capability_id": capability_id,
        "description": str(spec.get("description", "")).strip(),
        "keywords": _as_list(spec, "keywords"),
        "required_paths": [_safe_rel_path(x) for x in _as_list(spec, "required_paths")],
        "required_symbols": _as_list(spec, "required_symbols"),
        "required_test_paths": [_safe_rel_path(x) for x in _as_list(spec, "required_test_paths")],
        "optional_paths": [_safe_rel_path(x) for x in _as_list(spec, "optional_paths")],
    }
    if not any(
        normalized[k]
        for k in ("keywords", "required_paths", "required_symbols", "required_test_paths", "optional_paths")
    ):
        raise GateError("spec must contain at least one discovery or requirement field")
    return normalized


def _head_has_path(repo: Path, rel: str) -> bool:
    cp = _git(repo, ["cat-file", "-e", f"HEAD:{rel}"], allow_codes=(0, 1, 128))
    return cp.returncode == 0


def _worktree_has_path(repo: Path, rel: str) -> bool:
    return (repo / rel).exists()


def _git_grep(repo: Path, needle: str, limit: int = 50) -> list[str]:
    cp = _git(repo, ["grep", "-n", "-I", "-F", "-e", needle, "--", "."], allow_codes=(0, 1))
    if cp.returncode == 1 or not cp.stdout.strip():
        return []
    return cp.stdout.splitlines()[:limit]


def _history_hits(repo: Path, needles: list[str], limit: int = 30) -> list[str]:
    hits: list[str] = []
    seen: set[str] = set()
    for needle in needles:
        cp = _git(
            repo,
            ["log", "--all", "--oneline", "--regexp-ignore-case", f"--grep={re.escape(needle)}", "-n", "10"],
            allow_codes=(0,),
        )
        for line in cp.stdout.splitlines():
            if line and line not in seen:
                seen.add(line)
                hits.append(line)
                if len(hits) >= limit:
                    return hits
    return hits


def _run_python_test(repo: Path, rel: str) -> dict[str, Any]:
    path = repo / rel
    if not path.exists():
        return {
            "path": rel,
            "exists": False,
            "executed": False,
            "passed": False,
            "returncode": None,
            "stdout_tail": "",
            "stderr_tail": "",
        }

    cp = subprocess.run(
        [sys.executable, rel],
        cwd=str(repo),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return {
        "path": rel,
        "exists": True,
        "executed": True,
        "passed": cp.returncode == 0,
        "returncode": cp.returncode,
        "stdout_tail": "\n".join(cp.stdout.splitlines()[-20:]),
        "stderr_tail": "\n".join(cp.stderr.splitlines()[-20:]),
    }


def classify(repo: Path, raw_spec: dict[str, Any], *, run_tests: bool = True) -> dict[str, Any]:
    repo = repo.resolve()
    spec = validate_spec(raw_spec)

    inside = _git(repo, ["rev-parse", "--is-inside-work-tree"]).stdout.strip()
    if inside != "true":
        raise GateError(f"not a git work tree: {repo}")

    branch = _git(repo, ["branch", "--show-current"]).stdout.strip()
    head = _git(repo, ["rev-parse", "HEAD"]).stdout.strip()
    status = _git(repo, ["status", "--porcelain=v1", "--untracked-files=all"]).stdout.strip()
    if status:
        raise GateError(
            "worktree must be clean before capability classification; "
            "uncommitted content could produce an unsafe reuse/build decision"
        )

    required_paths = {
        p: {"head": _head_has_path(repo, p), "worktree": _worktree_has_path(repo, p)}
        for p in spec["required_paths"]
    }
    optional_paths = {
        p: {"head": _head_has_path(repo, p), "worktree": _worktree_has_path(repo, p)}
        for p in spec["optional_paths"]
    }
    required_symbols = {s: _git_grep(repo, s) for s in spec["required_symbols"]}
    keyword_hits = {k: _git_grep(repo, k) for k in spec["keywords"]}

    test_results: list[dict[str, Any]] = []
    for test_path in spec["required_test_paths"]:
        if run_tests:
            test_results.append(_run_python_test(repo, test_path))
        else:
            exists = _worktree_has_path(repo, test_path)
            test_results.append(
                {
                    "path": test_path,
                    "exists": exists,
                    "executed": False,
                    "passed": None,
                    "returncode": None,
                    "stdout_tail": "",
                    "stderr_tail": "",
                }
            )

    history_needles = list(
        dict.fromkeys([spec["capability_id"], *spec["keywords"], *spec["required_symbols"]])
    )
    history = _history_hits(repo, history_needles)

    missing_paths = [p for p, ev in required_paths.items() if not (ev["head"] and ev["worktree"])]
    missing_symbols = [s for s, hits in required_symbols.items() if not hits]
    missing_tests = [x["path"] for x in test_results if not x["exists"]]
    failing_tests = [x["path"] for x in test_results if x["executed"] and not x["passed"]]

    implementation_evidence = (
        sum(1 for ev in required_paths.values() if ev["head"] and ev["worktree"])
        + sum(1 for hits in required_symbols.values() if hits)
        + sum(1 for ev in optional_paths.values() if ev["head"] and ev["worktree"])
    )
    discovery_evidence = (
        sum(1 for hits in keyword_hits.values() if hits)
        + (1 if history else 0)
    )

    hard_requirements = len(required_paths) + len(required_symbols) + len(spec["required_test_paths"])
    hard_present = hard_requirements - len(missing_paths) - len(missing_symbols) - len(missing_tests)

    reasons: list[str] = []
    if implementation_evidence > 0 and failing_tests:
        decision = "REPAIR"
        reasons.append("implementation evidence exists but one or more required tests fail")
    elif implementation_evidence == 0 and discovery_evidence == 0:
        decision = "BUILD"
        reasons.append("no implementation or discovery evidence found in the clean repository")
    elif implementation_evidence == 0 and discovery_evidence > 0:
        decision = "EXTEND"
        reasons.append(
            "related repository/history evidence exists but required implementation contracts are not proven; "
            "new build is blocked pending reconciliation"
        )
    elif missing_paths or missing_symbols or missing_tests:
        decision = "EXTEND"
        reasons.append("capability implementation evidence exists but required contracts are incomplete")
    else:
        decision = "REUSE"
        reasons.append("all required capability contracts are present")
        if test_results and all(x["passed"] for x in test_results if x["executed"]):
            reasons.append("all executed required tests pass")

    evidence = {
        "schema_version": SCHEMA_VERSION,
        "capability_id": spec["capability_id"],
        "decision": decision,
        "build_required": decision == "BUILD",
        "reasons": reasons,
        "repository": {
            "path": str(repo),
            "branch": branch,
            "head": head,
            "worktree_clean": True,
        },
        "requirements": {
            "required_paths": required_paths,
            "required_symbols": required_symbols,
            "required_test_paths": test_results,
            "optional_paths": optional_paths,
            "missing_paths": missing_paths,
            "missing_symbols": missing_symbols,
            "missing_tests": missing_tests,
            "failing_tests": failing_tests,
            "hard_requirements": hard_requirements,
            "hard_present": hard_present,
        },
        "discovery": {
            "keyword_hits": keyword_hits,
            "history_hits": history,
            "implementation_evidence_count": implementation_evidence,
            "discovery_evidence_count": discovery_evidence,
        },
        "generated_at_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
    }
    return evidence


def _load_spec(args: argparse.Namespace) -> dict[str, Any]:
    if args.spec and args.spec_json:
        raise GateError("use either --spec or --spec-json, not both")
    if args.spec:
        return json.loads(Path(args.spec).read_text(encoding="utf-8"))
    if args.spec_json:
        return json.loads(args.spec_json)
    raise GateError("--spec or --spec-json is required")


def _write_output(path: str | None, data: dict[str, Any]) -> None:
    if not path:
        return
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="PROJECT PHOENIX Existing Capability + Reuse Gate v1.0"
    )
    p.add_argument("--repo", default=".", help="Phoenix repository path")
    p.add_argument("--spec", help="Capability-spec JSON file")
    p.add_argument("--spec-json", help="Capability-spec JSON string")
    p.add_argument("--output", help="Optional JSON evidence output path")
    p.add_argument(
        "--no-run-tests",
        action="store_true",
        help="Only inspect required test presence; do not execute tests",
    )
    p.add_argument(
        "--require-decision",
        choices=DECISIONS,
        help="Fail closed unless classification equals this decision",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        spec = _load_spec(args)
        evidence = classify(Path(args.repo), spec, run_tests=not args.no_run_tests)
        _write_output(args.output, evidence)

        print(f"EXISTING_CAPABILITY_GATE={evidence['decision']}")
        print(f"CAPABILITY_ID={evidence['capability_id']}")
        print(f"BUILD_REQUIRED={'YES' if evidence['build_required'] else 'NO'}")
        for reason in evidence["reasons"]:
            print(f"REASON={reason}")
        print(json.dumps(evidence, indent=2, sort_keys=True))

        if args.require_decision and evidence["decision"] != args.require_decision:
            print(
                f"GATE_BLOCKED=YES expected={args.require_decision} actual={evidence['decision']}",
                file=sys.stderr,
            )
            return DECISION_EXIT[evidence["decision"]]
        return 0
    except (GateError, OSError, json.JSONDecodeError) as exc:
        print("EXISTING_CAPABILITY_GATE=ERROR", file=sys.stderr)
        print(f"ERROR={exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
