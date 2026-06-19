from fastapi import FastAPI
from pydantic import BaseModel
from pathlib import Path
import json
import re
from datetime import datetime

app = FastAPI(title="BREWSTER ENGINEERING WIZARD API", version="1.2.0")
ROOT = Path(__file__).resolve().parents[1]

class ProjectRequest(BaseModel):
    project_name: str
    project_type: str
    location: str | None = None
    country: str | None = None
    description: str | None = None

def safe_slug(name: str) -> str:
    name = name.strip().replace(" ", "_")
    return re.sub(r"[^A-Za-z0-9_\\-]", "", name) or "project"

def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)

def write_json(path: Path, data: dict):
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def append_stee(project_name: str, source_type: str, source: str, purpose: str):
    stee_dir = ROOT / "stee"
    ensure_dir(stee_dir)
    csv_path = stee_dir / "bronnenregister.csv"
    if not csv_path.exists():
        csv_path.write_text("datum_tijd,project,bron_type,bron,doel,status\n", encoding="utf-8")
    line = f"{datetime.now().isoformat(timespec='seconds')},{project_name},{source_type},{source},{purpose},AANGEMAAKT\n"
    with csv_path.open("a", encoding="utf-8") as f:
        f.write(line)

def create_project_files(request: ProjectRequest):
    slug = safe_slug(request.project_name)
    project_dir = ROOT / "projects" / slug
    folders = [
        "00_input", "01_project_data", "02_digital_twin", "03_geotwin",
        "04_structural", "05_mep", "06_permit", "07_reports",
        "08_drawings", "09_exports", "10_stee", "11_sketchup", "12_archive"
    ]
    for folder in folders:
        ensure_dir(project_dir / folder)

    project_data = {
        "project_name": request.project_name,
        "project_type": request.project_type,
        "location": request.location,
        "country": request.country,
        "description": request.description,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "status": "AANGEMAAKT",
        "workflow": ["ADAE", "AAIE", "GECE", "Living Digital Twin"]
    }
    twin = {
        "digital_twin_id": f"DT-{slug}",
        "project_name": request.project_name,
        "status": "CONCEPT",
        "modules": {
            "architecture": "PENDING",
            "geotwin": "PENDING",
            "structural": "PENDING",
            "mep": "PENDING",
            "permit": "PENDING",
            "sketchup": "PENDING",
            "stee": "ACTIVE"
        },
        "parameters": [],
        "assumptions": [],
        "created_at": datetime.now().isoformat(timespec="seconds")
    }
    geotwin = {
        "project_name": request.project_name,
        "location": request.location,
        "country": request.country,
        "geo_mode": "Optie 1 - Grondwaterstand en geo-informatie automatisch genereren",
        "foundation_mode": "Optie 2 - Funderingstypen automatisch onderzoeken en vergelijken",
        "status": "PENDING_INPUT_OR_OPEN_DATA",
        "supported_sources": ["adres", "Google Maps", "satellietfoto", "dronefoto", "kaartuitsnede", "LiDAR", "BRO/AHN/PDOK waar beschikbaar"]
    }
    structural = {
        "project_name": request.project_name,
        "engine": "OpenSees + CalculiX + FreeCAD FEM + Structural Optimizer",
        "status": "PENDING_DIGITAL_TWIN",
        "default_outputs": ["belastingen", "reacties", "momenten", "dwarskrachten", "fundering", "wapening", "optimalisatie"]
    }
    stee_project = {
        "project_name": request.project_name,
        "source_traceability": "ACTIVE",
        "folder": "Bronvermelding_van_dit_project",
        "created_at": datetime.now().isoformat(timespec="seconds")
    }
    readme = f"""# {request.project_name}

Project aangemaakt door BREWSTER ENGINEERING WIZARD 1.2.

## Projectgegevens
- Projecttype: {request.project_type}
- Locatie: {request.location}
- Land/regio: {request.country}
- Omschrijving: {request.description}

## Workflow
ADAE -> AAIE -> GECE -> Living Digital Twin
"""
    write_json(project_dir / "01_project_data" / "project.json", project_data)
    write_json(project_dir / "02_digital_twin" / "digital_twin.json", twin)
    write_json(project_dir / "03_geotwin" / "geotwin.json", geotwin)
    write_json(project_dir / "04_structural" / "structural_model.json", structural)
    write_json(project_dir / "10_stee" / "stee_project.json", stee_project)
    (project_dir / "README.md").write_text(readme, encoding="utf-8")
    append_stee(request.project_name, "PROJECT", str(project_dir), "Projectmap en basisbestanden aangemaakt")
    return project_dir, project_data, twin

@app.get("/")
def root():
    return {
        "status": "BREWSTER ENGINEERING WIZARD runtime actief",
        "version": "1.2.0",
        "modules": ["Project Manager", "Living Digital Twin", "GeoTwin", "Structural Agent", "STEE"]
    }

@app.post("/projects/create")
def create_project(request: ProjectRequest):
    project_dir, project_data, twin = create_project_files(request)
    return {
        "message": "Project aangemaakt en opgeslagen",
        "project": project_data,
        "project_folder": str(project_dir),
        "digital_twin": twin,
        "next_step": "ADAE -> AAIE -> GECE -> Living Digital Twin"
    }

@app.get("/projects/list")
def list_projects():
    projects_dir = ROOT / "projects"
    ensure_dir(projects_dir)
    projects = []
    for p in projects_dir.iterdir():
        if p.is_dir():
            data_file = p / "01_project_data" / "project.json"
            if data_file.exists():
                projects.append(json.loads(data_file.read_text(encoding="utf-8")))
            else:
                projects.append({"project_name": p.name, "status": "UNKNOWN"})
    return {"projects": projects}

@app.get("/projects/{project_name}/twin")
def get_project_twin(project_name: str):
    twin_file = ROOT / "projects" / safe_slug(project_name) / "02_digital_twin" / "digital_twin.json"
    if not twin_file.exists():
        return {"error": "Digital Twin niet gevonden", "project_name": project_name}
    return json.loads(twin_file.read_text(encoding="utf-8"))

@app.get("/projects/{project_name}/geotwin")
def get_project_geotwin(project_name: str):
    geo_file = ROOT / "projects" / safe_slug(project_name) / "03_geotwin" / "geotwin.json"
    if not geo_file.exists():
        return {"error": "GeoTwin niet gevonden", "project_name": project_name}
    return json.loads(geo_file.read_text(encoding="utf-8"))

@app.get("/projects/{project_name}/structural")
def get_project_structural(project_name: str):
    structural_file = ROOT / "projects" / safe_slug(project_name) / "04_structural" / "structural_model.json"
    if not structural_file.exists():
        return {"error": "Structural model niet gevonden", "project_name": project_name}
    return json.loads(structural_file.read_text(encoding="utf-8"))
