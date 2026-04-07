#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Instala o Controle de Ativos como servico Windows usando NSSM.

.DESCRIPTION
    Este script usa o NSSM (Non-Sucking Service Manager) para registrar
    o Waitress como um servico Windows que inicia automaticamente com o servidor.

    Pre-requisitos:
      - Executar como Administrador
      - NSSM instalado (https://nssm.cc/download)
      - Python e dependencias instalados no virtualenv (.venv)
      - Arquivo .env configurado com as variaveis de ambiente

    Uso:
      .\deploy\nssm\install_service.ps1 -ProjectDir "C:\controle_ativos"
      .\deploy\nssm\install_service.ps1 -ProjectDir "C:\controle_ativos" -NssmPath "C:\tools\nssm.exe"
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectDir,

    [string]$NssmPath = "nssm",

    [string]$ServiceName = "controle_ativos",

    [string]$Host = "127.0.0.1",

    [int]$Port = 8000,

    [int]$Threads = 8
)

$ErrorActionPreference = "Stop"

# ─────────────────────────────────────────────────
# Validacoes
# ─────────────────────────────────────────────────

if (-not (Test-Path $ProjectDir)) {
    throw "Diretorio do projeto nao encontrado: $ProjectDir"
}

$venvPython = Join-Path $ProjectDir ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    throw "Virtualenv ausente em $venvPython. Execute scripts/setup_server.ps1 primeiro."
}

$envFile = Join-Path $ProjectDir ".env"
if (-not (Test-Path $envFile)) {
    throw "Arquivo .env nao encontrado em $envFile. Configure as variaveis de ambiente antes de instalar o servico."
}

try {
    & $NssmPath version | Out-Null
} catch {
    throw "NSSM nao encontrado. Baixe em https://nssm.cc/download e adicione ao PATH ou informe -NssmPath."
}

# ─────────────────────────────────────────────────
# Remove servico anterior se existir
# ─────────────────────────────────────────────────

$existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "[INFO] Servico '$ServiceName' ja existe. Parando e removendo..." -ForegroundColor Yellow
    & $NssmPath stop $ServiceName confirm
    & $NssmPath remove $ServiceName confirm
    Start-Sleep -Seconds 2
}

# ─────────────────────────────────────────────────
# Instala o servico
# ─────────────────────────────────────────────────

Write-Host "[INFO] Instalando servico '$ServiceName'..." -ForegroundColor Cyan

$waitressArgs = "-m waitress --listen=${Host}:${Port} --threads=$Threads --ident=controle-ativos wsgi:application"

& $NssmPath install $ServiceName $venvPython $waitressArgs

# Diretorio de trabalho (onde wsgi.py esta)
& $NssmPath set $ServiceName AppDirectory $ProjectDir

# Tipo de inicializacao automatica
& $NssmPath set $ServiceName Start SERVICE_AUTO_START

# Carrega variaveis de ambiente do arquivo .env
# NSSM nao le .env nativamente — usamos o bloco de variaveis de ambiente
$envContent = Get-Content $envFile | Where-Object { $_ -match "^\s*[^#].*=.*" }
$envVars = @()
foreach ($line in $envContent) {
    $line = $line.Trim()
    if ($line -and -not $line.StartsWith("#")) {
        $envVars += $line
    }
}
$envBlock = $envVars -join "`n"
& $NssmPath set $ServiceName AppEnvironmentExtra $envBlock

# Redireciona stdout e stderr para arquivos de log
$logsDir = Join-Path $ProjectDir "logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
}

& $NssmPath set $ServiceName AppStdout (Join-Path $logsDir "waitress_stdout.log")
& $NssmPath set $ServiceName AppStderr (Join-Path $logsDir "waitress_stderr.log")
& $NssmPath set $ServiceName AppRotateFiles 1
& $NssmPath set $ServiceName AppRotateBytes 10485760

# Reinicia automaticamente em caso de falha (ate 3 tentativas, intervalo 5s)
& $NssmPath set $ServiceName AppRestartDelay 5000

# ─────────────────────────────────────────────────
# Inicia o servico
# ─────────────────────────────────────────────────

Write-Host "[INFO] Iniciando servico..." -ForegroundColor Cyan
& $NssmPath start $ServiceName

Start-Sleep -Seconds 3

$svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($svc -and $svc.Status -eq "Running") {
    Write-Host "[OK] Servico '$ServiceName' iniciado com sucesso." -ForegroundColor Green
    Write-Host "[OK] Waitress escutando em ${Host}:${Port}" -ForegroundColor Green
    Write-Host ""
    Write-Host "Proximos passos:" -ForegroundColor Cyan
    Write-Host "  1. Verifique o health: Invoke-WebRequest http://127.0.0.1:$Port/health"
    Write-Host "  2. Configure o IIS como reverse proxy usando deploy\iis\web.config"
    Write-Host "  3. Configure TLS no IIS para HTTPS"
} else {
    Write-Host "[ERRO] Servico nao iniciou corretamente." -ForegroundColor Red
    Write-Host "Verifique os logs em: $logsDir" -ForegroundColor Yellow
    exit 1
}
