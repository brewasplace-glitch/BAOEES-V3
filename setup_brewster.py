#!/usr/bin/env python3
"""
BREWSTER ENGINEERING WIZARD 1.0 - Auto Setup Script

Maakt automatisch een lokale repository-structuur voor BREWSTER ENGINEERING WIZARD.
Optioneel initialiseert het Git en koppelt het aan een bestaande GitHub repository.

Gebruik:
    python setup_brewster.py

Optioneel:
    python setup_brewster.py --project-dir "C:/BREWSTER/BREWSTER-ENGINEERING-WIZARD"
    python setup_brewster.py --github-url https://github.com/<user>/BREWSTER-ENGINEERING-WIZARD.git --push
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

PROJECT_NAME = "BREWSTER-ENGINEERING-WIZARD"

FOLDERS = [
    "docs",
    "core",
    "agents",
    "agents/architect_agent",
    "agents/structural_agent",
    "agents/geo_agent",
    "agents/mep_agent",
    "agents/infrastructure_agent",
    "agents/permit_agent",
    "agents/cost_agent",
    "agents/asset_agent",
    "digital_twin",
    "geotwin",
    "structural",
    "mep",
    "permit",
    "infrastructure",
    "sketchup",
    "reports",
    "stee",
    "runtime",
    "ui",
    "tests",
    "projects",
    "templates",
    "data",
    "exports",
]

README = """# BREWSTER ENGINEERING WIZARD 1.0

## Autonomous Open Engineering Ecosystem

BREWSTER ENGINEERING WIZARD is een autonoom engineeringplatform voor bouw, civiel, infra, gebiedsontwikkeling, Suriname, Nederland en de Nederlandse Cariben.

## Kernmodules

- Living Digital Twin
- Knowledge Graph
- Knowledge Vault
- Project Parameter Database
- ADAE – Autonomous Data Acquisition Engine
- AAIE – Autonomous Assumption & Inference Engine
- GECE – Global Environmental Compliance Engine
- Structural Agent: OpenSees + CalculiX + FreeCAD FEM
- Geo Agent
- MEP Agent
- Infrastructure Agent
- Permit Agent
- Cost Agent
- Asset Agent
- SketchUp Integration Module
- Unified Drawing Engine
- Production Engine
- STEE – Source Traceability & Evidence Engine
- Deployment & Storage Module

## Standaard output

Rapporten:
- PDF
- DOCX
- XLSX

Tekeningen/modellen:
- SKP
- DWG
- DXF
- IFC
- STEP
- FreeCAD
- OpenSees
- CalculiX

## Deployment standaard

- Lokaal
- Eigen opslag
- NAS optioneel
- Cloud-backup optioneel
"""

ARCHITECTURE = """# BREWSTER ENGINEERING WIZARD 1.0 – Architectuur

## BREWSTER Core

```text
BREWSTER Core
├── Living Digital Twin
├── Knowledge Graph
├── Knowledge Vault
├── Project Parameter Database
├── ADAE
├── AAIE
├── GECE
├── Architect Agent
├── Structural Agent
├── Geo Agent
├── MEP Agent
├── Infrastructure Agent
├── Permit Agent
├── Cost Agent
├── Asset Agent
├── AI Design Review Board
├── Unified Drawing Engine
├── Production Engine
├── SketchUp Integration Module
├── STEE
├── Deployment & Storage Module
└── Runtime Manager
```

## Workflow

```text
Projectinvoer
↓
ADAE – Data verzamelen
↓
AAIE – Ontbrekende data aanvullen
↓
GECE – Regelgeving en milieu bepalen
↓
Living Digital Twin
↓
Autonomous Engineering Agents
↓
AI Design Review Board
↓
Production Engine
↓
Definitieve deliverables
```

## Status van data

- AANNAME
- GEACTUALISEERD
- BEVESTIGD

## Standaard landen

- Nederland
- Suriname
- Nederlandse Cariben
- Ander land via invoerveld
"""

ROADMAP = """# Roadmap

## V1.0 – Basisstructuur
- Repository structuur
- Documentatie
- Project Parameter Database concept
- STEE basis
- Local Runtime Mode

## V1.1 – Project Wizard
- Projectinvoer
- Projecttype
- Land/regio
- Outputselectie

## V1.2 – Living Digital Twin
- Projectmodel
- Objectenmodel
- Twin status

## V1.3 – Structural Agent
- OpenSees basis
- CalculiX basis
- FreeCAD FEM koppeling

## V1.4 – SketchUp Integration Module
- Lagenstructuur
- Componenten
- SKP-compatible package

## V2.0 – Autonomous Production Engine
- PDF/DOCX rapporten
- DXF/IFC/SKP-compatible modellen
- Project ZIP
"""

GITIGNORE = """# Python
__pycache__/
*.pyc
.venv/
venv/
.env

# Node
node_modules/
.next/
dist/
build/

# OS
.DS_Store
Thumbs.db

# BREWSTER generated output
projects/*/exports/
projects/*/temp/
exports/
*.zip
"""

PYPROJECT = """[project]
name = "brewster-engineering-wizard"
version = "0.1.0"
description = "BREWSTER ENGINEERING WIZARD 1.0 prototype"
requires-python = ">=3.10"
dependencies = [
    "fastapi",
    "uvicorn",
    "pydantic",
    "python-docx",
    "reportlab",
]
"""

MAIN_PY = """from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="BREWSTER ENGINEERING WIZARD API")

class ProjectRequest(BaseModel):
    project_name: str
    project_type: str
    location: str | None = None
    country: str | None = None
    description: str | None = None

@app.get("/")
def root():
    return {"status": "BREWSTER ENGINEERING WIZARD runtime actief"}

@app.post("/projects/create")
def create_project(request: ProjectRequest):
    return {
        "message": "Project aangemaakt",
        "project": request.model_dump(),
        "next_step": "ADAE -> AAIE -> GECE -> Living Digital Twin",
    }
"""

STEE_TEMPLATE = """bron_id,bron_type,naam,url,bestand,datum_tijd,doel,status
1,SYSTEEM,Setup Script,,setup_brewster.py,{timestamp},Initiële projectstructuur,BEVESTIGD
"""

CONFIG = {
    "product": "BREWSTER ENGINEERING WIZARD",
    "version": "1.0",
    "deployment_mode": "local",
    "storage": {
        "local": True,
        "nas": False,
        "cloud_backup": False,
    },
    "default_countries": ["Nederland", "Suriname", "Nederlandse Cariben"],
    "data_statuses": ["AANNAME", "GEACTUALISEERD", "BEVESTIGD"],
    "standard_report_output": ["PDF", "DOCX", "XLSX"],
    "standard_drawing_output": ["SKP", "DWG", "DXF", "IFC", "STEP"],
}


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("$", " ".join(cmd))
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


def write_file(path: Path, content: str, overwrite: bool = False) -> None:
    if path.exists() and not overwrite:
        print(f"Bestaat al, overslaan: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"Aangemaakt: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Maak BREWSTER ENGINEERING WIZARD repository structuur")
    parser.add_argument("--project-dir", default=PROJECT_NAME, help="Doelmap voor project")
    parser.add_argument("--github-url", default="", help="GitHub remote URL, bijvoorbeeld https://github.com/user/repo.git")
    parser.add_argument("--push", action="store_true", help="Commit en push naar GitHub")
    parser.add_argument("--overwrite", action="store_true", help="Overschrijf bestaande basisbestanden")
    args = parser.parse_args()

    root = Path(args.project_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)

    for folder in FOLDERS:
        (root / folder).mkdir(parents=True, exist_ok=True)
        print(f"Map gereed: {root / folder}")

    write_file(root / "README.md", README, args.overwrite)
    write_file(root / "docs" / "Architecture.md", ARCHITECTURE, args.overwrite)
    write_file(root / "docs" / "Roadmap.md", ROADMAP, args.overwrite)
    write_file(root / ".gitignore", GITIGNORE, args.overwrite)
    write_file(root / "pyproject.toml", PYPROJECT, args.overwrite)
    write_file(root / "runtime" / "main.py", MAIN_PY, args.overwrite)
    write_file(root / "config.json", json.dumps(CONFIG, indent=2, ensure_ascii=False), args.overwrite)
    write_file(root / "stee" / "bronnenregister.csv", STEE_TEMPLATE.format(timestamp=datetime.now().isoformat(timespec="seconds")), args.overwrite)

    # Keep empty folders in git
    for folder in FOLDERS:
        keep = root / folder / ".gitkeep"
        if not keep.exists():
            keep.write_text("", encoding="utf-8")

    # Git init
    if not (root / ".git").exists():
        try:
            run(["git", "init"], cwd=root)
        except Exception as exc:
            print(f"Git init niet uitgevoerd: {exc}")

    if args.github_url:
        try:
            remotes = subprocess.run(["git", "remote"], cwd=str(root), capture_output=True, text=True, check=True).stdout
            if "origin" not in remotes.split():
                run(["git", "remote", "add", "origin", args.github_url], cwd=root)
            else:
                run(["git", "remote", "set-url", "origin", args.github_url], cwd=root)
        except Exception as exc:
            print(f"Git remote niet ingesteld: {exc}")

    try:
        run(["git", "add", "."], cwd=root)
        run(["git", "commit", "-m", "Initial BREWSTER ENGINEERING WIZARD structure"], cwd=root)
    except Exception as exc:
        print(f"Git commit overgeslagen of mislukt: {exc}")

    if args.push:
        if not args.github_url:
            print("Gebruik --github-url voordat je --push gebruikt.")
        else:
            try:
                run(["git", "branch", "-M", "main"], cwd=root)
                run(["git", "push", "-u", "origin", "main"], cwd=root)
            except Exception as exc:
                print(f"Git push mislukt: {exc}")

    print("\nKLAAR: BREWSTER ENGINEERING WIZARD setup is aangemaakt.")
    print(f"Projectmap: {root}")
    print("Start API later met: uvicorn runtime.main:app --reload")


if __name__ == "__main__":
    main()
