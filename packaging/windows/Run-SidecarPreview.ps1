$ErrorActionPreference = "Stop"

# Preview launcher: enforces writable paths outside install (see docs/constraints/windows-packaging.md).
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path

$env:PYC_HERMES_ENFORCE_PACKAGING_RULES = "1"
$env:PYC_HERMES_INSTALL_DIR = $RepoRoot

$python = if ($env:PYC_HERMES_PYTHON) { $env:PYC_HERMES_PYTHON } else { "python" }

Write-Host "PycHermesAgent sidecar (packaging preview)"
Write-Host "  INSTALL_DIR (read-only root): $env:PYC_HERMES_INSTALL_DIR"
Write-Host "  Python: $python"
Write-Host "  APPDATA:    $env:APPDATA"
Write-Host "  LOCALAPPDATA: $env:LOCALAPPDATA"

& $python -m pyc_hermes_agent.sidecar_api --root $RepoRoot @args
