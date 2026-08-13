param(
    [ValidateSet("CreateDossier","ProcessReturn")]
    [string]$Action,
    [string]$Repository = "C:\PROJECT-PHOENIX",
    [string]$Plan,
    [string]$DossierRoot,
    [string]$ReviewerReturn
)

$ErrorActionPreference = "Stop"
$Repository = (Resolve-Path $Repository).Path
Set-Location $Repository

if ($Action -eq "CreateDossier") {
    if (-not $Plan) { throw "-Plan is required for CreateDossier." }
    $Plan = (Resolve-Path $Plan).Path
    python -m phoenix.autonomy.professional_dossier_controlled_review_v1_0 `
        create-dossier --repository $Repository --plan $Plan
} else {
    if (-not $DossierRoot -or -not $ReviewerReturn) {
        throw "-DossierRoot and -ReviewerReturn are required for ProcessReturn."
    }
    python -m phoenix.autonomy.professional_dossier_controlled_review_v1_0 `
        process-return --repository $Repository --dossier-root $DossierRoot --reviewer-return $ReviewerReturn
}

if ($LASTEXITCODE -ne 0) {
    throw "Phoenix Professional Dossier / Controlled Review action did not reach a passing state."
}
