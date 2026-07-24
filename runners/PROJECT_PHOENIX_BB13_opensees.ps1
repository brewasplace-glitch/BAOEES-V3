param(
    [string]$RepoRoot = "C:\PROJECT-PHOENIX",
    [string]$OutputRoot = "outputs/runtime/bb13"
)

$ErrorActionPreference = "Stop"
Set-Location $RepoRoot
$env:PYTHONPATH = $RepoRoot

@'
from pathlib import Path
from phoenix.opensees import (
    BoundaryCondition,
    Load,
    Node,
    OpenSeesIntegrationEngine,
    StructuralModel,
    TrussElement,
)

n1 = Node(0.0, 0.0)
n2 = Node(4.0, 0.0)
n3 = Node(2.0, 3.0)

model = StructuralModel(
    name="BB13 Demonstration Truss",
    model_id="BB13-DEMO",
    nodes=[n1, n2, n3],
    truss_elements=[
        TrussElement(n1.node_id, n2.node_id, 0.01, 210e9),
        TrussElement(n1.node_id, n3.node_id, 0.01, 210e9),
        TrussElement(n2.node_id, n3.node_id, 0.01, 210e9),
    ],
    boundary_conditions=[
        BoundaryCondition(n1.node_id, True, True),
        BoundaryCondition(n2.node_id, False, True),
    ],
    loads=[Load(n3.node_id, fy=-100000.0)],
)

engine = OpenSeesIntegrationEngine()
result = engine.analyze_and_save(
    model,
    evidence_path=Path(r"outputs/runtime/bb13/analysis.json"),
)

print("Phoenix OpenSees Integration self-test: PASSED")
print(f"Runtime mode: {result.runtime_mode}")
print(f"Nodes: {len(model.nodes)}")
print(f"Elements: {len(model.truss_elements)}")
print(f"Checksum: {result.checksum_sha256}")
'@ | python -

if ($LASTEXITCODE -ne 0) {
    throw "Phoenix OpenSees self-test failed."
}
