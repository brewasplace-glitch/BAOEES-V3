param(
    [int]$Port = 8765,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$Repository = Split-Path -Parent $MyInvocation.MyCommand.Path

function Resolve-Python {
    foreach ($Candidate in @(
        @{ Command = "py"; Prefix = @("-3") },
        @{ Command = "python"; Prefix = @() },
        @{ Command = "python3"; Prefix = @() }
    )) {
        $Found = Get-Command $Candidate.Command -ErrorAction SilentlyContinue
        if ($null -ne $Found) {
            return @{ Command = $Found.Source; Prefix = $Candidate.Prefix }
        }
    }
    throw "Python 3 was not found."
}

$Python = Resolve-Python
$Arguments = @()
$Arguments += $Python.Prefix
$Arguments += @(
    (Join-Path $Repository "runners\PROJECT_PHOENIX_local_one_click_app_v1_0_0.py"),
    "--repository", $Repository,
    "--background",
    "--port", $Port
)
if (-not $NoBrowser) {
    $Arguments += "--open-browser"
}

& $Python.Command @Arguments
if ($LASTEXITCODE -ne 0) {
    throw "Project Phoenix Local failed to start."
}
