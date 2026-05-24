#!/usr/bin/env pwsh
# NSIS silent smoke for CI:
# - **FromDistDir**: pick Setup under `desktop/dist-installer`, install twice from the same exe (repair path).
# - **Dual semver upgrade**: `-PreviousInstaller` then `-UpgradeInstaller` into the same `/D=` prefix (true cross-build upgrade).
#
# electron-updater still needs a published feed JSON with two payloads; this script validates the **NSIS sequential upgrade skeleton**.

param(
    [Parameter(ParameterSetName = 'FromDir', Mandatory = $true)]
    [string]$DistDir,

    [Parameter(ParameterSetName = 'Dual', Mandatory = $true)]
    [string]$PreviousInstaller,

    [Parameter(ParameterSetName = 'Dual', Mandatory = $true)]
    [string]$UpgradeInstaller,

    [Parameter(ParameterSetName = 'Dual')]
    [string]$ExpectedVersionSubstringAfterUpgrade = ''

)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$instRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("ph-nsis-smoke-" + [Guid]::NewGuid().ToString("N"))
Write-Host "Temp install prefix: $instRoot"

function Get-InstallerExe {
    param([string]$Root)
    $rootPath = Resolve-Path $Root
    $candidates = @(
        Get-ChildItem -Path $rootPath -Filter *.exe -File -ErrorAction SilentlyContinue
        Get-ChildItem -Path $rootPath -Directory -ErrorAction SilentlyContinue |
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

    return @($filtered | Sort-Object Length -Descending | Select-Object -First 1)
}

function Resolve-Exe {
    param([string]$MaybePath)

    return (Resolve-Path -LiteralPath $MaybePath).Path
}

function Invoke-QuietInstaller {
    param(
        [string]$ExePath,
        [string]$TargetDir,
        [int]$Attempt,
        [switch]$ResetTargetDir
    )

    if (-not (Test-Path -LiteralPath $ExePath)) {
        throw "Installer missing: $ExePath"
    }

    if ($ResetTargetDir) {
        if (Test-Path $TargetDir) {
            Remove-Item -LiteralPath $TargetDir -Recurse -Force -ErrorAction SilentlyContinue
        }
        New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
    }
    elseif (-not (Test-Path $TargetDir)) {
        throw "Attempt $Attempt : expected directory $TargetDir to exist."
    }

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
    return $exeHit.FullName
}

function Assert-UpgradeVersionHints {
    param(
        [string]$ExePath,
        [string]$Needle
    )

    if ([string]::IsNullOrWhiteSpace($Needle)) {
        return
    }

    try {
        $vi = [System.Diagnostics.FileVersionInfo]::GetVersionInfo($ExePath)
        $blob = (@($vi.ProductVersion, $vi.FileVersion, $vi.Comments, $vi.ProductName) | Where-Object { $_ }) -join '|'
        if ([string]::IsNullOrWhiteSpace($blob)) {
            throw "Empty PE metadata for $ExePath (cannot validate '$Needle')."
        }
        if (-not $blob.Contains($Needle)) {
            throw "Expected '$Needle' in PE metadata for upgraded EXE; got '$blob'."
        }
        Write-Host "Version heuristic OK ('$Needle' in metadata)."
    }
    catch {
        throw $_
    }
}

try {
    if ($PSCmdlet.ParameterSetName -eq 'FromDir') {
        $dist = Resolve-Path $DistDir
        Write-Host "Using installer dir: $dist"

        $installer = Get-InstallerExe -Root $dist
        if (-not $installer) {
            throw "NSIS installer .exe not found under $dist (expected electron-builder Setup output)."
        }
        Write-Host "Installer candidate: $($installer.FullName)"

        Invoke-QuietInstaller -ExePath $installer.FullName -TargetDir $instRoot -Attempt 1 -ResetTargetDir | Out-Null
        Invoke-QuietInstaller -ExePath $installer.FullName -TargetDir $instRoot -Attempt 2 | Out-Null
    }
    else {
        $prev = Resolve-Exe -MaybePath $PreviousInstaller
        $next = Resolve-Exe -MaybePath $UpgradeInstaller
        Write-Host "Dual upgrade: PREV=$prev"
        Write-Host "Dual upgrade: NEXT=$next"

        Invoke-QuietInstaller -ExePath $prev -TargetDir $instRoot -Attempt 1 -ResetTargetDir | Out-Null
        $mainAfter = Invoke-QuietInstaller -ExePath $next -TargetDir $instRoot -Attempt 2
        Assert-UpgradeVersionHints -ExePath $mainAfter -Needle $ExpectedVersionSubstringAfterUpgrade
    }

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
}
finally {
    if (Test-Path $instRoot) {
        Remove-Item -LiteralPath $instRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
