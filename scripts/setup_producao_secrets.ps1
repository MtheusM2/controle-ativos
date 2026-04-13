# =============================================================================
# SETUP DE SECRETS EM PRODUCAO - WINDOWS SERVER
# =============================================================================
#
# Este script configura variaveis de ambiente necessarias para producao.
#
# REQUISITOS:
# - Executar como Administrator
# - Python 3.11+ instalado
# - Arquivo .env.production em controle_ativos/
#
# USO:
#   powershell -ExecutionPolicy Bypass -File scripts\setup_producao_secrets.ps1
#
# =============================================================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SETUP DE SECRETS EM PRODUCAO" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verifica se esta sendo executado como admin
$isAdmin = ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERRO: Este script deve ser executado como Administrator." -ForegroundColor Red
    Write-Host "Abra PowerShell como administrador e tente novamente." -ForegroundColor Red
    exit 1
}

Write-Host "Status: Executando como Administrator OK" -ForegroundColor Green
Write-Host ""

# Define o caminho do projeto
$projectPath = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$scriptsPath = Join-Path $projectPath "scripts"

Write-Host "Caminho do projeto: $projectPath" -ForegroundColor Yellow
Write-Host ""

# Opcao 1: Gerar secrets automaticamente
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "OPCAO 1: GERAR SECRETS AUTOMATICAMENTE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$generateScript = Join-Path $scriptsPath "gerar_secrets_seguros.py"

if (Test-Path $generateScript) {
    Write-Host "Executando gerador de secrets..." -ForegroundColor Yellow
    Write-Host ""

    python $generateScript

    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "Secrets gerados com sucesso!" -ForegroundColor Green
    } else {
        Write-Host "ERRO ao gerar secrets." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "Script nao encontrado: $generateScript" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PROXIMAS ETAPAS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Copie os valores de FLASK_SECRET_KEY, APP_PEPPER e DB_PASSWORD acima"
Write-Host ""
Write-Host "2. Configure como variaveis de ambiente do Windows (execute como Admin):"
Write-Host ""
Write-Host "   setx FLASK_SECRET_KEY `"<valor_aqui>`" /M" -ForegroundColor Yellow
Write-Host "   setx APP_PEPPER `"<valor_aqui>`" /M" -ForegroundColor Yellow
Write-Host "   setx DB_PASSWORD `"<valor_aqui>`" /M" -ForegroundColor Yellow
Write-Host "   setx ENVIRONMENT `"production`" /M" -ForegroundColor Yellow
Write-Host ""
Write-Host "3. Atualize a senha do usuario 'opus_app' no MySQL com o valor de DB_PASSWORD"
Write-Host ""
Write-Host "4. Feche todos os terminais PowerShell e abra um novo para validar carregamento"
Write-Host ""
Write-Host "5. Valide o carregamento executando:"
Write-Host ""
Write-Host "   python -c `"from config import diagnosticar_config; import json; print(json.dumps(diagnosticar_config(), indent=2))`"" -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Setup concluido!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
