param(
    [Parameter(Mandatory)]
    [string]$Manifest,

    [switch]$RunTests
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

Import-Module `
    ".\phoenix\release\PhoenixReleaseFramework.psm1" `
    -Force

$result = Invoke-PhoenixRelease `
    -ManifestPath $Manifest `
    -RunTests:$RunTests

$result | ConvertTo-Json -Depth 5
