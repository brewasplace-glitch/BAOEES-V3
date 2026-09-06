[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path,

    [Parameter(Mandatory = $false)]
    [string]$ProjectId = 'PLUTOSTRAAT_R10_2',

    [Parameter(Mandatory = $false)]
    [string]$OutputRoot = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Info([string]$Message) {
    Write-Host "[R10.2] $Message"
}

if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
    $OutputRoot = Join-Path $RepoRoot "outputs/projects/plutostraat/r10_2"
}

$designDir = Join-Path $OutputRoot 'designs'
$evalDir   = Join-Path $OutputRoot 'evaluation'
$qaDir     = Join-Path $OutputRoot 'qa'
$sheetDir  = Join-Path $OutputRoot 'review_sheets'
$variantCodes = @('A','B','C','D','E')

foreach ($dir in @($OutputRoot, $designDir, $evalDir, $qaDir, $sheetDir)) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

$pythonScript = @'
from pathlib import Path
import json

from phoenix.architecture.r10_2_optimizer import refine_variant, build_evaluation_summary
from phoenix.architecture.r10_2_camera_quality_gate import load_policy, evaluate_variant
from phoenix.architecture.r10_2_variant_sheet_builder import build_variant_sheet, build_comparison_sheet, write_json

repo_root = Path(r"__REPO_ROOT__")
output_root = Path(r"__OUTPUT_ROOT__")
policy = load_policy(repo_root / "configs/phoenix/r10_2_quality_gate_policy.json")
variant_codes = ["A", "B", "C", "D", "E"]
comparison = []

for code in variant_codes:
    source = {
        "source_variant": code,
        "status": "R10.1_BASELINE_INPUT",
        "assumptions": ["carry forward existing topology", "refine instead of replace"]
    }
    design = refine_variant(code, source)
    evaluation = build_evaluation_summary(code, design)
    dummy_metrics = {
        "street_corner": {"visible_building_ratio": 0.45, "useful_context_ratio": 0.14, "occlusion_ratio": 0.20, "camera_collision": False, "target_landmark_visible": True, "view_purpose_pass": True},
        "rear": {"visible_building_ratio": 0.42, "useful_context_ratio": 0.12, "occlusion_ratio": 0.18, "camera_collision": False, "target_landmark_visible": True, "view_purpose_pass": True},
        "side": {"visible_building_ratio": 0.43, "useful_context_ratio": 0.11, "occlusion_ratio": 0.20, "camera_collision": False, "target_landmark_visible": True, "view_purpose_pass": True},
        "courtyard_or_patio": {"visible_building_ratio": 0.40, "useful_context_ratio": 0.10, "occlusion_ratio": 0.22, "camera_collision": False, "target_landmark_visible": True, "view_purpose_pass": True},
        "aerial": {"visible_building_ratio": 0.50, "useful_context_ratio": 0.18, "occlusion_ratio": 0.12, "camera_collision": False, "target_landmark_visible": True, "view_purpose_pass": True}
    }
    qa = evaluate_variant(dummy_metrics, policy)
    sheet = build_variant_sheet(code, design, evaluation, qa)

    write_json(output_root / "designs" / f"variant_{code}.json", design)
    write_json(output_root / "evaluation" / f"variant_{code}.json", evaluation)
    write_json(output_root / "qa" / f"variant_{code}.json", qa)
    write_json(output_root / "review_sheets" / f"variant_{code}.json", sheet)
    comparison.append(sheet)

comparison_sheet = build_comparison_sheet(comparison)
write_json(output_root / "R10_2_QA_SUMMARY.json", comparison_sheet)
(output_root / "R10_2_RESULT.txt").write_text(
    "R10.2 scaffolding run completed\nSTATUS=PRELIMINARY / NOT FOR CONSTRUCTION\nLOCKS=UNCHANGED\n",
    encoding="utf-8"
)
print(str(output_root))
'@

$pythonScript = $pythonScript.Replace('__REPO_ROOT__', $RepoRoot).Replace('__OUTPUT_ROOT__', $OutputRoot)
$tempPy = Join-Path $env:TEMP 'phoenix_r10_2_execute_temp.py'
Set-Content -Path $tempPy -Value $pythonScript -Encoding UTF8

Write-Info "Running Python R10.2 scaffolding pipeline..."
python $tempPy
Remove-Item $tempPy -Force -ErrorAction SilentlyContinue

Write-Info "R10.2 output scaffold written to: $OutputRoot"
