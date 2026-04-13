# Cloudflare Tunnel — Guia Completo de Deploy

**Data:** 2026-04-10  
**Status:** Pronto para produção  
**Stack:** Windows Server + Waitress + Cloudflare Tunnel

---

## Sumário Executivo

Seu sistema controle-ativos está configurado para publicação profissional via **Cloudflare Tunnel**, uma solução que:

✅ **Não requer port forwarding no roteador**  
✅ **Fornece HTTPS grátis e automático**  
✅ **Termina a criptografia na borda da Cloudflare**  
✅ **Oferece WAF e DDoS protection integrado**  
✅ **Mantém o servidor Windows local, apenas criptografado**  

**Arquitetura:**
```
Internet (HTTPS)
    ↓
Cloudflare (termina HTTPS, WAF, DDoS)
    ↓
cloudflared daemon (Windows, sa conexão saída)
    ↓
http://localhost:8000 (Waitress — HTTP local, seguro)
```

---

## 1. Arquitetura e Fluxo de Tráfego

### 1.1 Antes do Tunnel (Atual)

```
Internet
    ↓
[NAT/Firewall — não alcança servidor local]
    ↓
192.168.88.41:8000 (inacessível de fora)
```

**Limitação:** Rede corporativa atrás de NAT, sem port forwarding para servidor local.

### 1.2 Com Cloudflare Tunnel (Novo)

```
Cliente Internet (navegador)
    ↓
https://sistema.empresa.com (DNS → Cloudflare)
    ↓
Cloudflare (HTTPS termina aqui, WAF ativo)
    ↓
Tunnel Magic ™ (criptografia ponta-a-ponta)
    ↓
cloudflared.exe (Windows Server, conexão de SAÍDA)
    ↓
http://localhost:8000 (HTTP local, isolado)
    ↓
Flask/Waitress (processa requisição)
```

**Vantagens:**
- Nenhuma porta aberta no firewall/router
- cloudflared inicia conexão de SAÍDA (não entrada)
- Criptografia fim-a-fim
- Proteção WAF/DDoS da Cloudflare
- Certificado HTTPS grátis (mantido pela Cloudflare)

---

## 2. Pré-requisitos

### 2.1 Cloudflare

- [ ] Conta Cloudflare (grátis ou paga)
- [ ] Domínio registrado (ex: `empresa.com`)
- [ ] **Nameservers do domínio apontados para Cloudflare**
  ```
  NS1.CLOUDFLARE.COM
  NS2.CLOUDFLARE.COM
  ```
  ⚠️ **CRÍTICO:** Se usar registrador diferente (GoDaddy, Namecheap, etc), mude os NS para Cloudflare lá.

### 2.2 Servidor Local (Windows)

- [ ] Windows Server 2016 ou posterior
- [ ] Python 3.11+ instalado
- [ ] Waitress rodando em `http://localhost:8000`
- [ ] Acesso Administrator no Windows Server
- [ ] Conexão de internet para fora (cloudflared abre conexão de SAÍDA para Cloudflare)

### 2.3 Variáveis de Ambiente da Aplicação

Em produção, configure no `.env`:
```
ENVIRONMENT=production
PROXY_FIX_ENABLED=1
SESSION_COOKIE_SECURE=1
FLASK_DEBUG=0
```

---

## 3. Passo a Passo — Setup Cloudflared

### 3.1 Instalar Cloudflared

**Opção A: Script Automático (Recomendado)**

```powershell
.\scripts\instalar_cloudflared.ps1
```

O script:
- Baixa `cloudflared.exe` automaticamente
- Instala em `C:\cloudflared\`
- Adiciona ao PATH
- Registra como serviço Windows
- Copia template de config

**Opção B: Manual**

```powershell
# 1. Criar diretório
mkdir C:\cloudflared

# 2. Baixar cloudflared
Invoke-WebRequest -Uri "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" `
  -OutFile "C:\cloudflared\cloudflared.exe"

# 3. Adicionar ao PATH
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\cloudflared", "Machine")

# 4. Registrar serviço (próximo passo)
```

### 3.2 Autenticar com Sua Conta Cloudflare

```powershell
cloudflared tunnel login
```

Isto:
- Abre seu navegador automaticamente
- Você seleciona o domínio
- cloudflared salva credenciais em `C:\Users\<Seu Usuário>\.cloudflared\`

✅ **Resultado esperado:** Arquivo `.json` criado com suas credenciais.

### 3.3 Criar o Tunnel

```powershell
cloudflared tunnel create seu-tunnel-name
```

Exemplo:
```powershell
cloudflared tunnel create controle-ativos-prod
```

**Resultado esperado:**
```
Tunnel created with ID: 550e8400-e29b-41d4-a716-446655440000
Credentials file saved to C:\Users\Usuário\.cloudflared\550e8400-e29b-41d4-a716-446655440000.json
```

🔑 **Guarde o ID** — você precisa dele no próximo passo.

### 3.4 Editar Arquivo de Configuração

Edite: `C:\cloudflared\config.yml`

```yaml
tunnel: 550e8400-e29b-41d4-a716-446655440000
credentials-file: C:\Users\Seu_Usuario\.cloudflared\550e8400-e29b-41d4-a716-446655440000.json

ingress:
  - hostname: sistema.empresa.com
    service: http://localhost:8000
  - service: http_status:404
```

**Onde:**
- `tunnel`: ID que você copiou acima
- `credentials-file`: caminho exato do arquivo de credenciais (varie para seu usuário Windows)
- `hostname`: seu domínio público (ex: `sistema.empresa.com`)
- `service`: onde a aplicação está rodando localmente (padrão: `http://localhost:8000`)

### 3.5 Registrar Serviço Windows

```powershell
cloudflared service install --config C:\cloudflared\config.yml
```

Isto registra cloudflared como serviço Windows (`cloudflared`), que inicia automaticamente no boot.

---

## 4. Configurar DNS no Cloudflare

### 4.1 Adicionar Registro CNAME

1. Acesse **dashboard.cloudflare.com** → seu domínio
2. Menu lateral: **DNS** → **Records**
3. Clique **+ Add record**
4. Preencha:
   - **Type:** CNAME
   - **Name:** `sistema` (ou o subdomínio desejado; ex: `app`, `portal`)
   - **Target:** `550e8400-e29b-41d4-a716-446655440000.cfargotunnel.com`
   - **TTL:** Auto
   - **Proxy status:** Proxied (nuvem laranja)
5. Salve

**Resultado esperado:**
```
sistema.empresa.com CNAME → 550e8400...cfargotunnel.com
```

Aguarde propagação (geralmente < 5 minutos).

---

## 5. Configuração da Aplicação

### 5.1 Variáveis de Ambiente Críticas

Edite `.env` ou variáveis de ambiente do Windows:

```
# Ativar ProxyFix para reconhecer headers de proxy
PROXY_FIX_ENABLED=1

# Número de proxies (Cloudflare Tunnel = 1)
PROXY_FIX_X_FOR=1
PROXY_FIX_X_PROTO=1
PROXY_FIX_X_HOST=0

# Cookies seguros (obrigatório quando HTTPS ativo)
SESSION_COOKIE_SECURE=1

# Modo produção
ENVIRONMENT=production
FLASK_DEBUG=0
```

**Por que PROXY_FIX_ENABLED=1 é crítico:**

Sem ele, Flask vê:
- `request.remote_addr = 127.0.0.1` (IP do cloudflared, não do cliente real)
- `request.is_secure = False` (conexão é HTTP local)

Com cloudflared, Cloudflare adiciona headers:
- `X-Forwarded-For: <IP real do cliente>`
- `X-Forwarded-Proto: https`

ProxyFix lê esses headers e reconstitui:
- `request.remote_addr = <IP real>`
- `request.is_secure = True`

Sem isso, `SESSION_COOKIE_SECURE=1` rejeitará cookies (Flask vê HTTP não HTTPS).

### 5.2 Verificar Configuração

```powershell
curl http://localhost:8000/config-diagnostico
```

Deve retornar:
```json
{
  "ok": true,
  "is_production": true,
  "diagnostico": {
    "proxy_fix_enabled": true,
    "proxy_fix_x_proto": 1,
    ...
  },
  "alertas": []
}
```

---

## 6. Iniciar e Validar

### 6.1 Iniciar Aplicação Localmente

```powershell
# Modo de desenvolvimento com debug
python web_app/app.py

# Ou simular produção (recomendado antes de ligar tunnel)
.\scripts\simulate_production.ps1
```

Verifique que está respondendo:
```powershell
curl http://localhost:8000/health
# Resultado esperado: {"ok": true, "status": "healthy"}
```

### 6.2 Iniciar Serviço Cloudflared

```powershell
# Iniciar o serviço Windows
net start cloudflared

# Verificar status
Get-Service cloudflared
# Status deve ser "Running"
```

### 6.3 Validar Tunnel Completo

```powershell
.\scripts\validar_tunnel.ps1
```

Script validará:
- ✓ cloudflared instalado
- ✓ Serviço rodando
- ✓ Aplicação local respondendo
- ✓ Variáveis de ambiente configuradas
- ✓ Conectividade do tunnel

### 6.4 Testar via Domínio Público

```powershell
# Testar HTTPS (do seu PC local ou remoto)
curl https://sistema.empresa.com/health

# Ou no navegador
https://sistema.empresa.com/
```

**Esperado:**
- Certificado HTTPS válido (Cloudflare)
- Página de login aparece
- Sem erros 502/503

---

## 7. Monitoramento e Diagnóstico

### 7.1 Verificar Logs Locais

**Logs da aplicação Flask:**
```powershell
Get-Content .\logs\*.log -Tail 50
```

**Logs do cloudflared:**
```powershell
# Windows Event Viewer → Application
# Ou arquivo de log se configurado em config.yml
Get-Content C:\cloudflared\tunnel.log -Tail 100
```

### 7.2 Verificar Conectividade do Tunnel

```powershell
# Ver status do tunnel
cloudflared tunnel info seu-tunnel-name

# Ver conexões ativas
cloudflared tunnel routes
```

### 7.3 Dashboard Cloudflare

Acesse https://dash.cloudflare.com/ → seu domínio:

- **Analytics:** tráfego, requisições, cache
- **Security:** WAF, DDoS, taxa de ataque
- **Workers:** scripts customizados (opcional)

---

## 8. Segurança — Checklist

- [ ] `PROXY_FIX_ENABLED=1` configurado
- [ ] `SESSION_COOKIE_SECURE=1` configurado
- [ ] `/config-diagnostico` restrito a localhost (implementado)
- [ ] `FLASK_DEBUG=0` em produção
- [ ] Credenciais de DB em variáveis de ambiente (não em código)
- [ ] Certificado HTTPS da Cloudflare válido
- [ ] WAF da Cloudflare ativado (recomendado)
- [ ] Firewall do Windows Server configurado (bloqueia portas desnecessárias)

---

## 9. Troubleshooting

### 9.1 "DNS não resolve"

**Sintoma:** `nslookup sistema.empresa.com` retorna erro  
**Causa:** Nameservers não apontam para Cloudflare ou DNS não propagou  
**Solução:**
1. Confirme nameservers no registrador (GoDaddy, Namecheap, etc):
   ```
   NS1.CLOUDFLARE.COM
   NS2.CLOUDFLARE.COM
   ```
2. Aguarde propagação (até 48h, geralmente < 5 min)
3. Teste: `nslookup sistema.empresa.com`

### 9.2 "Conexão recusada (refused)"

**Sintoma:** `curl https://sistema.empresa.com` → error  
**Causa:** cloudflared não está rodando ou config.yml está errado  
**Solução:**
```powershell
# 1. Verificar serviço
Get-Service cloudflared

# 2. Verificar config
more C:\cloudflared\config.yml

# 3. Reiniciar
net stop cloudflared
net start cloudflared

# 4. Verificar logs
Get-EventLog -LogName Application -Source cloudflared -Newest 10
```

### 9.3 "ERR_TOO_MANY_REDIRECTS"

**Sintoma:** Navegador fica redirecionando HTTP → HTTPS → HTTP  
**Causa:** `SESSION_COOKIE_SECURE=1` sem HTTPS ativado, ou config HTTP em Cloudflare  
**Solução:**
1. Verificar que Cloudflare "Proxy status" está **Proxied** (nuvem laranja)
2. Verificar que `PROXY_FIX_ENABLED=1` e `PROXY_FIX_X_PROTO=1`
3. Verificar que `SESSION_COOKIE_SECURE=1`

### 9.4 "403 Forbidden — /config-diagnostico"

**Sintoma:** Acessando `/config-diagnostico` via tunnel retorna 403  
**Causa:** Proteção contra exposição de config em produção (comportamento esperado)  
**Solução:** Acessar pelo servidor local:
```powershell
curl http://localhost:8000/config-diagnostico
```

### 9.5 "Erro de credenciais cloudflared"

**Sintoma:** `cloudflared tunnel list` → "unauthorized"  
**Causa:** Arquivo de credenciais ausente ou caminho errado em config.yml  
**Solução:**
```powershell
# Re-autenticar
cloudflared tunnel login

# Copiar arquivo correto para config.yml
# Verificar que credentials-file aponta para o arquivo exato

# Testar conexão
cloudflared tunnel validate seu-tunnel-name
```

### 9.6 "502 Bad Gateway"

**Sintoma:** HTTPS funciona, mas aplicação retorna 502  
**Causa:** Waitress não está rodando em localhost:8000 ou ProxyFix quebrou algo  
**Solução:**
```powershell
# 1. Verificar que Flask está rodando
curl http://localhost:8000/health

# 2. Se sim, desabilitar ProxyFix temporariamente
# Editar .env: PROXY_FIX_ENABLED=0
# Reiniciar Waitress

# 3. Verificar logs
Get-Content .\logs\*.log -Tail 100 | grep -i error
```

---

## 10. Performance e Otimização

### 10.1 Latência

Cloudflare Tunnel adiciona mínimo overhead (~5-10ms). A maioria da latência vem de:
- Distância geográfica cliente ↔ edge Cloudflare
- Latência interna Windows Server ↔ locahost:8000

### 10.2 Largura de Banda

Cloudflare oferece largura de banda ilimitada no plano Tunnel.

### 10.3 Limites

| Limite | Valor | Nota |
|--------|-------|------|
| Concurrent connections | Ilimitado | Por default |
| Max request size | 100 MB | (Configurável) |
| Timeout | 30s (default) | (Configurável em config.yml) |

---

## 11. Mantendo Acesso Interno via IIS

Se quiser manter acesso interno via IIS (192.168.88.41:80) E acesso externo via Tunnel:

**Não há conflito.** As duas rotas coexistem:

```
Interno (LAN):
192.168.88.41:80 → IIS → Waitress:8000

Externo (Internet):
https://sistema.empresa.com → Cloudflare → cloudflared → Waitress:8000
```

Ambas chegam em `localhost:8000` mas por caminhos diferentes.

**Diferenças na configuração:**

| Cenário | PROXY_FIX_ENABLED | SESSION_COOKIE_SECURE | Notas |
|---------|-------------------|-----------------------|-------|
| Interno via IIS | 0 | 0 | HTTP local, sem proxy |
| Externo via Tunnel | 1 | 1 | HTTPS Cloudflare, precisa ProxyFix |

**Recomendação:** Ative ambas as configurações (`PROXY_FIX_ENABLED=1`, `SESSION_COOKIE_SECURE=1`). O ProxyFix é backward-compatible; em ambiente sem proxy, simplemente não faz nada.

---

## 12. Desabilitar ou Remover Tunnel

### 12.1 Parar Serviço Temporariamente

```powershell
net stop cloudflared
# Seu site fica offline
```

### 12.2 Remover Serviço Permanentemente

```powershell
cloudflared service uninstall

# (Optional) Deletar arquivos
Remove-Item C:\cloudflared -Recurse -Force
```

### 12.3 Remover Tunnel da Cloudflare

```powershell
cloudflared tunnel delete seu-tunnel-name
```

---

## 13. Renovação e Manutenção

### 13.1 Certificados HTTPS

**Cloudflare gerencia automaticamente.** Você não precisa fazer nada.

### 13.2 Atualizações de cloudflared

Periodicamente, atualize para a versão mais recente:

```powershell
# Parar serviço
net stop cloudflared

# Baixar nova versão (sobrescreve C:\cloudflared\cloudflared.exe)
.\scripts\instalar_cloudflared.ps1

# Reiniciar
net start cloudflared
```

### 13.3 Renovação de Credenciais

Se suas credenciais Cloudflare vencerem ou forem revogadas:

```powershell
cloudflared tunnel login
# Siga o OAuth novamente
```

---

## 14. Checklist Final Pré-Launch

### Código e Configuração Local
- [ ] `config.py` importa e inicializa PROXY_FIX_* vars ✓ (Claude fez)
- [ ] `web_app/app.py` aplica ProxyFix middleware ✓ (Claude fez)
- [ ] `/config-diagnostico` protege acesso a localhost ✓ (Claude fez)
- [ ] `deploy/iis/web.config` corrige X-Forwarded-Proto ✓ (Claude fez)
- [ ] `.env` possui PROXY_FIX_ENABLED=1 ✓ (você configura)
- [ ] `.env` possui SESSION_COOKIE_SECURE=1 ✓ (você configura)
- [ ] Waitress roda em `http://localhost:8000` ✓ (você verifica)

### Infraestrutura Cloudflare
- [ ] Conta Cloudflare criada e domínio adicionado ❌ (manual)
- [ ] Nameservers apontam para Cloudflare (NS1/NS2.cloudflare.com) ❌ (manual)
- [ ] cloudflared instalado e `net start cloudflared` ✓ (script + seu comando)
- [ ] Tunnel criado com `cloudflared tunnel create` ❌ (manual)
- [ ] `C:\cloudflared\config.yml` editado com seus valores ❌ (manual)
- [ ] CNAME adicionado ao DNS: `sistema.empresa.com` → `<TUNNEL_ID>.cfargotunnel.com` ❌ (manual)

### Validação
- [ ] `curl http://localhost:8000/health` → 200 ✓ (local)
- [ ] `curl https://sistema.empresa.com/health` → 200 ❌ (pós-setup tunnel)
- [ ] `.\scripts\validar_tunnel.ps1` → sem erros ❌ (pós-setup)
- [ ] Login na aplicação funciona ❌ (pós-setup)

---

## 15. Contato e Suporte

| Tópico | Recurso |
|--------|---------|
| Cloudflare Tunnel | https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/ |
| cloudflared Releases | https://github.com/cloudflare/cloudflared/releases |
| Community & Support | https://community.cloudflare.com |
| Documentação interna | docs/DEPLOYMENT.md, docs/SPRINT_2_1_FASE_C_HTTPS.md |

---

## 16. Veredito Final

✅ **Sistema PRONTO para publicação via Cloudflare Tunnel**

**O que Claude preparou:**
- ProxyFix middleware habilitado para reconhecer headers de proxy
- Proteção de endpoints internos (`/config-diagnostico`)
- Corrigido bug de X-Forwarded-Proto no IIS
- Scripts PowerShell para instalação e validação
- Documentação operacional completa

**O que você precisa fazer:**
1. Cloudflare: Conta, domínio, nameservers
2. Executar scripts: instalação, autenticação, criação do tunnel
3. Configurar: DNS CNAME, variáveis de ambiente da aplicação
4. Validar: scripts de teste, acesso público

**Tempo estimado:** 30-60 minutos (incluindo propagação DNS)

---

**Responsável:** Claude Code  
**Versão:** 1.0 (2026-04-10)  
**Pronto para produção:** SIM ✅
