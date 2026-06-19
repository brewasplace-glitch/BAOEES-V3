from pathlib import Path
import csv
from datetime import datetime

ROOT = Path(__file__).resolve().parent

MAIN_PY = 'from fastapi import FastAPI\nfrom pydantic import BaseModel\nfrom pathlib import Path\nimport json\nimport re\nfrom datetime import datetime\n\napp = FastAPI(title="BREWSTER ENGINEERING WIZARD API", version="1.2.0")\nROOT = Path(__file__).resolve().parents[1]\n\nclass ProjectRequest(BaseModel):\n    project_name: str\n    project_type: str\n    location: str | None = None\n    country: str | None = None\n    description: str | None = None\n\ndef safe_slug(name: str) -> str:\n    name = name.strip().replace(" ", "_")\n    return re.sub(r"[^A-Za-z0-9_\\\\-]", "", name) or "project"\n\ndef ensure_dir(path: Path):\n    path.mkdir(parents=True, exist_ok=True)\n\ndef write_json(path: Path, data: dict):\n    ensure_dir(path.parent)\n    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")\n\ndef append_stee(project_name: str, source_type: str, source: str, purpose: str):\n    stee_dir = ROOT / "stee"\n    ensure_dir(stee_dir)\n    csv_path = stee_dir / "bronnenregister.csv"\n    if not csv_path.exists():\n        csv_path.write_text("datum_tijd,project,bron_type,bron,doel,status\\n", encoding="utf-8")\n    line = f"{datetime.now().isoformat(timespec=\'seconds\')},{project_name},{source_type},{source},{purpose},AANGEMAAKT\\n"\n    with csv_path.open("a", encoding="utf-8") as f:\n        f.write(line)\n\ndef create_project_files(request: ProjectRequest):\n    slug = safe_slug(request.project_name)\n    project_dir = ROOT / "projects" / slug\n    folders = [\n        "00_input", "01_project_data", "02_digital_twin", "03_geotwin",\n        "04_structural", "05_mep", "06_permit", "07_reports",\n        "08_drawings", "09_exports", "10_stee", "11_sketchup", "12_archive"\n    ]\n    for folder in folders:\n        ensure_dir(project_dir / folder)\n\n    project_data = {\n        "project_name": request.project_name,\n        "project_type": request.project_type,\n        "location": request.location,\n        "country": request.country,\n        "description": request.description,\n        "created_at": datetime.now().isoformat(timespec="seconds"),\n        "status": "AANGEMAAKT",\n        "workflow": ["ADAE", "AAIE", "GECE", "Living Digital Twin"]\n    }\n    twin = {\n        "digital_twin_id": f"DT-{slug}",\n        "project_name": request.project_name,\n        "status": "CONCEPT",\n        "modules": {\n            "architecture": "PENDING",\n            "geotwin": "PENDING",\n            "structural": "PENDING",\n            "mep": "PENDING",\n            "permit": "PENDING",\n            "sketchup": "PENDING",\n            "stee": "ACTIVE"\n        },\n        "parameters": [],\n        "assumptions": [],\n        "created_at": datetime.now().isoformat(timespec="seconds")\n    }\n    geotwin = {\n        "project_name": request.project_name,\n        "location": request.location,\n        "country": request.country,\n        "geo_mode": "Optie 1 - Grondwaterstand en geo-informatie automatisch genereren",\n        "foundation_mode": "Optie 2 - Funderingstypen automatisch onderzoeken en vergelijken",\n        "status": "PENDING_INPUT_OR_OPEN_DATA",\n        "supported_sources": ["adres", "Google Maps", "satellietfoto", "dronefoto", "kaartuitsnede", "LiDAR", "BRO/AHN/PDOK waar beschikbaar"]\n    }\n    structural = {\n        "project_name": request.project_name,\n        "engine": "OpenSees + CalculiX + FreeCAD FEM + Structural Optimizer",\n        "status": "PENDING_DIGITAL_TWIN",\n        "default_outputs": ["belastingen", "reacties", "momenten", "dwarskrachten", "fundering", "wapening", "optimalisatie"]\n    }\n    stee_project = {\n        "project_name": request.project_name,\n        "source_traceability": "ACTIVE",\n        "folder": "Bronvermelding_van_dit_project",\n        "created_at": datetime.now().isoformat(timespec="seconds")\n    }\n    readme = f"""# {request.project_name}\n\nProject aangemaakt door BREWSTER ENGINEERING WIZARD 1.2.\n\n## Projectgegevens\n- Projecttype: {request.project_type}\n- Locatie: {request.location}\n- Land/regio: {request.country}\n- Omschrijving: {request.description}\n\n## Workflow\nADAE -> AAIE -> GECE -> Living Digital Twin\n"""\n    write_json(project_dir / "01_project_data" / "project.json", project_data)\n    write_json(project_dir / "02_digital_twin" / "digital_twin.json", twin)\n    write_json(project_dir / "03_geotwin" / "geotwin.json", geotwin)\n    write_json(project_dir / "04_structural" / "structural_model.json", structural)\n    write_json(project_dir / "10_stee" / "stee_project.json", stee_project)\n    (project_dir / "README.md").write_text(readme, encoding="utf-8")\n    append_stee(request.project_name, "PROJECT", str(project_dir), "Projectmap en basisbestanden aangemaakt")\n    return project_dir, project_data, twin\n\n@app.get("/")\ndef root():\n    return {\n        "status": "BREWSTER ENGINEERING WIZARD runtime actief",\n        "version": "1.2.0",\n        "modules": ["Project Manager", "Living Digital Twin", "GeoTwin", "Structural Agent", "STEE"]\n    }\n\n@app.post("/projects/create")\ndef create_project(request: ProjectRequest):\n    project_dir, project_data, twin = create_project_files(request)\n    return {\n        "message": "Project aangemaakt en opgeslagen",\n        "project": project_data,\n        "project_folder": str(project_dir),\n        "digital_twin": twin,\n        "next_step": "ADAE -> AAIE -> GECE -> Living Digital Twin"\n    }\n\n@app.get("/projects/list")\ndef list_projects():\n    projects_dir = ROOT / "projects"\n    ensure_dir(projects_dir)\n    projects = []\n    for p in projects_dir.iterdir():\n        if p.is_dir():\n            data_file = p / "01_project_data" / "project.json"\n            if data_file.exists():\n                projects.append(json.loads(data_file.read_text(encoding="utf-8")))\n            else:\n                projects.append({"project_name": p.name, "status": "UNKNOWN"})\n    return {"projects": projects}\n\n@app.get("/projects/{project_name}/twin")\ndef get_project_twin(project_name: str):\n    twin_file = ROOT / "projects" / safe_slug(project_name) / "02_digital_twin" / "digital_twin.json"\n    if not twin_file.exists():\n        return {"error": "Digital Twin niet gevonden", "project_name": project_name}\n    return json.loads(twin_file.read_text(encoding="utf-8"))\n\n@app.get("/projects/{project_name}/geotwin")\ndef get_project_geotwin(project_name: str):\n    geo_file = ROOT / "projects" / safe_slug(project_name) / "03_geotwin" / "geotwin.json"\n    if not geo_file.exists():\n        return {"error": "GeoTwin niet gevonden", "project_name": project_name}\n    return json.loads(geo_file.read_text(encoding="utf-8"))\n\n@app.get("/projects/{project_name}/structural")\ndef get_project_structural(project_name: str):\n    structural_file = ROOT / "projects" / safe_slug(project_name) / "04_structural" / "structural_model.json"\n    if not structural_file.exists():\n        return {"error": "Structural model niet gevonden", "project_name": project_name}\n    return json.loads(structural_file.read_text(encoding="utf-8"))\n'

def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)

def append_stee():
    stee_dir = ROOT / "stee"
    ensure_dir(stee_dir)
    csv_path = stee_dir / "bronnenregister.csv"
    if not csv_path.exists():
        csv_path.write_text("datum_tijd,project,bron_type,bron,doel,status\n", encoding="utf-8")
    with csv_path.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')},BREWSTER,SYSTEM,BREWSTER v1.2 Runtime Upgrade,Projectopslag en Digital Twin endpoints toegevoegd,AANGEMAAKT\n")

def main():
    ensure_dir(ROOT / "runtime")
    (ROOT / "runtime" / "main.py").write_text(MAIN_PY, encoding="utf-8")

    ensure_dir(ROOT / "docs")
    (ROOT / "docs" / "BREWSTER_v1_2_Project_Storage.md").write_text("""# BREWSTER ENGINEERING WIZARD 1.2

Toegevoegd:
- Echte projectopslag in `projects/<projectnaam>`
- Project JSON
- Concept Living Digital Twin JSON
- GeoTwin JSON
- Structural Model JSON
- STEE projectregistratie

Nieuwe endpoints:
- POST /projects/create
- GET /projects/list
- GET /projects/{project_name}/twin
- GET /projects/{project_name}/geotwin
- GET /projects/{project_name}/structural
""", encoding="utf-8")

    append_stee()
    print("KLAAR: BREWSTER ENGINEERING WIZARD v1.2 upgrade uitgevoerd.")
    print("Start daarna met:")
    print("python -m uvicorn runtime.main:app --reload")
    print("Open:")
    print("http://127.0.0.1:8000/docs")

if __name__ == "__main__":
    main()
