$ErrorActionPreference = "Stop"
$RepoRoot = "C:\PROJECT-PHOENIX"
$RuntimeRoot = Join-Path $env:LOCALAPPDATA "PROJECT-PHOENIX\autonomy\phase16"
$Branch = "project-phoenix"
$fetchOut = Join-Path $env:TEMP ("phoenix-phase16-fetch-" + [guid]::NewGuid().ToString("N") + ".out")
$fetchErr = $fetchOut + ".err"
try {
    $fetch = Start-Process -FilePath "git.exe" -ArgumentList @("-C", $RepoRoot, "fetch", "origin", $Branch) -RedirectStandardOutput $fetchOut -RedirectStandardError $fetchErr -NoNewWindow -Wait -PassThru
    if ($fetch.ExitCode -ne 0) { throw "PHASE16_SCHEDULED_REMOTE_FETCH_DENY" }
}
finally {
    Remove-Item -LiteralPath $fetchOut, $fetchErr -Force -ErrorAction SilentlyContinue
}
$head = (& git.exe -C $RepoRoot rev-parse HEAD).Trim()
$origin = (& git.exe -C $RepoRoot rev-parse "origin/$Branch").Trim()
if ($LASTEXITCODE -ne 0 -or $head -ne $origin) { throw "PHASE16_SCHEDULED_BASELINE_SYNC_DENY" }
$runner = Join-Path $RepoRoot "runners\PROJECT_PHOENIX_4_41_governed_continuous_level5_v1.py"
Set-Location -LiteralPath $RepoRoot
& python.exe $runner --repo-root $RepoRoot --runtime-root $RuntimeRoot --expected-baseline $head --scheduled-window
if ($LASTEXITCODE -ne 0) { throw "PHASE16_SCHEDULED_WINDOW_FAILED" }
