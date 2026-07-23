param(
    [string]$ProjectId = "PHOENIX-DEMO",
    [string]$StorageRoot = "outputs/runtime/v33_0"
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot
$env:PYTHONPATH = $RepoRoot

$PythonCode = @'
from pathlib import Path
from phoenix.database import ProjectDatabase

db = ProjectDatabase("__PROJECT_ID__", Path(r"__STORAGE_ROOT__"))
building = db.create_object("building", "Phoenix Demonstration Building")
storey = db.create_object("storey", "Ground Floor")
db.relate(building.object_id, "contains", storey.object_id)
checksum = db.save()
snapshot = db.create_snapshot()

print("Phoenix Digital Twin Core self-test: PASSED")
print(f"Project: {db.project_id}")
print(f"Objects: {len(list(db.objects.all()))}")
print(f"Relationships: {len(list(db.relationships.all()))}")
print(f"Checksum: {checksum}")
print(f"Snapshot: {snapshot.snapshot_id}")
'@

$PythonCode = $PythonCode.Replace("__PROJECT_ID__", $ProjectId)
$PythonCode = $PythonCode.Replace("__STORAGE_ROOT__", $StorageRoot.Replace("\", "\\"))
$PythonCode | python -
if ($LASTEXITCODE -ne 0) {
    throw "Phoenix Digital Twin Core self-test failed."
}
