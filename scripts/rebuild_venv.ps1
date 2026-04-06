param(
    [string]$PythonCommand = "python"
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPath = Join-Path $projectRoot ".venv"
$requirementsPath = Join-Path $projectRoot "requirements.txt"

Write-Host "Reconstruindo ambiente virtual em $venvPath" -ForegroundColor Cyan

try {
    & $PythonCommand --version | Out-Null
} catch {
    Write-Error "Nao foi possivel localizar um Python valido usando '$PythonCommand'. Instale o Python e tente novamente."
}

if (Test-Path $venvPath) {
    Write-Host "Removendo ambiente virtual anterior..." -ForegroundColor Yellow
    Remove-Item -LiteralPath $venvPath -Recurse -Force
}

Write-Host "Criando nova virtualenv..." -ForegroundColor Cyan
& $PythonCommand -m venv $venvPath

$venvPython = Join-Path $venvPath "Scripts\\python.exe"

Write-Host "Atualizando pip..." -ForegroundColor Cyan
& $venvPython -m pip install --upgrade pip

Write-Host "Instalando dependencias..." -ForegroundColor Cyan
& $venvPython -m pip install -r $requirementsPath

Write-Host "Ambiente virtual reconstruido com sucesso." -ForegroundColor Green
