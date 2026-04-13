#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Instala cloudflared como daemon Windows e cria configuração de Tunnel.

.DESCRIPTION
    Baixa cloudflared.exe da Cloudflare, instala em C:\cloudflared\,
    registra como serviço Windows e orienta a autenticação do tunnel.

    Pré-requisitos:
      - Windows Server 2016 ou superior
      - Acesso Administrator
      - Conexão de internet
      - Conta Cloudflare com domínio configurado

.EXAMPLE
    .\scripts\instalar_cloudflared.ps1
#>

param(
    [string]$CloudflaredDir = "C:\cloudflared",
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = "Stop"

Write-Host "=== Cloudflare Tunnel — Instalação no Windows ===" -ForegroundColor Cyan
Write-Host "Diretório de instalação: $CloudflaredDir" -ForegroundColor Gray

# ─────────────────────────────────────────────────
# 1. Criar diretório
# ─────────────────────────────────────────────────

Write-Host ""
Write-Host "[1/5] Criando diretório..." -ForegroundColor Cyan

if (-not (Test-Path $CloudflaredDir)) {
    New-Item -ItemType Directory -Path $CloudflaredDir -Force | Out-Null
    Write-Host "[OK] Diretório criado: $CloudflaredDir" -ForegroundColor Green
} else {
    Write-Host "[OK] Diretório já existe: $CloudflaredDir" -ForegroundColor Green
}

# ─────────────────────────────────────────────────
# 2. Baixar cloudflared.exe
# ─────────────────────────────────────────────────

Write-Host ""
Write-Host "[2/5] Baixando cloudflared.exe..." -ForegroundColor Cyan

$cloudflaredUrl = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
$cloudflaredExe = Join-Path $CloudflaredDir "cloudflared.exe"

try {
    # Usar método moderno com -SkipCertificateCheck se disponível (PS 7+)
    if ($PSVersionTable.PSVersion.Major -ge 7) {
        Invoke-WebRequest -Uri $cloudflaredUrl -OutFile $cloudflaredExe -SkipCertificateCheck
    } else {
        Invoke-WebRequest -Uri $cloudflaredUrl -OutFile $cloudflaredExe
    }
    Write-Host "[OK] cloudflared.exe baixado: $cloudflaredExe" -ForegroundColor Green
} catch {
    Write-Host "[ERRO] Falha ao baixar cloudflared: $_" -ForegroundColor Red
    Write-Host "Tente fazer download manual em: https://github.com/cloudflare/cloudflared/releases" -ForegroundColor Yellow
    exit 1
}

# ─────────────────────────────────────────────────
# 3. Adicionar ao PATH do sistema
# ─────────────────────────────────────────────────

Write-Host ""
Write-Host "[3/5] Adicionando ao PATH do sistema..." -ForegroundColor Cyan

$currentPath = [Environment]::GetEnvironmentVariable("Path", [EnvironmentVariableTarget]::Machine)
if ($currentPath -notlike "*$CloudflaredDir*") {
    $newPath = "$currentPath;$CloudflaredDir"
    [Environment]::SetEnvironmentVariable("Path", $newPath, [EnvironmentVariableTarget]::Machine)
    Write-Host "[OK] $CloudflaredDir adicionado ao PATH" -ForegroundColor Green
    Write-Host "Reinicie o PowerShell para ver a mudança refletida." -ForegroundColor Yellow
} else {
    Write-Host "[OK] $CloudflaredDir já está no PATH" -ForegroundColor Green
}

# ─────────────────────────────────────────────────
# 4. Copiar config.yml.example para config.yml
# ─────────────────────────────────────────────────

Write-Host ""
Write-Host "[4/5] Preparando arquivo de configuração..." -ForegroundColor Cyan

$configExample = Join-Path $ProjectRoot "deploy\cloudflare\config.yml.example"
$configTarget = Join-Path $CloudflaredDir "config.yml"

if (Test-Path $configExample) {
    Copy-Item -Path $configExample -Destination $configTarget -Force
    Write-Host "[OK] config.yml copiado de $configExample" -ForegroundColor Green
    Write-Host "⚠️  Edite $configTarget com seu tunnel ID e domínio antes de iniciar o serviço." -ForegroundColor Yellow
} else {
    Write-Host "[AVISO] Arquivo de exemplo não encontrado em $configExample" -ForegroundColor Yellow
    Write-Host "Crie manualmente config.yml em $CloudflaredDir com o conteúdo de deploy/cloudflare/config.yml.example" -ForegroundColor Yellow
}

# ─────────────────────────────────────────────────
# 5. Registrar como serviço Windows
# ─────────────────────────────────────────────────

Write-Host ""
Write-Host "[5/5] Registrando cloudflared como serviço Windows..." -ForegroundColor Cyan

$serviceName = "cloudflared"
$existingService = Get-Service -Name $serviceName -ErrorAction SilentlyContinue

if ($existingService) {
    Write-Host "[AVISO] Serviço $serviceName já existe." -ForegroundColor Yellow
    Write-Host "Para reinstalar, execute: net stop cloudflared; cloudflared service uninstall" -ForegroundColor Gray
} else {
    try {
        # Registrar como serviço usando cloudflared service install
        & $cloudflaredExe service install --config $configTarget
        Write-Host "[OK] Serviço cloudflared registrado com sucesso." -ForegroundColor Green
    } catch {
        Write-Host "[ERRO] Falha ao registrar serviço: $_" -ForegroundColor Red
        Write-Host "Tente manualmente: & '$cloudflaredExe' service install --config '$configTarget'" -ForegroundColor Yellow
        exit 1
    }
}

# ─────────────────────────────────────────────────
# Próximos passos
# ─────────────────────────────────────────────────

Write-Host ""
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "✅ Instalação concluída!" -ForegroundColor Green
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Green

Write-Host ""
Write-Host "📋 Próximos passos:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Autenticar cloudflared com sua conta Cloudflare:" -ForegroundColor White
Write-Host "   cloudflared tunnel login" -ForegroundColor Gray
Write-Host "   (Abrirá seu navegador para autenticação OAuth)" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Criar o tunnel (escolha um nome único):" -ForegroundColor White
Write-Host "   cloudflared tunnel create seu-tunnel-name" -ForegroundColor Gray
Write-Host "   Guarde o <TUNNEL_ID> exibido" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Editar $configTarget:" -ForegroundColor White
Write-Host "   - Substitua <ID-DO-TUNNEL> pelo TUNNEL_ID obtido" -ForegroundColor Gray
Write-Host "   - Substitua seu-dominio.com pelo domínio real" -ForegroundColor Gray
Write-Host "   - Certifique-se de que hostname e service estão corretos" -ForegroundColor Gray
Write-Host ""
Write-Host "4. Configurar DNS no Cloudflare:" -ForegroundColor White
Write-Host "   - Vá para seu domínio no dashboard Cloudflare" -ForegroundColor Gray
Write-Host "   - Crie um CNAME: seu-dominio.com → <TUNNEL_ID>.cfargotunnel.com" -ForegroundColor Gray
Write-Host ""
Write-Host "5. Iniciar o serviço:" -ForegroundColor White
Write-Host "   net start cloudflared" -ForegroundColor Gray
Write-Host ""
Write-Host "6. Validar funcionamento:" -ForegroundColor White
Write-Host "   .\scripts\validar_tunnel.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host "📖 Documentação completa:" -ForegroundColor Cyan
Write-Host "   docs/CLOUDFLARE_TUNNEL_DEPLOY.md" -ForegroundColor Gray
Write-Host ""
