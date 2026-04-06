param()

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    throw "Virtualenv ausente. Execute scripts/rebuild_venv.ps1 antes."
}

$env:FLASK_DEBUG = "1"
& ".venv\Scripts\python.exe" "app.py"