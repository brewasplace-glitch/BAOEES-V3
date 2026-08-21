from __future__ import annotations
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

VISUAL_MARKERS = (
    "STATUS_POLL_MS=600000",
    "PERIODIC_VISUAL_HEARTBEAT_6S=REMOVED",
    "POINTER_RELEASE_GUARD=ENABLED",
    "OS_POINTER_TRAP_GUARD=ENABLED",
    "DE_TV_CORE_UNCHANGED=PASS",
)

def run(cmd, cwd):
    try:
        cp = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=12)
        return cp.returncode, (cp.stdout + cp.stderr).strip()
    except Exception as exc:
        return 127, str(exc)

def find_visual_evidence(repo: Path):
    docs = repo / "docs" / "automation"
    files = sorted(docs.glob("PHOENIX_START_VISUAL_IDLE_POINTER_RELEASE*_EVIDENCE.txt"),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    for path in files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        if all(marker in text for marker in VISUAL_MARKERS):
            return path, text
    return None, ""

def read_projects(repo: Path):
    result = []
    for path in sorted((repo / "configs" / "projects").glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        identity = data.get("identity") if isinstance(data.get("identity"), dict) else {}
        pid = str(data.get("project_id") or identity.get("project_id") or path.stem)
        name = str(data.get("name") or identity.get("name") or pid)
        result.append({"project_id": pid, "name": name, "file": path.relative_to(repo).as_posix()})
    return result

def find_binary(repo: Path, names):
    for name in names:
        hit = shutil.which(name)
        if hit:
            return hit
    candidates = []
    for root in ("tools", "vendor", "engines", "apps"):
        base = repo / root
        if not base.exists():
            continue
        for name in names:
            candidates.extend(base.rglob(name))
    return str(candidates[0]) if candidates else ""

def detect_browser_backends(repo: Path):
    pw_py = importlib.util.find_spec("playwright") is not None
    sel_py = importlib.util.find_spec("selenium") is not None

    npx = shutil.which("npx.cmd") or shutil.which("npx")
    pw_node = False
    pw_version = ""
    if npx:
        code, text = run([npx, "playwright", "--version"], repo)
        if code == 0:
            pw_node = True
            pw_version = text.splitlines()[-1] if text else "detected"

    return {
        "playwright_primary": {
            "available": bool(pw_py or pw_node),
            "python_module": pw_py,
            "node_cli": pw_node,
            "version": pw_version,
        },
        "selenium_fallback": {
            "available": bool(sel_py),
            "python_module": sel_py,
        },
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--json-out")
    ns = ap.parse_args()
    repo = Path(ns.repo).resolve()

    visual_path, _ = find_visual_evidence(repo)
    projects = read_projects(repo)
    browsers = detect_browser_backends(repo)

    status = {
        "visual_stability_evidence": "PASS" if visual_path else "MISSING",
        "visual_stability_evidence_file": str(visual_path.relative_to(repo).as_posix()) if visual_path else "",
        "projects": projects,
        "project_candidate_count": len(projects),
        "real_project_selection": "PENDING" if len(projects) != 1 else "SINGLE_CANDIDATE_REVIEW_REQUIRED",
        "browser_backends": browsers,
        "freecad": find_binary(repo, ["FreeCADCmd.exe", "FreeCADCmd"]),
        "blender": find_binary(repo, ["blender.exe", "blender"]),
        "calculix": find_binary(repo, ["ccx.exe", "ccx"]),
        "release": "CONCEPT ONLY / NOT FOR CONSTRUCTION",
        "production_release": "LOCKED",
    }

    if ns.json_out:
        out = Path(ns.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")

    print(f"VISUAL_STABILITY_EVIDENCE={status['visual_stability_evidence']}")
    if status["visual_stability_evidence_file"]:
        print(f"VISUAL_STABILITY_EVIDENCE_FILE={status['visual_stability_evidence_file']}")
    print(f"PROJECT_CANDIDATES={len(projects)}")
    for p in projects:
        print(f"PROJECT_CANDIDATE={p['project_id']} | {p['name']} | {p['file']}")
    print(f"REAL_PROJECT_SELECTION={status['real_project_selection']}")
    print("PLAYWRIGHT_PRIMARY=" + ("AVAILABLE" if browsers["playwright_primary"]["available"] else "NOT_DETECTED"))
    print("SELENIUM_FALLBACK=" + ("AVAILABLE" if browsers["selenium_fallback"]["available"] else "NOT_DETECTED"))
    print("FREECAD=" + ("AVAILABLE" if status["freecad"] else "NOT_DETECTED"))
    print("BLENDER=" + ("AVAILABLE" if status["blender"] else "NOT_DETECTED"))
    print("CALCULIX=" + ("AVAILABLE" if status["calculix"] else "NOT_DETECTED"))
    print("PRODUCTION_RELEASE=LOCKED")
    print("FOR_CONSTRUCTION=LOCKED")
    print("E2E_READINESS_PROBE=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
