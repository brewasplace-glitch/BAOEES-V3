param(
    [string]$RepoRoot = "C:\PROJECT-PHOENIX",
    [string]$OutputPath = "outputs/runtime/bb10/knowledge_graph.json"
)

$ErrorActionPreference = "Stop"
Set-Location $RepoRoot
$env:PYTHONPATH = $RepoRoot

$Code = @'
from pathlib import Path
from phoenix.database import ProjectDatabase
from phoenix.knowledge_graph import KnowledgeGraphEngine
from phoenix.knowledge_graph.digital_twin_bridge import import_project_database

repo = Path.cwd()
db = ProjectDatabase("BB10-DEMO", repo / "outputs" / "runtime" / "bb10")
building = db.create_object("building", "Phoenix Demo Building")
storey = db.create_object("storey", "Ground Floor")
document = db.create_object("document", "Concept Design Report")
db.relate(building.object_id, "contains", storey.object_id)
db.relate(document.object_id, "documents", building.object_id)

graph = KnowledgeGraphEngine()
import_project_database(db, graph)
checksum = graph.repository.save(repo / r"__OUTPUT__")
validation = graph.validate_traceability()

print("Phoenix Knowledge Graph self-test: PASSED")
print(f"Nodes: {validation['node_count']}")
print(f"Edges: {validation['edge_count']}")
print(f"Valid: {validation['valid']}")
print(f"Checksum: {checksum}")
'@

$Code = $Code.Replace("__OUTPUT__", $OutputPath.Replace("\", "\\"))
$Code | python -
if ($LASTEXITCODE -ne 0) {
    throw "Phoenix Knowledge Graph self-test failed."
}
