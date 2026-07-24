param(
    [string]$RepoRoot = "C:\PROJECT-PHOENIX",
    [string]$OutputRoot = "outputs/runtime/bb12"
)

$ErrorActionPreference = "Stop"
Set-Location $RepoRoot
$env:PYTHONPATH = $RepoRoot

$Code = @'
from pathlib import Path

from phoenix.database import ProjectDatabase
from phoenix.knowledge_graph import KnowledgeGraphEngine
from phoenix.qgis import QGISIntegrationEngine, SpatialExtent
from phoenix.qgis.datasources import write_geojson
from phoenix.qgis.digital_twin_bridge import publish_project_to_digital_twin
from phoenix.qgis.knowledge_graph_bridge import publish_project_to_knowledge_graph

root = Path(r"__OUTPUT__")
root.mkdir(parents=True, exist_ok=True)

site_path = root / "site.geojson"
write_geojson(
    site_path,
    [{
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [5.377, 52.25],
        },
        "properties": {
            "name": "Phoenix demonstration site",
        },
    }],
)

engine = QGISIntegrationEngine()
project = engine.create_project(
    name="Phoenix BB12 Demonstration",
    project_id="BB12-DEMO",
    crs="EPSG:28992",
    extent=SpatialExtent(
        155000,
        470000,
        156000,
        471000,
        "EPSG:28992",
    ),
)
engine.add_file_layer(
    project,
    name="Demonstration Site",
    path=site_path,
    geometry_type="point",
    crs="EPSG:4326",
)

result = engine.save_project(
    project,
    manifest_path=root / "project_manifest.json",
    qgs_path=root / "project.qgs",
)

database = ProjectDatabase("BB12-DEMO", root / "digital_twin")
twin_mapping = publish_project_to_digital_twin(project, database)

graph = KnowledgeGraphEngine()
graph_mapping = publish_project_to_knowledge_graph(project, graph)

print("Phoenix QGIS Integration self-test: PASSED")
print(f"Runtime mode: {result['runtime']['mode']}")
print(f"Layers: {len(project.layers)}")
print(f"Digital Twin objects: {len(twin_mapping)}")
print(f"Knowledge Graph nodes: {len(graph_mapping)}")
print(f"Manifest checksum: {result['manifest_checksum_sha256']}")
'@

$Code = $Code.Replace("__OUTPUT__", $OutputRoot.Replace("\", "\\"))
$Code | python -
if ($LASTEXITCODE -ne 0) {
    throw "Phoenix QGIS Integration self-test failed."
}
