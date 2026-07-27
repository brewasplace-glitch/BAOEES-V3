$ErrorActionPreference = "Stop"
$Repository = Split-Path -Parent $MyInvocation.MyCommand.Path
$SessionPath = Join-Path $Repository "outputs\runtime\phoenix_local_app_v1_0_0\session.json"
if (-not (Test-Path -LiteralPath $SessionPath -PathType Leaf)) {
    Write-Host "Project Phoenix Local is not running." -ForegroundColor Yellow
    exit 0
}
$Session = Get-Content -LiteralPath $SessionPath -Raw | ConvertFrom-Json
$Headers = @{ "X-Phoenix-Token" = $Session.token }
Invoke-RestMethod -Method Post -Uri ($Session.url + "/api/shutdown") -Headers $Headers -ContentType "application/json" -Body "{}" | Out-Null
Write-Host "Project Phoenix Local is stopping." -ForegroundColor Green
