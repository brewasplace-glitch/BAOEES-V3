param([string]$RepoRoot="C:\PROJECT-PHOENIX")
$ErrorActionPreference="Stop"
Set-Location $RepoRoot
$env:PYTHONPATH=$RepoRoot
@'
from pathlib import Path
from phoenix.calculix import *
n1,n2=Node(0,0,0),Node(3,0,0)
m=Material("Steel",210e9,0.3,7850)
e=BeamElement(n1.node_id,n2.node_id,m.material_id,0.01,8e-6,8e-6,1e-5)
model=FEModel("BB14 Demo","BB14-DEMO",[n1,n2],[m],[e],
 [BoundaryCondition(n1.node_id,1,6)],[ConcentratedLoad(n2.node_id,2,-10000)])
result=CalculiXIntegrationEngine().analyze_and_save(
 model,Path("outputs/runtime/bb14/work"),Path("outputs/runtime/bb14/evidence.json"),False)
print("Phoenix CalculiX Integration self-test: PASSED")
print("Runtime mode:",result.runtime_mode)
print("Checksum:",result.checksum_sha256)
'@ | python -
if ($LASTEXITCODE -ne 0){throw "BB14 self-test failed"}
