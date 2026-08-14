param(
    [ValidateSet("Inspect","ClassifyExistingProbe","Probe")]
    [string]$Action,
    [string]$Repository = "C:\PROJECT-PHOENIX",
    [string]$LicenseTarget,
    [string]$Output,
    [string]$ProbeJson,
    [string]$ProjectEsa,
    [string]$Analysis = "LIN",
    [switch]$AllowRuntimeHelp,
    [switch]$AllowLiveProbe,
    [int]$TimeoutSeconds = 900,
    [string]$EsaXml = "C:\Program Files (x86)\SCIA\Engineer18.1\ESA_XML.exe",
    [string]$EsaExe = "C:\Program Files (x86)\SCIA\Engineer18.1\ESA.exe",
    [string]$Lockman = "C:\Program Files (x86)\SCIA\Engineer18.1\Lockman.exe"
)

$ErrorActionPreference = "Stop"
$Repository = (Resolve-Path $Repository).Path
Set-Location $Repository

if (-not $Output) {
    $Output = Join-Path $Repository "projects\runtime\SCIA-ENVIRONMENT-READINESS-v1_1"
}

switch ($Action) {
    "Inspect" {
        $argsList = @(
            "-m", "phoenix.integrations.scia.environment_readiness_hardening_v1_1",
            "inspect",
            "--esa-xml", $EsaXml,
            "--esa", $EsaExe,
            "--lockman", $Lockman,
            "--output", (Join-Path $Output "scia_environment_inspection_v1_1.json")
        )
        if ($LicenseTarget) { $argsList += @("--license-target", $LicenseTarget) }
        if ($AllowRuntimeHelp) { $argsList += "--allow-runtime-help" }
        python @argsList
    }

    "ClassifyExistingProbe" {
        if (-not $ProbeJson) {
            $ProbeJson = Join-Path $Repository "projects\runtime\REFERENCE-MODELS\SCIA-BEAM-v1_0\scia\scia_live_validation_result.json"
        }
        python -m phoenix.integrations.scia.environment_readiness_hardening_v1_1 `
            classify-existing-probe `
            --probe-json $ProbeJson `
            --output (Join-Path $Output "scia_existing_probe_classification_v1_1.json")
    }

    "Probe" {
        if (-not $AllowLiveProbe) {
            throw "Live SCIA probe blocked. Re-run only when intended with explicit -AllowLiveProbe."
        }
        if (-not $ProjectEsa) {
            $ProjectEsa = Join-Path $Repository "reference_models\structural\scia\beam_v1_0\Beam.esa"
        }
        python -m phoenix.integrations.scia.environment_readiness_hardening_v1_1 `
            probe `
            --esa-xml $EsaXml `
            --project-esa $ProjectEsa `
            --output (Join-Path $Output "live_probe") `
            --analysis $Analysis `
            --allow-live-probe `
            --timeout-seconds $TimeoutSeconds
    }
}

if ($LASTEXITCODE -ne 0) {
    throw "PROJECT PHOENIX SCIA Environment Readiness v1.1 action failed."
}
