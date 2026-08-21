
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

TOOL_PATTERNS = {
    "freecad": ("FreeCADCmd.exe", "FreeCAD.exe", "FreeCADCmd", "FreeCAD"),
    "blender": ("blender.exe", "blender"),
    "calculix": ("ccx.exe", "ccx_*.exe", "ccx"),
}

def unique_existing(paths):
    seen = set()
    out = []
    for p in paths:
        p = Path(p)
        if not p.exists():
            continue
        try:
            rp = p.resolve()
        except Exception:
            rp = p
        key = str(rp).lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(str(rp))
    return out

def command_candidates(names):
    out = []
    for name in names:
        hit = shutil.which(name)
        if hit:
            out.append(Path(hit))
    return out

def repo_candidates(repo, patterns):
    out = []
    search_roots = [
        repo / "tools",
        repo / "vendor",
        repo / "engines",
        repo / "apps",
        repo / "phoenix",
        repo / "runners",
    ]
    for root in search_roots:
        if not root.exists():
            continue
        for pattern in patterns:
            try:
                out.extend(p for p in root.rglob(pattern) if p.is_file())
            except OSError:
                pass
    return out

def common_windows_candidates(patterns):
    if os.name != "nt":
        return []
    roots = []
    for env_name in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        value = os.environ.get(env_name)
        if value:
            roots.append(Path(value))
    roots.extend([Path(r"C:\CalculiX"), Path(r"C:\FreeCAD"), Path(r"C:\Blender")])

    out = []
    for root in roots:
        if not root.exists():
            continue
        bases = [root]
        try:
            bases.extend(p for p in root.iterdir() if p.is_dir())
        except OSError:
            pass
        for base in bases:
            for child in (base, base / "bin"):
                if not child.exists():
                    continue
                for pattern in patterns:
                    try:
                        out.extend(p for p in child.glob(pattern) if p.is_file())
                    except OSError:
                        pass
    return out

def configured_path_candidates(repo, tool):
    keywords = {
        "freecad": ("freecadcmd", "freecad.exe", "freecad"),
        "blender": ("blender.exe", "blender"),
        "calculix": ("ccx.exe", "ccx_", "calculix"),
    }[tool]
    path_rx = re.compile(r'(?i)([A-Z]:[\\/][^"\'`\r\n]+?\.(?:exe|cmd|bat))')
    out = []
    for suffix in ("*.json", "*.ps1", "*.py", "*.md", "*.txt"):
        for path in repo.rglob(suffix):
            low_parts = {part.lower() for part in path.parts}
            if ".git" in low_parts or "__pycache__" in low_parts:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            low = text.lower()
            if not any(k in low for k in keywords):
                continue
            for match in path_rx.findall(text):
                candidate = Path(match.replace("\\\\", "\\"))
                if candidate.exists():
                    out.append(candidate)
    return out

def detect_tool(repo, tool):
    patterns = TOOL_PATTERNS[tool]
    found = []
    found.extend(command_candidates(patterns))
    found.extend(repo_candidates(repo, patterns))
    found.extend(common_windows_candidates(patterns))
    found.extend(configured_path_candidates(repo, tool))
    paths = unique_existing(found)
    return {
        "available": bool(paths),
        "paths": paths,
        "preferred": paths[0] if paths else "",
    }

def detect_browser_backends(repo):
    playwright_py = importlib.util.find_spec("playwright") is not None
    selenium_py = importlib.util.find_spec("selenium") is not None

    playwright_cli = []
    for base in (repo, Path.cwd()):
        for rel in (
            Path("node_modules/.bin/playwright.cmd"),
            Path("node_modules/.bin/playwright"),
        ):
            p = base / rel
            if p.exists():
                playwright_cli.append(str(p.resolve()))

    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if npm:
        try:
            cp = subprocess.run(
                [npm, "root", "-g"],
                cwd=repo,
                text=True,
                capture_output=True,
                timeout=8,
            )
            if cp.returncode == 0:
                root = Path(cp.stdout.strip())
                for rel in (Path("playwright/cli.js"), Path("playwright-core/cli.js")):
                    p = root / rel
                    if p.exists():
                        playwright_cli.append(str(p.resolve()))
        except Exception:
            pass

    playwright_cli = list(dict.fromkeys(playwright_cli))
    return {
        "playwright_primary": {
            "available": bool(playwright_py or playwright_cli),
            "python_module": playwright_py,
            "cli_paths": playwright_cli,
            "network_fetch_attempted": False,
        },
        "selenium_fallback": {
            "available": bool(selenium_py),
            "python_module": selenium_py,
        },
    }

def project_identity(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    identity = data.get("identity") if isinstance(data.get("identity"), dict) else {}
    pid = str(data.get("project_id") or identity.get("project_id") or path.stem)
    name = str(data.get("name") or identity.get("name") or pid)
    return pid, name

def classify_projects(repo):
    real_roots = []
    for filename in ("bruynzeel_waterfront.json", "moskee_bunschoten.json", "plutostraat.json"):
        path = repo / "configs" / "projects" / filename
        if path.exists():
            pid, name = project_identity(path)
            real_roots.append({
                "project_id": pid,
                "name": name,
                "file": path.relative_to(repo).as_posix(),
                "classification": "canonical_real_project_root",
            })

    pilots = []
    for path in sorted((repo / "configs" / "projects").glob("*.json")):
        pid, name = project_identity(path)
        token = f"{pid} {path.name}".lower()
        if "pat001" in token or "phoenix-pat-001" in token:
            pilots.append({
                "project_id": pid,
                "name": name,
                "file": path.relative_to(repo).as_posix(),
                "classification": "pilot_or_validation_project",
            })

    total = len(list((repo / "configs" / "projects").glob("*.json")))
    return {
        "all_config_count": total,
        "real_root_candidates": real_roots,
        "pilot_candidates": pilots,
        "selection_required": True,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--json-out")
    ns = ap.parse_args()

    repo = Path(ns.repo).resolve()
    result = {
        "browser_evidence": detect_browser_backends(repo),
        "tools": {
            "freecad": detect_tool(repo, "freecad"),
            "blender": detect_tool(repo, "blender"),
            "calculix": detect_tool(repo, "calculix"),
        },
        "projects": classify_projects(repo),
        "release": {"production": "LOCKED", "for_construction": "LOCKED"},
    }

    if ns.json_out:
        out = Path(ns.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    print("E2E_RUNTIME_DISCOVERY=PASS")
    pw = result["browser_evidence"]["playwright_primary"]
    se = result["browser_evidence"]["selenium_fallback"]
    print("PLAYWRIGHT_PRIMARY=" + ("AVAILABLE" if pw["available"] else "NOT_DETECTED"))
    print("PLAYWRIGHT_NETWORK_FETCH_ATTEMPTED=NO")
    print("SELENIUM_FALLBACK=" + ("AVAILABLE" if se["available"] else "NOT_DETECTED"))

    for tool in ("freecad", "blender", "calculix"):
        info = result["tools"][tool]
        print(tool.upper() + "=" + ("AVAILABLE" if info["available"] else "NOT_DETECTED"))
        for path in info["paths"]:
            print(tool.upper() + "_PATH=" + path)

    projects = result["projects"]
    print(f"PROJECT_CONFIGS_TOTAL={projects['all_config_count']}")
    print(f"REAL_ROOT_CANDIDATES={len(projects['real_root_candidates'])}")
    for p in projects["real_root_candidates"]:
        print(f"REAL_ROOT_CANDIDATE={p['project_id']} | {p['name']} | {p['file']}")
    for p in projects["pilot_candidates"]:
        print(f"PILOT_CANDIDATE={p['project_id']} | {p['file']}")
    print("REAL_PROJECT_SELECTION=REQUIRED")
    print("PRODUCTION_RELEASE=LOCKED")
    print("FOR_CONSTRUCTION=LOCKED")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
