from pathlib import Path
import textwrap, csv

ROOT = Path.cwd()

folders = [
    'core', 'agents', 'agents/geo_agent', 'agents/structural_agent', 'digital_twin',
    'projects', 'projects/_template', 'data', 'reports', 'exports', 'stee', 'runtime'
]
for f in folders:
    (ROOT / f).mkdir(parents=True, exist_ok=True)

# Core project manager
(ROOT / 'core' / 'project_manager.py').write_text(textwrap.dedent('''
    from pathlib import Path
    from datetime import datetime
    import json

    PROJECTS_DIR = Path(__file__).resolve().parents[1] / 'projects'

    def create_project(name: str, location: str = '', country: str = 'Nederland', project_type: str = 'Bouw'):
        slug = name.strip().replace(' ', '_').replace('/', '_')
        project_dir = PROJECTS_DIR / slug
        project_dir.mkdir(parents=True, exist_ok=True)
        for sub in ['input', 'digital_twin', 'geo', 'structural', 'reports', 'drawings', 'exports', 'stee']:
            (project_dir / sub).mkdir(exist_ok=True)
        manifest = {
            'name': name,
            'location': location,
            'country': country,
            'project_type': project_type,
            'created_at': datetime.now().isoformat(timespec='seconds'),
            'status': 'created',
            'data_completeness_mode': 'known_data_open_data_ai_assumptions',
            'deployment_mode': 'local'
        }
        (project_dir / 'project_manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
        return manifest

    def list_projects():
        if not PROJECTS_DIR.exists():
            return []
        return [p.name for p in PROJECTS_DIR.iterdir() if p.is_dir() and not p.name.startswith('_')]
'''), encoding='utf-8')

# Digital twin core
(ROOT / 'digital_twin' / 'twin_core.py').write_text(textwrap.dedent('''
    from pathlib import Path
    from datetime import datetime
    import json

    ROOT = Path(__file__).resolve().parents[1]

    def create_twin(project_name: str):
        slug = project_name.strip().replace(' ', '_').replace('/', '_')
        project_dir = ROOT / 'projects' / slug
        twin_dir = project_dir / 'digital_twin'
        twin_dir.mkdir(parents=True, exist_ok=True)
        twin = {
            'project': project_name,
            'twin_type': 'Living Digital Twin',
            'created_at': datetime.now().isoformat(timespec='seconds'),
            'twins': {
                'architecture': {'status': 'initialized'},
                'geo': {'status': 'initialized'},
                'structural': {'status': 'initialized'},
                'mep': {'status': 'initialized'},
                'permit': {'status': 'initialized'},
                'asset': {'status': 'initialized'}
            }
        }
        (twin_dir / 'living_digital_twin.json').write_text(json.dumps(twin, indent=2, ensure_ascii=False), encoding='utf-8')
        return twin
'''), encoding='utf-8')

# Geo agent
(ROOT / 'agents' / 'geo_agent' / 'geo_agent.py').write_text(textwrap.dedent('''
    def analyse_geo(location: str, country: str = 'Nederland'):
        country_lower = country.lower()
        if 'suriname' in country_lower:
            return {
                'location': location,
                'country': country,
                'groundwater_level': {'value': 'P = -0.50 m', 'status': 'GEACTUALISEERD'},
                'soil_profile': [
                    {'from': '0.00 m', 'to': '-0.50 m', 'soil': 'zandopvulling', 'status': 'AANNAME'},
                    {'from': '-0.50 m', 'to': '-1.00 m', 'soil': 'vaste klei', 'status': 'AANNAME'},
                    {'from': '-1.00 m', 'to': '-2.20 m', 'soil': 'slappe klei', 'status': 'AANNAME'},
                    {'from': '-2.20 m', 'to': '-3.70 m', 'soil': 'zand', 'status': 'AANNAME'}
                ],
                'foundation_options': ['strokenfundering', 'paalfundering'],
                'recommendation': 'Vergelijk strokenfundering en paalfundering; zettingscontrole verplicht.'
            }
        return {
            'location': location,
            'country': country,
            'groundwater_level': {'value': 'automatisch bepalen via open geo-data; fallback P = -0.50 m', 'status': 'AANNAME'},
            'soil_profile': [],
            'foundation_options': ['strokenfundering', 'paalfundering'],
            'recommendation': 'Start ADAE/geo-data ophalen en maak Geo Twin.'
        }
'''), encoding='utf-8')

# Structural agent
(ROOT / 'agents' / 'structural_agent' / 'structural_agent.py').write_text(textwrap.dedent('''
    def concept_structural(project_name: str, foundation_choice: str = 'strokenfundering'):
        return {
            'project': project_name,
            'engine': 'OpenSees + CalculiX + FreeCAD FEM + Structural Optimizer',
            'foundation_choice': foundation_choice,
            'assumptions': {
                'concrete': {'value': 'C25/30', 'status': 'AANNAME'},
                'reinforcement': {'value': 'B500B', 'status': 'AANNAME'},
                'columns': {'value': '300x300 mm', 'status': 'AANNAME'},
                'beams': {'value': '300x500 mm', 'status': 'AANNAME'},
                'strip_foundation': {'value': '1500x400 mm', 'status': 'AANNAME'},
                'foundation_beam': {'value': '500x600 mm', 'status': 'AANNAME'}
            },
            'next_checks': ['draagkracht', 'zetting', 'verschilzetting', 'wapening', 'stabiliteit']
        }
'''), encoding='utf-8')

# STEE register
stee_file = ROOT / 'stee' / 'bronnenregister.csv'
if not stee_file.exists():
    with stee_file.open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(['datum_tijd','project','bron_type','bron','doel','status'])

# Runtime FastAPI
(ROOT / 'runtime' / 'main.py').write_text(textwrap.dedent('''
    from fastapi import FastAPI
    from pydantic import BaseModel
    from core.project_manager import create_project, list_projects
    from digital_twin.twin_core import create_twin
    from agents.geo_agent.geo_agent import analyse_geo
    from agents.structural_agent.structural_agent import concept_structural

    app = FastAPI(title='BREWSTER ENGINEERING WIZARD', version='1.1')

    class ProjectIn(BaseModel):
        name: str
        location: str = ''
        country: str = 'Nederland'
        project_type: str = 'Bouw'

    class GeoIn(BaseModel):
        location: str
        country: str = 'Nederland'

    class StructuralIn(BaseModel):
        project_name: str
        foundation_choice: str = 'strokenfundering'

    @app.get('/')
    def root():
        return {'status': 'BREWSTER ENGINEERING WIZARD runtime actief', 'version': '1.1'}

    @app.get('/projects')
    def projects():
        return {'projects': list_projects()}

    @app.post('/project/new')
    def new_project(project: ProjectIn):
        return create_project(project.name, project.location, project.country, project.project_type)

    @app.post('/twin/create')
    def twin_create(project: ProjectIn):
        create_project(project.name, project.location, project.country, project.project_type)
        return create_twin(project.name)

    @app.post('/geo/analyse')
    def geo_analyse(geo: GeoIn):
        return analyse_geo(geo.location, geo.country)

    @app.post('/structural/concept')
    def structural_concept(data: StructuralIn):
        return concept_structural(data.project_name, data.foundation_choice)
'''), encoding='utf-8')

# Docs
(ROOT / 'docs' / 'Sprint_1_Runtime.md').write_text(textwrap.dedent('''
    # BREWSTER ENGINEERING WIZARD 1.1 - Sprint 1 Runtime

    Toegevoegd:
    - Project Manager API
    - Living Digital Twin API
    - Geo Agent API
    - Structural Agent API
    - STEE basisregister

    Start:
    ```powershell
    python -m uvicorn runtime.main:app --reload
    ```

    Open:
    - http://127.0.0.1:8000
    - http://127.0.0.1:8000/docs
'''), encoding='utf-8')

print('KLAAR: BREWSTER ENGINEERING WIZARD v1.1 runtime modules toegevoegd.')
print('Start met: python -m uvicorn runtime.main:app --reload')
