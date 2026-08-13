param(
    [ValidateSet("ValidateModel","PrepareScia","InspectSciaEnvironment","ProbeSciaEnvironment")]
    [string]$Action,
    [string]$Repository = "C:\PROJECT-PHOENIX",
    [string]$Model,
    [string]$Output,
    [string]$SeedEsa,
    [string]$XmlUpdate,
    [string]$XmlDefinition,
    [string]$AnalysisScope,
    [string]$LicenseTarget,
    [string]$ProbeProject,
    [switch]$AllowLiveProbe,
    [string]$EsaXml = "C:\Program Files (x86)\SCIA\Engineer18.1\ESA_XML.exe",
    [string]$EsaExe = "C:\Program Files (x86)\SCIA\Engineer18.1\ESA.exe",
    [string]$Lockman = "C:\Program Files (x86)\SCIA\Engineer18.1\Lockman.exe"
)

$ErrorActionPreference = "Stop"
$Repository = (Resolve-Path $Repository).Path
Set-Location $Repository

$RuntimeRoot = Join-Path $Repository "projects\runtime\STRUCTURAL-MODEL-INTERCHANGE-SCIA-v1_0"
if (-not $Output) {
    switch ($Action) {
        "ValidateModel" { $Output = Join-Path $RuntimeRoot "canonical_model_validation.json" }
        "PrepareScia" { $Output = Join-Path $RuntimeRoot "scia_preparation" }
        "InspectSciaEnvironment" { $Output = Join-Path $RuntimeRoot "scia_environment_readiness.json" }
        "ProbeSciaEnvironment" { $Output = Join-Path $RuntimeRoot "scia_environment_probe" }
    }
}

switch ($Action) {
    "ValidateModel" {
        if (-not $Model) { throw "-Model is required." }
        python -m phoenix.autonomy.structural_model_interchange_scia_preparation_v1_0 `
            validate --model $Model --output $Output
    }
    "PrepareScia" {
        if (-not $Model) { throw "-Model is required." }
        $argsList = @(
            "-m", "phoenix.autonomy.structural_model_interchange_scia_preparation_v1_0",
            "prepare-scia",
            "--model", $Model,
            "--output", $Output,
            "--esa-xml", $EsaXml
        )
        if ($SeedEsa) { $argsList += @("--seed-esa", $SeedEsa) }
        if ($XmlUpdate) { $argsList += @("--xml-update", $XmlUpdate) }
        if ($XmlDefinition) { $argsList += @("--xml-definition", $XmlDefinition) }
        if ($AnalysisScope) { $argsList += @("--analysis-scope", $AnalysisScope) }
        python @argsList
    }
    "InspectSciaEnvironment" {
        $argsList = @(
            "-m", "phoenix.integrations.scia.environment_readiness_v1_0",
            "inspect",
            "--esa-xml", $EsaXml,
            "--esa", $EsaExe,
            "--lockman", $Lockman,
            "--output", $Output
        )
        if ($LicenseTarget) { $argsList += @("--license-target", $LicenseTarget) }
        python @argsList
    }
    "ProbeSciaEnvironment" {
        if (-not $AllowLiveProbe) {
            throw "Live SCIA probe blocked: rerun with explicit -AllowLiveProbe."
        }
        if (-not $ProbeProject) {
            $ProbeProject = Join-Path $Repository "reference_models\structural\scia\beam_v1_0\Beam.esa"
        }
        $scope = if ($AnalysisScope) { $AnalysisScope } else { "LIN" }
        python -m phoenix.integrations.scia.environment_readiness_v1_0 `
            probe `
            --esa-xml $EsaXml `
            --project-esa $ProbeProject `
            --output $Output `
            --analysis $scope `
            --allow-live-probe
    }
}

if ($LASTEXITCODE -ne 0) {
    throw "PROJECT PHOENIX structural interchange / SCIA readiness action failed."
}
