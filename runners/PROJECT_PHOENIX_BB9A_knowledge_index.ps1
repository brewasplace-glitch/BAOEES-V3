param(
    [string]$RepoRoot = "C:\PROJECT-PHOENIX"
)

$ErrorActionPreference = "Stop"
Set-Location $RepoRoot
$env:PYTHONPATH = $RepoRoot

@'
from pathlib import Path
from phoenix.build_system.knowledge_index import generate_index

output = generate_index(Path.cwd())
print(f"Phoenix Knowledge Base index generated: {output}")
'@ | python -

if ($LASTEXITCODE -ne 0) {
    throw "Phoenix Knowledge Base index generation failed."
}
