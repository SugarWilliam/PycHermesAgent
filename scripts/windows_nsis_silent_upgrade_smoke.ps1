#!/usr/bin/env pwsh
# NSIS silent install + reinstall (upgrade-ish) smoke for GitHub-hosted or self-hosted Windows runners.
#
# Usage (repo root path optional):
#   pwsh scripts/windows_nsis_silent_upgrade_smoke.ps1 -DistDir desktop/dist-installer
#
# Picks the newest non-unpacked *.exe installer under DistDir (electron-builder Setup output).

param(
    [Parameter(Mandatory = $true)]
    [string]$DistDir
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$dist = Resolve-Path $DistDir
$instRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("ph-nsis-smoke-" + [Guid]::NewGuid().ToString("N"))

Write-Host "Using installer dir: $dist"
Write-Host "Temp install prefix: $instRoot"

function Get-InstallerExe {
    param([string]$Root)
    $candidates = @(
        Get-ChildItem -Path $Root -Filter *.exe -File -ErrorAction SilentlyContinue
        Get-ChildItem -Path $Root -Directory -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -notmatch '(?i)(unpacked|mac|darwin|linux)' } |
            Get-ChildItem -Filter *.exe -File -Recurse -ErrorAction SilentlyContinue
    )
    $filtered = $candidates |
        Where-Object {
            $_ -and
            $_.FullName -notmatch '(?i)unpacked|[\\/]resources[\\/]'
        }
    $setup = @($filtered |
            Where-Object { $_.Name -match '(?i)setup|install' }) |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1

    if ($setup) {
        return $setup
    }
    # Fallback to largest exe that is not Electron runtime chunk (Setup is usually singular at dist root).
    return @($filtered | Sort-Object Length -Descending | Select-Object -First 1)
}

$installer = Get-InstallerExe -Root $dist
if (-not $installer) {
    throw "NSIS installer .exe not found under $dist (expected electron-builder Setup output)."
}
Write-Host "Installer candidate: $($installer.FullName)"

function Invoke-QuietInstaller {
    param(
        [string]$ExePath,
        [string]$TargetDir,
        [int]$Attempt,
        [switch]$ResetTargetDir
    )

    if ($ResetTargetDir) {
        if (Test-Path $TargetDir) {
            Remove-Item -LiteralPath $TargetDir -Recurse -Force -ErrorAction SilentlyContinue
        }
        New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
    }
    elseif (-not (Test-Path $TargetDir)) {
        throw "Attempt $Attempt : expected directory $TargetDir to exist."
    }

    # /S = silent. Keep /D= on every attempt — NSIS honours it when the directory already exists under many electron-builder stubs.
    $args = @('/S', "/D=$TargetDir")
    Write-Host "Install attempt $Attempt -> $ExePath $($args -join ' ')"
    $p = Start-Process -FilePath $ExePath -ArgumentList $args -Wait -PassThru -NoNewWindow
    if ($p.ExitCode -ne 0) {
        throw "Installer exit code $($p.ExitCode) on attempt $Attempt"
    }

    Start-Sleep -Seconds 3

    $exeHit = Get-ChildItem -Path $TargetDir -Filter 'PycHermesAgent.exe' -Recurse -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if (-not $exeHit) {
        $exeHit = Get-ChildItem -Path $TargetDir -Filter '*.exe' -Recurse -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match '(?i)pyc.*hermes' -and $_.Name -notmatch '(?i)uninstall|unins' } |
            Select-Object -First 1
    }
    if (-not $exeHit) {
        throw "Installed app executable not found under $TargetDir after attempt $Attempt"
    }
    Write-Host "Found EXE: $($exeHit.FullName)"
}

# First install into empty prefix (pass /D=).
Invoke-QuietInstaller -ExePath $installer.FullName -TargetDir $instRoot -Attempt 1 -ResetTargetDir

# Second silent pass targeting existing tree (upgrade / maintenance path).
Invoke-QuietInstaller -ExePath $installer.FullName -TargetDir $instRoot -Attempt 2

# Best-effort silent uninstall
$uninst = Get-ChildItem -Path $instRoot -Filter *.exe -Recurse -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match '(?i)uninstall' } |
    Select-Object -First 1
if ($uninst) {
    Write-Host "Running uninstaller: $($uninst.FullName) /S"
    $u = Start-Process -FilePath $uninst.FullName -ArgumentList @('/S') -Wait -PassThru -NoNewWindow
    if ($u.ExitCode -ne 0) {
        Write-Warning "Uninstaller exit $($u.ExitCode) — cleaning temp tree anyway."
    }
}
else {
    Write-Warning 'No Uninstall*.exe found; removing temp install tree only.'
}

Start-Sleep -Seconds 2
Remove-Item -LiteralPath $instRoot -Recurse -Force -ErrorAction SilentlyContinue

Write-Host 'PASS windows_nsis_silent_upgrade_smoke'
