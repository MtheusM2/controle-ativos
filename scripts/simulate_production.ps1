param(
    [int]$Port = 8001
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    throw "Virtualenv ausente. Execute scripts/rebuild_venv.ps1 antes."
}

$env:FLASK_DEBUG = "0"
& ".venv\Scripts\python.exe" -m waitress --listen=127.0.0.1:$Port wsgi:application