param(
    [ValidateSet("AnalyticalGoldenBeam","PrepareCalculixGoldenBeam","RunCalculixGoldenBeam")]
    [string]$Action,
    [string]$Repository = "C:\PROJECT-PHOENIX",
    [string]$Output,
    [string]$Ccx,
    [switch]$AllowLiveSolver,
    [int]$TimeoutSeconds = 900
)

$ErrorActionPreference = "Stop"
$Repository = (Resolve-Path $Repository).Path
Set-Location $Repository

if (-not $Output) {
    $Output = Join-Path $Repository "projects\runtime\REFERENCE-MODELS\CALCULIX-ANALYTICAL-v1_0"
}

switch ($Action) {
    "AnalyticalGoldenBeam" {
        python -m phoenix.autonomy.structural_analytical_verification_v1_0 `
            golden-beam `
            --output (Join-Path $Output "analytical_golden_beam.json")
    }
    "PrepareCalculixGoldenBeam" {
        python -m phoenix.integrations.calculix.reference_verification_v1_0 `
            prepare-golden-beam `
            --output (Join-Path $Output "calculix")
    }
    "RunCalculixGoldenBeam" {
        if (-not $AllowLiveSolver) {
            throw "Live CalculiX blocked. Re-run with explicit -AllowLiveSolver."
        }
        $argsList = @(
            "-m", "phoenix.integrations.calculix.reference_verification_v1_0",
            "run-golden-beam",
            "--output", (Join-Path $Output "calculix"),
            "--repository", $Repository,
            "--timeout-seconds", "$TimeoutSeconds",
            "--allow-live-solver"
        )
        if ($Ccx) { $argsList += @("--ccx", $Ccx) }
        python @argsList
    }
}

if ($LASTEXITCODE -ne 0) {
    throw "PROJECT PHOENIX CalculiX/Analytical verification action failed."
}
