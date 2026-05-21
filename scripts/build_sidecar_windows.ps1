# Build pyc-hermes-sidecar.exe (Windows, from repo root)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Error "uv is not on PATH. Install from https://docs.astral.sh/uv/"
}
uv sync --frozen --extra ga
uv run pyinstaller --noconfirm packaging\pyinstaller\pyc_hermes_sidecar_onefile.spec
Write-Host "OK: dist\pyc-hermes-sidecar.exe"
