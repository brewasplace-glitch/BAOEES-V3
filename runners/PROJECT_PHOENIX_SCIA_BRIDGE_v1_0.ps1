param(
    [string]$Repository = "C:\PROJECT-PHOENIX",
    [Parameter(Mandatory=$true)][string]$Plan,
    [string]$EsaXml = "C:\Program Files (x86)\SCIA\Engineer18.1\ESA_XML.exe",
    [switch]$DryRun,
    [int]$TimeoutSeconds = 3600
)

$ErrorActionPreference = "Stop"
$Repository = (Resolve-Path $Repository).Path
$Plan = (Resolve-Path $Plan).Path

$argsList = @(
    "-m", "phoenix.integrations.scia.professional_engineering_bridge_v1_0",
    "--repository", $Repository,
    "--plan", $Plan,
    "--esa-xml", $EsaXml,
    "--timeout-seconds", "$TimeoutSeconds"
)
if ($DryRun) { $argsList += "--dry-run" }

Set-Location $Repository
python @argsList
if ($LASTEXITCODE -ne 0) {
    throw "Phoenix SCIA bridge execution failed."
}
