param([string]$RepoPath = ".")
$ErrorActionPreference = "Stop"
Write-Host "PROJECT PHOENIX - EAMS v1.0 Installer" -ForegroundColor Cyan
$repo = Resolve-Path $RepoPath
Set-Location $repo
if (-not (Test-Path ".git")) { throw "Geen git repository gevonden. Voer uit vanuit C:\PROJECT-PHOENIX." }
$targetDirs = @(
  "project_phoenix/specifications/architectural",
  "project_phoenix/intelligence/master_specification/architectural",
  "docs/project_phoenix/specifications/architectural",
  "outputs/phoenix_intelligence/specifications/architectural"
)
foreach ($d in $targetDirs) { New-Item -ItemType Directory -Force -Path $d | Out-Null }
Copy-Item ".\architectural_master_specification_v1_0.json" "project_phoenix/specifications/architectural/architectural_master_specification_v1_0.json" -Force
Copy-Item ".\architectural_master_specification_v1_0.yaml" "project_phoenix/specifications/architectural/architectural_master_specification_v1_0.yaml" -Force
Copy-Item ".\architectural_master_specification_v1_0_executable.py" "project_phoenix/specifications/architectural/architectural_master_specification_v1_0_executable.py" -Force
Copy-Item ".\PROJECT_PHOENIX_Architectural_Master_Specification_v1_0_Executable.docx" "docs/project_phoenix/specifications/architectural/PROJECT_PHOENIX_Architectural_Master_Specification_v1_0_Executable.docx" -Force
Copy-Item ".\PROJECT_PHOENIX_Architectural_Master_Specification_v1_0_Executable.pdf" "docs/project_phoenix/specifications/architectural/PROJECT_PHOENIX_Architectural_Master_Specification_v1_0_Executable.pdf" -Force
Copy-Item ".\architectural_master_specification_v1_0.json" "project_phoenix/intelligence/master_specification/architectural/architectural_master_specification_v1_0.json" -Force
python "project_phoenix/specifications/architectural/architectural_master_specification_v1_0_executable.py"
git add project_phoenix/specifications/architectural project_phoenix/intelligence/master_specification/architectural docs/project_phoenix/specifications/architectural
git commit -m "spec: add executable architectural master specification v1.0"
git status
Write-Host "KLAAR: EAMS v1.0 is geïnstalleerd. Voer daarna uit: git push" -ForegroundColor Green
