param(
    [ValidateSet("Prepare","Execute")]
    [string]$Action = "Prepare",
    [string]$Repository = "C:\PROJECT-PHOENIX",
    [string]$ProjectId = "PHOENIX-PAT-001",
    [string]$EsaXml = "C:\Program Files (x86)\SCIA\Engineer18.1\ESA_XML.exe"
)

$ErrorActionPreference = "Stop"
$Repository = (Resolve-Path $Repository).Path
Set-Location $Repository

if ($Action -eq "Prepare") {
    python -m phoenix.autonomy.structural_scia_end_to_end_v1_0 `
        prepare --repository $Repository --project-id $ProjectId --esa-xml $EsaXml
} else {
    python -m phoenix.autonomy.structural_scia_end_to_end_v1_0 `
        execute --repository $Repository --project-id $ProjectId --esa-xml $EsaXml
}

if ($LASTEXITCODE -ne 0) {
    throw "Phoenix SCIA E2E software execution failed. Review the printed project/software status."
}
