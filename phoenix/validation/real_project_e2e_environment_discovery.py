
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

TOOL_RULES = {
    "freecad": {
        "glob": ("FreeCADCmd.exe", "FreeCAD.exe", "FreeCADCmd", "FreeCAD"),
        "basename_rx": re.compile(r"(?i)^freecad(?:cmd)?(?:\.exe)?$"),
        "version_args": ("--version",),
    },
    "blender": {
        "glob": ("blender.exe", "blender"),
        "basename_rx": re.compile(r"(?i)^blender(?:\.exe)?$"),
        "version_args": ("--version",),
    },
    "calculix": {
        "glob": ("ccx.exe", "ccx_*.exe", "ccx"),
        "basename_rx": re.compile(r"(?i)^ccx(?:_[0-9A-Za-z.\-]+)?(?:\.exe)?$"),
        "version_args": ("-v",),
    },
}

def is_tool_binary(tool: str, path: Path) -> bool:
    return bool(TOOL_RULES[tool]["basename_rx"].match(path.name))

def unique_tool_paths(tool: str, paths):
    seen = set()
    out = []
    for raw in paths:
        p = Path(raw)
        if not p.exists() or not p.is_file() or not is_tool_binary(tool, p):
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

def path_candidates(tool: str):
    out = []
    for name in TOOL_RULES[tool]["glob"]:
        hit = shutil.which(name)
        if hit:
            out.append(Path(hit))
    return out

def repo_candidates(repo: Path, tool: str):
    out = []
    roots = [repo / "tools", repo / "vendor", repo / "engines", repo / "apps", repo / "phoenix"]
    for root in roots:
        if not root.exists():
            continue
        for pattern in TOOL_RULES[tool]["glob"]:
            try:
                out.extend(p for p in root.rglob(pattern) if p.is_file() and is_tool_binary(tool, p))
            except OSError:
                pass
    return out

def common_windows_candidates(tool: str):
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
            for candidate_root in (base, base / "bin"):
                if not candidate_root.exists():
                    continue
                for pattern in TOOL_RULES[tool]["glob"]:
                    try:
                        out.extend(
                            p for p in candidate_root.glob(pattern)
                            if p.is_file() and is_tool_binary(tool, p)
                        )
                    except OSError:
                        pass
    return out

def configured_candidates(repo: Path, tool: str):
    # Extract Windows executable paths, but attribute them only if the executable
    # basename itself matches the requested tool. Keyword proximity alone is forbidden.
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
            for match in path_rx.findall(text):
                candidate = Path(match.replace("\\\\", "\\"))
                if candidate.exists() and is_tool_binary(tool, candidate):
                    out.append(candidate)
    return out

def version_probe(tool: str, executable: str):
    args = list(TOOL_RULES[tool]["version_args"])
    try:
        cp = subprocess.run(
            [executable] + args,
            text=True,
            capture_output=True,
            timeout=8,
        )
        text = (cp.stdout + cp.stderr).strip()
        # Some native tools use non-zero status for informational version output.
        return {
            "attempted": True,
            "exit_code": cp.returncode,
            "output": text[:500],
        }
    except Exception as exc:
        return {"attempted": True, "exit_code": 127, "output": str(exc)[:500]}

def detect_tool(repo: Path, tool: str):
    paths = []
    paths.extend(path_candidates(tool))
    paths.extend(repo_candidates(repo, tool))
    paths.extend(common_windows_candidates(tool))
    paths.extend(configured_candidates(repo, tool))
    paths = unique_tool_paths(tool, paths)

    probes = {p: version_probe(tool, p) for p in paths}
    return {
        "available": bool(paths),
        "paths": paths,
        "preferred": paths[0] if paths else "",
        "version_probes": probes,
        "strict_basename_attribution": True,
    }

def detect_browser_backends(repo: Path):
    playwright_py = importlib.util.find_spec("playwright") is not None
    selenium_py = importlib.util.find_spec("selenium") is not None

    playwright_cli = []
    for base in (repo, Path.cwd()):
        for rel in (Path("node_modules/.bin/playwright.cmd"), Path("node_modules/.bin/playwright")):
            p = base / rel
            if p.exists():
                playwright_cli.append(str(p.resolve()))

    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if npm:
        try:
            cp = subprocess.run([npm, "root", "-g"], cwd=repo, text=True, capture_output=True, timeout=8)
            if cp.returncode == 0:
                root = Path(cp.stdout.strip())
                for rel in (Path("playwright/cli.js"), Path("playwright-core/cli.js")):
                    p = root / rel
                    if p.exists():
                        playwright_cli.append(str(p.resolve()))
        except Exception:
            pass

    return {
        "playwright_primary": {
            "available": bool(playwright_py or playwright_cli),
            "python_module": playwright_py,
            "cli_paths": list(dict.fromkeys(playwright_cli)),
            "network_fetch_attempted": False,
        },
        "selenium_fallback": {
            "available": bool(selenium_py),
            "python_module": selenium_py,
        },
    }

def project_identity(path: Path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    identity = data.get("identity") if isinstance(data.get("identity"), dict) else {}
    pid = str(data.get("project_id") or identity.get("project_id") or path.stem)
    name = str(data.get("name") or identity.get("name") or pid)
    return pid, name

def classify_projects(repo: Path):
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

    return {
        "all_config_count": len(list((repo / "configs" / "projects").glob("*.json"))),
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
        "tools": {tool: detect_tool(repo, tool) for tool in ("freecad", "blender", "calculix")},
        "projects": classify_projects(repo),
        "release": {"production": "LOCKED", "for_construction": "LOCKED"},
    }

    if ns.json_out:
        out = Path(ns.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    print("E2E_RUNTIME_DISCOVERY=PASS")
    print("STRICT_TOOL_PATH_ATTRIBUTION=PASS")
    print("PLAYWRIGHT_PRIMARY=" + ("AVAILABLE" if result["browser_evidence"]["playwright_primary"]["available"] else "NOT_DETECTED"))
    print("PLAYWRIGHT_NETWORK_FETCH_ATTEMPTED=NO")
    print("SELENIUM_FALLBACK=" + ("AVAILABLE" if result["browser_evidence"]["selenium_fallback"]["available"] else "NOT_DETECTED"))

    for tool in ("freecad", "blender", "calculix"):
        info = result["tools"][tool]
        print(tool.upper() + "=" + ("AVAILABLE" if info["available"] else "NOT_DETECTED"))
        if info["preferred"]:
            print(tool.upper() + "_PREFERRED=" + info["preferred"])
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
