Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function ConvertTo-NormalizedGitPath {
    param([Parameter(Mandatory)][string]$Path)
    return $Path.Replace("\", "/").TrimStart("./").TrimEnd("/")
}

function Test-PhoenixPathMatch {
    param(
        [Parameter(Mandatory)][string]$Candidate,
        [Parameter(Mandatory)][string[]]$AllowedPaths
    )

    $candidateNormalized = (ConvertTo-NormalizedGitPath $Candidate).ToLowerInvariant()

    foreach ($allowed in $AllowedPaths) {
        $allowedNormalized = (ConvertTo-NormalizedGitPath $allowed).ToLowerInvariant()
        if (
            $candidateNormalized -eq $allowedNormalized -or
            $candidateNormalized.StartsWith($allowedNormalized + "/")
        ) {
            return $true
        }
    }
    return $false
}

function Invoke-PhoenixCommand {
    param(
        [Parameter(Mandatory)][string]$Command,
        [Parameter(Mandatory)][string]$FailureMessage
    )

    Write-Host "  > $Command" -ForegroundColor DarkGray
    Invoke-Expression $Command
    if ($LASTEXITCODE -ne 0) { throw $FailureMessage }
}

function Remove-PhoenixRuntimeArtifacts {
    param(
        [Parameter(Mandatory)][string]$Root,
        [Parameter(Mandatory)]$RuntimePolicies
    )

    foreach ($policy in $RuntimePolicies) {
        if ($policy.mode -ne "clean") { continue }
        $target = Join-Path $Root $policy.path
        if (Test-Path $target) {
            Remove-Item -Recurse -Force $target
        }
    }
}

function Update-PhoenixGitIgnore {
    param(
        [Parameter(Mandatory)][string]$Root,
        [Parameter(Mandatory)]$RuntimePolicies
    )

    $gitIgnore = Join-Path $Root ".gitignore"
    if (-not (Test-Path $gitIgnore)) {
        New-Item -ItemType File -Path $gitIgnore -Force | Out-Null
    }

    $content = Get-Content -Raw -Path $gitIgnore -ErrorAction SilentlyContinue
    if ($null -eq $content) { $content = "" }

    $linesToAdd = @()
    foreach ($policy in $RuntimePolicies) {
        if ($policy.mode -ne "ignore") { continue }
        $entry = ConvertTo-NormalizedGitPath $policy.path
        if (-not $content.Contains($entry)) { $linesToAdd += $entry }
    }

    if ($linesToAdd.Count -gt 0) {
        Add-Content -Path $gitIgnore -Value ""
        Add-Content -Path $gitIgnore -Value "# Phoenix Release Framework managed runtime"
        foreach ($line in $linesToAdd) {
            Add-Content -Path $gitIgnore -Value $line
        }
    }
}

function Invoke-PhoenixRelease {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$ManifestPath,
        [switch]$RunTests
    )

    $manifest = Get-Content -Raw -Path $ManifestPath |
        ConvertFrom-Json

    $root = (Resolve-Path $manifest.repository_root).Path
    Set-Location $root

    $branch = (git branch --show-current).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $branch) {
        throw "Branchcontrole mislukt."
    }

    if ($manifest.branch -and $branch -ne $manifest.branch) {
        throw "Verkeerde branch: '$branch'; verwacht '$($manifest.branch)'."
    }

    git restore --staged .
    if ($LASTEXITCODE -ne 0) { throw "Staging herstellen mislukt." }

    Update-PhoenixGitIgnore -Root $root -RuntimePolicies $manifest.runtime_policies
    Remove-PhoenixRuntimeArtifacts -Root $root -RuntimePolicies $manifest.runtime_policies

    foreach ($required in $manifest.required_files) {
        if (-not (Test-Path (Join-Path $root $required))) {
            throw "Vereist releasebestand ontbreekt: $required"
        }
    }

    foreach ($command in $manifest.validation_commands) {
        Invoke-PhoenixCommand `
            -Command $command.command `
            -FailureMessage $command.failure_message
    }

    if ($RunTests) {
        foreach ($command in $manifest.test_commands) {
            Invoke-PhoenixCommand `
                -Command $command.command `
                -FailureMessage $command.failure_message
        }
    }

    Remove-PhoenixRuntimeArtifacts -Root $root -RuntimePolicies $manifest.runtime_policies

    git diff --check
    if ($LASTEXITCODE -ne 0) { throw "git diff --check mislukt." }

    $allowed = @($manifest.source_paths)
    foreach ($policy in $manifest.runtime_policies) {
        if ($policy.mode -eq "track") { $allowed += $policy.path }
    }
    if ($manifest.include_gitignore) { $allowed += ".gitignore" }

    $statusLines = @(git status --porcelain -uall)
    $unexpected = @()

    foreach ($line in $statusLines) {
        if ($line.Length -lt 4) { continue }
        $candidate = $line.Substring(3).Trim('"')
        if (-not (Test-PhoenixPathMatch -Candidate $candidate -AllowedPaths $allowed)) {
            $unexpected += $line
        }
    }

    if ($unexpected.Count -gt 0) {
        throw "Release geblokkeerd door onverwachte wijzigingen: $($unexpected -join '; ')"
    }

    foreach ($path in $allowed) {
        git add -- $path
        if ($LASTEXITCODE -ne 0) { throw "Stagen mislukt voor: $path" }
    }

    $staged = @(git diff --cached --name-only)
    if ($staged.Count -eq 0) { throw "Geen releasewijzigingen om te committen." }

    $unexpectedStaged = @()
    foreach ($file in $staged) {
        if (-not (Test-PhoenixPathMatch -Candidate $file -AllowedPaths $allowed)) {
            $unexpectedStaged += $file
        }
    }

    if ($unexpectedStaged.Count -gt 0) {
        git restore --staged .
        throw "Onverwachte gestagede bestanden: $($unexpectedStaged -join ', ')"
    }

    git commit -m $manifest.commit_message
    if ($LASTEXITCODE -ne 0) { throw "Releasecommit mislukt." }

    git push origin $branch
    if ($LASTEXITCODE -ne 0) { throw "Releasepush mislukt." }

    $final = @(git status --porcelain -uall)
    if ($final.Count -gt 0) {
        throw "Finale controle mislukt: $($final -join '; ')"
    }

    git status
    if ($LASTEXITCODE -ne 0) { throw "Finale git status mislukt." }

    return [pscustomobject]@{
        framework = "Phoenix Release Framework"
        framework_version = "v1.0"
        release = $manifest.release
        branch = $branch
        commit_message = $manifest.commit_message
        status = "PASS"
        working_tree_clean = $true
        completed_at = (Get-Date).ToString("s")
    }
}

Export-ModuleMember -Function `
    ConvertTo-NormalizedGitPath,`
    Test-PhoenixPathMatch,`
    Invoke-PhoenixRelease

