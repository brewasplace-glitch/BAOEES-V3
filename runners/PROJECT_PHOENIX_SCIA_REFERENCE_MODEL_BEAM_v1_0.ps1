param(
    [ValidateSet("ValidateSource","RunScia","RunCalculix","RunAll")]
    [string]$Action = "RunAll",
    [string]$Repository = "C:\PROJECT-PHOENIX",
    [string]$EsaXml = "C:\Program Files (x86)\SCIA\Engineer18.1\ESA_XML.exe",
    [string]$Ccx,
    [int]$TimeoutSeconds = 3600
)

$ErrorActionPreference = "Stop"
$Repository = (Resolve-Path $Repository).Path
$ReferenceRoot = Join-Path $Repository "reference_models\structural\scia\beam_v1_0"
$OutputRoot = Join-Path $Repository "projects\runtime\REFERENCE-MODELS\SCIA-BEAM-v1_0"
Set-Location $Repository

$actionMap = @{
    "ValidateSource" = "validate-source"
    "RunScia" = "run-scia"
    "RunCalculix" = "run-calculix"
    "RunAll" = "run-all"
}

$argsList = @(
    "-m", "phoenix.autonomy.scia_reference_model_beam_validation_v1_0",
    $actionMap[$Action],
    "--reference-root", $ReferenceRoot,
    "--output-root", $OutputRoot,
    "--esa-xml", $EsaXml,
    "--timeout-seconds", "$TimeoutSeconds"
)
if ($Ccx) { $argsList += @("--ccx", $Ccx) }

python @argsList
if ($LASTEXITCODE -ne 0) {
    throw "Phoenix SCIA Beam reference-model validation failed. Review runtime evidence under $OutputRoot."
}
