<#
.SYNOPSIS
    Valida a instalação e conectividade do Cloudflare Tunnel.

.DESCRIPTION
    Verifica:
      - cloudflared instalado e no PATH
      - Serviço cloudflared ativo
      - Aplicação Flask respondendo em localhost:8000
      - Variáveis de ambiente críticas
      - Conectividade do tunnel

.EXAMPLE
    .\scripts\validar_tunnel.ps1
#>

param(
    [string]$AppUrl = "http://localhost:8000",
    [string]$HealthEndpoint = "/health",
    [int]$Timeout = 5
)

$ErrorActionPreference = "Continue"
$passCount = 0
$failCount = 0

Write-Host "=== Validação de Cloudflare Tunnel ===" -ForegroundColor Cyan
Write-Host ""

# ─────────────────────────────────────────────────
# 1. Verificar cloudflared no PATH
# ─────────────────────────────────────────────────

Write-Host "[1/6] Verificando se cloudflared está no PATH..." -ForegroundColor Cyan

try {
    $version = & cloudflared --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[✓] cloudflared encontrado:" -ForegroundColor Green
        Write-Host "    $version" -ForegroundColor Green
        $passCount++
    } else {
        throw "cloudflared não respondeu"
    }
} catch {
    Write-Host "[✗] cloudflared não encontrado no PATH" -ForegroundColor Red
    Write-Host "    Instale com: .\scripts\instalar_cloudflared.ps1" -ForegroundColor Yellow
    $failCount++
}

# ─────────────────────────────────────────────────
# 2. Verificar se serviço cloudflared está rodando
# ─────────────────────────────────────────────────

Write-Host ""
Write-Host "[2/6] Verificando serviço cloudflared..." -ForegroundColor Cyan

$svc = Get-Service -Name "cloudflared" -ErrorAction SilentlyContinue

if ($svc) {
    if ($svc.Status -eq "Running") {
        Write-Host "[✓] Serviço cloudflared está ativo" -ForegroundColor Green
        $passCount++
    } else {
        Write-Host "[⚠] Serviço cloudflared está parado (Status: $($svc.Status))" -ForegroundColor Yellow
        Write-Host "    Inicie com: net start cloudflared" -ForegroundColor Yellow
        $failCount++
    }
} else {
    Write-Host "[✗] Serviço cloudflared não encontrado" -ForegroundColor Red
    Write-Host "    Registre com: .\scripts\instalar_cloudflared.ps1" -ForegroundColor Yellow
    $failCount++
}

# ─────────────────────────────────────────────────
# 3. Verificar aplicação local (Flask)
# ─────────────────────────────────────────────────

Write-Host ""
Write-Host "[3/6] Verificando aplicação local em $AppUrl..." -ForegroundColor Cyan

try {
    $response = Invoke-WebRequest -Uri "$AppUrl$HealthEndpoint" -TimeoutSec $Timeout -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        $content = $response.Content | ConvertFrom-Json -ErrorAction SilentlyContinue
        if ($content.ok -eq $true) {
            Write-Host "[✓] Aplicação respondendo em $AppUrl" -ForegroundColor Green
            Write-Host "    Health check: OK" -ForegroundColor Green
            $passCount++
        } else {
            Write-Host "[⚠] Aplicação respondendo mas health check retornou false" -ForegroundColor Yellow
            $failCount++
        }
    }
} catch {
    Write-Host "[✗] Aplicação não está respondendo" -ForegroundColor Red
    Write-Host "    URL: $AppUrl" -ForegroundColor Gray
    Write-Host "    Erro: $($_.Exception.Message)" -ForegroundColor Gray
    Write-Host "    Inicie com: .\scripts\simulate_production.ps1" -ForegroundColor Yellow
    $failCount++
}

# ─────────────────────────────────────────────────
# 4. Verificar PROXY_FIX_ENABLED
# ─────────────────────────────────────────────────

Write-Host ""
Write-Host "[4/6] Verificando configuração de ProxyFix..." -ForegroundColor Cyan

# Tentar ler do .env se existir
$envFile = Join-Path (Split-Path -Parent $PSScriptRoot) ".env"
$proxyFixEnabled = $false

if (Test-Path $envFile) {
    $envContent = Get-Content $envFile -Raw
    if ($envContent -match "PROXY_FIX_ENABLED\s*=\s*1") {
        $proxyFixEnabled = $true
        Write-Host "[✓] PROXY_FIX_ENABLED=1 configurado (esperado para produção)" -ForegroundColor Green
        $passCount++
    } elseif ($envContent -match "PROXY_FIX_ENABLED\s*=\s*0") {
        Write-Host "[⚠] PROXY_FIX_ENABLED=0 (desenvolvimento)" -ForegroundColor Yellow
        Write-Host "    Configure como 1 em produção com Cloudflare Tunnel" -ForegroundColor Yellow
        $failCount++
    }
} else {
    Write-Host "[⚠] Arquivo .env não encontrado (esperado em produção)" -ForegroundColor Yellow
    $failCount++
}

# ─────────────────────────────────────────────────
# 5. Verificar SESSION_COOKIE_SECURE
# ─────────────────────────────────────────────────

Write-Host ""
Write-Host "[5/6] Verificando SESSION_COOKIE_SECURE..." -ForegroundColor Cyan

if (Test-Path $envFile) {
    $envContent = Get-Content $envFile -Raw
    if ($envContent -match "SESSION_COOKIE_SECURE\s*=\s*1") {
        Write-Host "[✓] SESSION_COOKIE_SECURE=1 (requerido em produção)" -ForegroundColor Green
        $passCount++
    } elseif ($envContent -match "SESSION_COOKIE_SECURE\s*=\s*0") {
        Write-Host "[⚠] SESSION_COOKIE_SECURE=0 (apenas em desenvolvimento/HTTP)" -ForegroundColor Yellow
        $failCount++
    }
}

# ─────────────────────────────────────────────────
# 6. Listar comandos úteis
# ─────────────────────────────────────────────────

Write-Host ""
Write-Host "[6/6] Resumo de comandos úteis:" -ForegroundColor Cyan

$commands = @(
    @{ Comando = "cloudflared tunnel list"; Desc = "Listar tunnels criados" },
    @{ Comando = "cloudflared tunnel info seu-tunnel"; Desc = "Ver detalhes do tunnel" },
    @{ Comando = "net start cloudflared"; Desc = "Iniciar serviço" },
    @{ Comando = "net stop cloudflared"; Desc = "Parar serviço" },
    @{ Comando = "cloudflared service uninstall"; Desc = "Desinstalar serviço Windows" },
    @{ Comando = "curl http://localhost:8000/config-diagnostico"; Desc = "Diagnosticar config local" }
)

foreach ($cmd in $commands) {
    Write-Host "  $($cmd.Comando)" -ForegroundColor Gray
    Write-Host "    → $($cmd.Desc)" -ForegroundColor DarkGray
}

# ─────────────────────────────────────────────────
# Resultado final
# ─────────────────────────────────────────────────

Write-Host ""
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Resultado da validação:" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan

$total = $passCount + $failCount
Write-Host "✓ Passou: $passCount/$total" -ForegroundColor Green
Write-Host "✗ Falhou: $failCount/$total" -ForegroundColor Red

Write-Host ""

if ($failCount -eq 0) {
    Write-Host "🎉 Todas as verificações passaram!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Próximo passo: Acessar seu domínio público e validar que o tunnel está funcionando." -ForegroundColor Green
    exit 0
} else {
    Write-Host "⚠️  Algumas verificações falharam. Revise acima." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Documentação: docs/CLOUDFLARE_TUNNEL_DEPLOY.md" -ForegroundColor Yellow
    exit 1
}
