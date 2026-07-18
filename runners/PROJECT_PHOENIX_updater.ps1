param(
    [ValidateSet("list","inspect","apply")]
    [string]$Command = "list",

    [string]$Package = "",

    [switch]$Commit,
    [switch]$Push,
    [switch]$NoTests
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

switch ($Command) {
    "list" {
        python -m phoenix.updater list
    }
    "inspect" {
        if (-not $Package) { throw "Package is verplicht." }
        python -m phoenix.updater inspect $Package
    }
    "apply" {
        if (-not $Package) { throw "Package is verplicht." }

        $arguments = @("-m", "phoenix.updater", "apply", $Package)
        if ($NoTests) { $arguments += "--no-tests" }
        if ($Commit) { $arguments += "--commit" }
        if ($Push) { $arguments += "--push" }

        python @arguments
    }
}

if ($LASTEXITCODE -ne 0) {
    throw "Phoenix Updater-opdracht mislukt."
}
