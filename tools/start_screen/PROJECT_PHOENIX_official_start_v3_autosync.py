#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, json, re, subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ENGINE_ID = "PHX-OFFICIAL-START-SCREEN-V3-AUTOSYNC"
VERSION = "3.0.0"
VERSION_RE = re.compile(r"v?(?P<major>\d+)[._](?P<minor>\d+)(?:[._](?P<patch>\d+))?", re.I)

def _version_tuple(text: str) -> Tuple[int, int, int]:
    m = VERSION_RE.search(text or "")
    if not m:
        return (0, 0, 0)
    return int(m.group("major")), int(m.group("minor")), int(m.group("patch") or 0)

def _version_text(t: Tuple[int, int, int]) -> str:
    return f"v{t[0]}.{t[1]}.{t[2]}"

def _run_git(repo: Path, *args: str):
    p = subprocess.run(["git", *args], cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout.strip()

def _safe_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else None
    except Exception:
        return None

def _category(text: str) -> str:
    s = text.lower()
    if "struct" in s or "foundation" in s: return "STRUCTURAL"
    if "architect" in s or "bim" in s or "drawing" in s: return "ARCHITECTURAL"
    if "permit" in s or "aerius" in s or "particip" in s: return "PERMITS"
    if "parking" in s or "traffic" in s or "infra" in s: return "INFRA"
    if "geo" in s or "soil" in s: return "GEOTECHNICAL"
    if "digital_twin" in s or "digital-twin" in s: return "DIGITAL_TWIN"
    if "release" in s or "qaqc" in s or "qa_qc" in s: return "RELEASE_QAQC"
    if "core" in s or "runtime" in s or "workflow" in s: return "CORE"
    return "OTHER"

def discover_engines(repo: Path) -> List[Dict[str, Any]]:
    files: List[Path] = []
    for base in [repo / "configs" / "phoenix", repo / "configs" / "projects"]:
        if base.is_dir():
            files.extend(base.rglob("*.json"))
    runners = repo / "runners"
    if runners.is_dir():
        files.extend(runners.glob("*.py"))

    result: Dict[str, Dict[str, Any]] = {}
    for path in files:
        rel = path.relative_to(repo).as_posix()
        data = _safe_json(path) if path.suffix.lower() == ".json" else None
        engine_id = str((data or {}).get("engine_id") or (data or {}).get("id") or "").strip()
        title = str((data or {}).get("name") or (data or {}).get("title") or "").strip()
        explicit_version = str((data or {}).get("version") or "").strip()
        vt = _version_tuple(explicit_version or path.stem)
        if vt == (0, 0, 0):
            continue
        item = {
            "engine_id": engine_id or path.stem,
            "name": title or path.stem.replace("_", " "),
            "version": _version_text(vt),
            "version_tuple": list(vt),
            "category": _category(" ".join([rel, engine_id, title])),
            "source": rel,
        }
        key = engine_id or f"{item['category']}::{path.stem.lower()}"
        old = result.get(key)
        if old is None or tuple(item["version_tuple"]) > tuple(old["version_tuple"]):
            result[key] = item
    items = list(result.values())
    items.sort(key=lambda x: (x["category"], tuple(-n for n in x["version_tuple"]), x["name"].lower()))
    return items

def structural_chain(engines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_version = {}
    for e in engines:
        if e["category"] != "STRUCTURAL":
            continue
        vt = tuple(int(n) for n in e["version_tuple"])
        if vt[0] != 8:
            continue
        by_version[vt] = {"version": _version_text(vt), "name": e["name"], "engine_id": e["engine_id"]}
    return [by_version[k] for k in sorted(by_version)]

def repo_status(repo: Path) -> Dict[str, Any]:
    rc, branch = _run_git(repo, "branch", "--show-current")
    branch = branch if rc == 0 else "UNKNOWN"
    rc, status = _run_git(repo, "status", "--porcelain=v1", "--untracked-files=normal")
    clean = rc == 0 and status == ""
    rc, head = _run_git(repo, "rev-parse", "--short=12", "HEAD")
    head = head if rc == 0 else "UNKNOWN"
    rc, subject = _run_git(repo, "log", "-1", "--pretty=%s")
    subject = subject if rc == 0 else "UNKNOWN"
    rl, local = _run_git(repo, "rev-parse", "HEAD")
    rr, remote = _run_git(repo, "rev-parse", f"origin/{branch}") if branch != "UNKNOWN" else (1, "")
    return {
        "branch": branch,
        "clean": clean,
        "head": head,
        "head_subject": subject,
        "local_remote_synchronized": rl == 0 and rr == 0 and bool(local) and local == remote,
    }

def load_policy(repo: Path) -> Dict[str, Any]:
    p = repo / "configs" / "phoenix" / "official_start_screen_v3_policy.json"
    data = _safe_json(p)
    return data or {
        "production_acceptance_test_status": "PENDING_REAL_PROJECT_END_TO_END_PRODUCTION_ACCEPTANCE_TEST",
        "production_release": "LOCKED_PENDING_PAT",
    }

def build_registry(repo: Path) -> Dict[str, Any]:
    engines = discover_engines(repo)
    chain = structural_chain(engines)
    policy = load_policy(repo)
    categories: Dict[str, int] = {}
    for e in engines:
        categories[e["category"]] = categories.get(e["category"], 0) + 1
    latest_structural = chain[-1]["version"] if chain else None
    return {
        "schema": "project-phoenix/official-start-v3/autosync",
        "engine_id": ENGINE_ID,
        "engine_version": VERSION,
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "phoenix": {"major_line": "Phoenix 3.0", "official_start_screen": "official_start_v3_0"},
        "repository": repo_status(repo),
        "product_status": {
            "building_structural_candidate": "READY_FOR_PRODUCTION_ACCEPTANCE_TEST",
            "structural_chain_closed_through": latest_structural,
            "production_acceptance_test": policy.get("production_acceptance_test_status", "PENDING"),
            "production_release": policy.get("production_release", "LOCKED_PENDING_PAT"),
        },
        "automation": {
            "start_screen_autosync": "ACTIVE",
            "auto_refresh_on_official_start": True,
            "future_module_discovery": "AUTOMATIC",
            "manual_dashboard_registration_required": False,
        },
        "summary": {"engine_count": len(engines), "category_counts": categories, "structural_chain_count": len(chain)},
        "structural_chain": chain,
        "engines": engines,
    }

def write_registry(repo: Path, output: Optional[Path] = None) -> Path:
    out = output or (repo / "phoenix" / "local_app" / "static" / "official_start_v3_0" / "phoenix_start_screen_runtime.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(build_registry(repo), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--output")
    ap.add_argument("--print-json", action="store_true")
    args = ap.parse_args()
    repo = Path(args.repo).resolve()
    if not (repo / ".git").exists():
        raise SystemExit(f"Not a git repository: {repo}")
    out = write_registry(repo, Path(args.output).resolve() if args.output else None)
    if args.print_json:
        print(out.read_text(encoding="utf-8"), end="")
    else:
        print(f"PHOENIX OFFICIAL START v3 AUTOSYNC: PASSED -> {out}")

if __name__ == "__main__":
    main()
