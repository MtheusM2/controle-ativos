#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Bootstrap completo para novo servidor Windows.

.DESCRIPTION
    Prepara o ambiente de producao no Windows Server:
      - Cria o .env a partir do .env.example
      - Cria o virtualenv Python e instala dependencias
      - Cria pastas operacionais (logs, uploads)
      - Executa diagnostico de configuracao

    Uso:
      .\scripts\setup_server.ps1
      .\scripts\setup_server.ps1 -PythonCommand "C:\Python311\python.exe"
#>

param(
    [string]$PythonCommand = "python"
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

Write-Host "=== Controle de Ativos — Setup de Servidor Windows ===" -ForegroundColor Cyan
Write-Host "Diretorio do projeto: $projectRoot" -ForegroundColor Gray

# ─────────────────────────────────────────────────
# 1. Verifica Python
# ─────────────────────────────────────────────────

Write-Host ""
Write-Host "[1/5] Verificando Python..." -ForegroundColor Cyan

try {
    $pyVersion = & $PythonCommand --version 2>&1
    Write-Host "[OK] $pyVersion" -ForegroundColor Green
} catch {
    throw "Python nao encontrado usando '$PythonCommand'. Instale o Python 3.11+ e adicione ao PATH."
}

# ─────────────────────────────────────────────────
# 2. Variaveis de ambiente
# ─────────────────────────────────────────────────

Write-Host ""
Write-Host "[2/5] Configurando variaveis de ambiente..." -ForegroundColor Cyan

if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "[ATENCAO] .env criado a partir do .env.example." -ForegroundColor Yellow
        Write-Host "          EDITE o arquivo .env com os valores reais antes de continuar!" -ForegroundColor Yellow
    } else {
        throw "Arquivo .env.example nao encontrado. Crie o .env manualmente."
    }
} else {
    Write-Host "[OK] .env ja existe." -ForegroundColor Green
}

# ─────────────────────────────────────────────────
# 3. Ambiente virtual Python
# ─────────────────────────────────────────────────

Write-Host ""
Write-Host "[3/5] Configurando virtualenv..." -ForegroundColor Cyan

$venvPath = Join-Path $projectRoot ".venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"

if (-not (Test-Path $venvPath)) {
    Write-Host "Criando virtualenv..." -ForegroundColor Gray
    & $PythonCommand -m venv $venvPath
    Write-Host "[OK] Virtualenv criado." -ForegroundColor Green
} else {
    Write-Host "[OK] Virtualenv ja existe." -ForegroundColor Green
}

Write-Host "Atualizando pip..." -ForegroundColor Gray
& $venvPython -m pip install --upgrade pip --quiet

Write-Host "Instalando dependencias..." -ForegroundColor Gray
& $venvPython -m pip install -r requirements.txt --quiet

Write-Host "[OK] Dependencias instaladas." -ForegroundColor Green

# ─────────────────────────────────────────────────
# 4. Diretorios operacionais
# ─────────────────────────────────────────────────

Write-Host ""
Write-Host "[4/5] Criando diretorios operacionais..." -ForegroundColor Cyan

$dirs = @(
    "logs",
    "web_app\static\uploads",
    "web_app\static\uploads\ativos"
)

foreach ($dir in $dirs) {
    $fullPath = Join-Path $projectRoot $dir
    if (-not (Test-Path $fullPath)) {
        New-Item -ItemType Directory -Path $fullPath | Out-Null
        Write-Host "[OK] Criado: $dir" -ForegroundColor Green
    } else {
        Write-Host "[OK] Ja existe: $dir" -ForegroundColor Gray
    }
}

# ─────────────────────────────────────────────────
# 5. Diagnostico de configuracao
# ─────────────────────────────────────────────────

Write-Host ""
Write-Host "[5/5] Executando diagnostico de configuracao..." -ForegroundColor Cyan

try {
    & $venvPython scripts\diagnose_runtime_config.py
} catch {
    Write-Host "[AVISO] Diagnostico falhou — verifique o .env e a conexao com o banco." -ForegroundColor Yellow
}

# ─────────────────────────────────────────────────
# Resumo
# ─────────────────────────────────────────────────

Write-Host ""
Write-Host "=== Setup concluido ===" -ForegroundColor Green
Write-Host ""
Write-Host "Proximos passos:" -ForegroundColor Cyan
Write-Host "  1. Edite .env com as credenciais reais do banco e da aplicacao"
Write-Host "  2. Aplique o schema no banco:"
Write-Host "     mysql -u root -p < database\schema.sql"
Write-Host "  3. Instale o servico Windows com NSSM (como Administrador):"
Write-Host "     .\deploy\nssm\install_service.ps1 -ProjectDir `"$projectRoot`""
Write-Host "  4. Configure o IIS usando deploy\iis\web.config"
Write-Host "  5. Verifique: Invoke-WebRequest http://127.0.0.1:8000/health"
