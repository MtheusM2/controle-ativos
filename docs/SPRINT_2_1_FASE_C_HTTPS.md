# FASE C — HTTPS e Cookies Seguros
## Sprint 2.1 Final

**Data:** 2026-04-10  
**Status:** Documentação + Preparação para HTTPS  
**Prioridade:** Crítica (para produção plena)

---

## 1. Estado Atual de Segurança de Cookies

### 1.1 Configuração de Cookies Flask

| Propriedade | Valor | Função | Status |
|-------------|-------|--------|--------|
| `HTTPONLY` | True | Bloqueie acesso via JavaScript (XSS) | ✅ OK |
| `SAMESITE` | "Lax" | Previne CSRF simplificado | ✅ OK |
| `SECURE` | Variável | Cookie enviado apenas em HTTPS | ⚠️ Condicional |
| Lifetime | 120 min | Tempo de vida da sessão | ✅ OK |

**Resumo:** Cookies estão bem configurados para desenvolvimento. Em produção com HTTPS, apenas uma variável precisa mudar.

---

## 2. Estratégia de HTTPS

### 2.1 Por Ambiente

#### Desenvolvimento Local

```
Cliente → HTTP → localhost:5000
         (sem HTTPS)

SESSION_COOKIE_SECURE=0 (padrão)
↓
Cookie enviado em HTTP (OK para teste local)
```

**Comportamento:** Funciona normalmente sem certificado.

#### Homologação Interna

```
Cliente (intranet) → HTTP → IIS/Windows Server
                   (sem HTTPS na rede interna)

SESSION_COOKIE_SECURE=0 (padrão)
↓
Cookie enviado em HTTP (aceitável em LAN corporativa)
```

**Comportamento:** Funciona sem certificado; risco baixo em rede corporativa.

#### Produção/Internet

```
Cliente → HTTPS → IIS (port 443) → HTTP → Waitress (port 8000)
       (com certificado SSL/TLS)

SESSION_COOKIE_SECURE=1 (obrigatório)
↓
Cookie enviado apenas em HTTPS
```

**Comportamento:** Cookie rejeitado se cliente tentar HTTP; força HTTPS.

### 2.2 Configuração de Variáveis por Ambiente

```
DESENVOLVIMENTO:
  SESSION_COOKIE_SECURE=0
  (padrão em .env)

HOMOLOGAÇÃO:
  SESSION_COOKIE_SECURE=0 ou 1 (opcional)
  Se estiver em intranet: 0
  Se tiver HTTPS: 1

PRODUÇÃO:
  SESSION_COOKIE_SECURE=1 (obrigatório)
  HTTPS deve estar ativo no IIS
```

---

## 3. O Que Foi Implementado

### 3.1 Rule de Redirect HTTP→HTTPS no web.config

**Adição:** Rule "Force HTTPS" em `deploy/iis/web.config`

```xml
<rule name="Force HTTPS" stopProcessing="true" enabled="false">
  <match url="(.*)" />
  <conditions>
    <add input="{HTTPS}" pattern="off" />
  </conditions>
  <action type="Redirect" url="https://{HTTP_HOST}{REQUEST_URI}" redirectType="Permanent" />
</rule>
```

**Status:** Desabilitada por padrão (`enabled="false"`)

**Ativação:** Quando certificado HTTPS for instalado no IIS:
1. Instalar certificado no IIS
2. Editar web.config: mudar `enabled="false"` para `enabled="true"`
3. Recarregar site IIS

**Resultado:** Toda requisição HTTP será redirecionada para HTTPS com status 301.

### 3.2 Documentação de Cookies em Código

**Adição:** Comentários explicativos em `web_app/app.py`

```python
# SESSION_COOKIE_HTTPONLY: Cookie nao acessivel por JavaScript
SESSION_COOKIE_HTTPONLY=True,

# SESSION_COOKIE_SAMESITE: Previne CSRF simples
SESSION_COOKIE_SAMESITE="Lax",

# SESSION_COOKIE_SECURE: Cookie apenas em HTTPS
# Desenvolvimento: False (HTTP local)
# Producao: True (quando HTTPS ativo)
SESSION_COOKIE_SECURE=SESSION_COOKIE_SECURE,
```

### 3.3 Headers de Segurança (Já Existentes)

**Verificação confirmada:** web.config já possui headers seguros:
- `X-Content-Type-Options: nosniff` (previne MIME sniffing)
- `X-Frame-Options: DENY` (clickjacking)
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: geolocation=(), camera=(), microphone=()`
- `Content-Security-Policy` (básica)

**Status:** ✅ OK, nenhuma mudança necessária.

---

## 4. Impacto de HTTPS em Diferentes Contextos

### 4.1 IIS + Reverse Proxy

```
Cliente HTTPS request (porta 443)
  ↓
IIS recebe em HTTPS
  ↓
IIS desencripta (tem certificado)
  ↓
IIS → Waitress em HTTP (127.0.0.1:8000)
  ↓
Waitress recebe em HTTP (confiável; é localhost)
  ↓
Flask vê `HTTPS=on` em server variables (setado por IIS)
```

**Impacto na aplicação:**
- Flask recebe `HTTPS` via header `HTTP_X_FORWARDED_PROTO` (setado por IIS)
- `obter_ip_cliente()` usa `X-Forwarded-For` corretamente
- `SESSION_COOKIE_SECURE=1` é seguro (IIS garante HTTPS end-to-end com cliente)

**Validação:**
```python
# No Flask, confirmar que está vendo HTTPS
from flask import request

print(request.environ.get('HTTP_X_FORWARDED_PROTO'))  # Deve ser 'https'
print(request.headers.get('X-Forwarded-Proto'))        # Deve ser 'https'
```

### 4.2 Waitress Direto (sem IIS)

**Não recomendado para produção**, mas se for necessário:

```
Cliente HTTPS request (porta 8000)
  ↓
Waitress com certificado SSL/TLS
  ↓
Flask vê HTTPS=on nativamente
```

**Configuração:** Waitress pode usar certificado via flag:
```powershell
python -m waitress \
  --cert=C:\path\to\cert.pem \
  --key=C:\path\to\key.pem \
  wsgi:application
```

**Status:** Não implementado (IIS é o cenário esperado).

---

## 5. Checklist: Ativar HTTPS em Produção

### Pré-requisitos

- [ ] Certificado SSL/TLS válido obtido (Let's Encrypt, DigiCert, etc.)
- [ ] Certificado instalado no Windows Server / IIS
- [ ] HTTPS binding criado no site IIS (porta 443)
- [ ] Certificado não está expirado
- [ ] Firewall permite porta 443 de entrada

### Passos de Ativação

1. **Instalar certificado no Windows Server**

   ```powershell
   # Importar certificado (como Administrator)
   Import-PfxCertificate -FilePath C:\path\cert.pfx -CertStoreLocation Cert:\LocalMachine\My -Password (Read-Host "Senha")
   ```

2. **Criar binding HTTPS no site IIS**

   ```
   IIS Manager → site "controle-ativos"
   → Edit Site → Add Binding
   → Type: https, Port: 443, SSL Certificate: <seu_certificado>
   ```

3. **Ativar rule de redirect HTTP→HTTPS**

   Editar `deploy/iis/web.config`:
   ```xml
   <rule name="Force HTTPS" stopProcessing="true" enabled="true">  <!-- Mudar enabled para true -->
   ```

4. **Atualizar variáveis de ambiente**

   ```powershell
   setx SESSION_COOKIE_SECURE "1" /M
   setx HTTPS "on" /M
   ```

5. **Reiniciar aplicação**

   ```powershell
   # Reiniciar serviço NSSM (Waitress)
   net stop controle-ativos-waitress
   net start controle-ativos-waitress
   ```

6. **Validar**

   ```
   Navegador: https://seu_servidor/
   ↓
   Redireciona automaticamente se você tentar http://seu_servidor/
   ↓
   Cookie de sessão é enviado com flag Secure
   ```

---

## 6. Obtenção de Certificado

### Opção A: Let's Encrypt (Gratuito)

**Para Windows Server:**
1. Instalar Certbot para Windows
2. Obter certificado:
   ```
   certbot certonly --standalone -d seu_dominio.com
   ```
3. Converter para PFX:
   ```
   openssl pkcs12 -export -in cert.pem -inkey key.pem -out cert.pfx
   ```

**Vantagem:** Gratuito, renovação automática possível  
**Desvantagem:** Requer validação de domínio

### Opção B: Certificado Corporativo

**Se empresa já tem certificado:**
1. Obter arquivo `.pfx` ou `.crt` + `.key`
2. Importar no Windows Server (veja Passo 1 acima)
3. Usar em binding IIS

**Vantagem:** Já validado, não expiração inesperada  
**Desvantagem:** Costo; sem renovação automática

### Opção C: Self-signed (Desenvolvimento)

**Para teste local/homologação:**
```powershell
New-SelfSignedCertificate -DnsName localhost -CertStoreLocation Cert:\LocalMachine\My
```

**Aviso:** Navegadores alertarão "certificado não confiável"  
**Uso:** Apenas para teste; nunca produção

---

## 7. Testes de Validação Pós-Ativação HTTPS

### Teste 1: Certificado Válido

```powershell
# Windows
certutil -verifystore My

# Ou via PowerShell
Get-ChildItem -Path Cert:\LocalMachine\My | Where {$_.Subject -like "*seu_dominio*"}
```

**Esperado:** Certificado listado sem erros.

### Teste 2: Acesso HTTPS Funciona

```bash
curl https://seu_servidor/health
```

**Esperado:** Resposta 200 com JSON `{"ok": true}`.

### Teste 3: Redirect HTTP→HTTPS

```bash
curl -i http://seu_servidor/  # Sem HTTPS
```

**Esperado:** Resposta 301/302 com `Location: https://seu_servidor/`

### Teste 4: Cookie é Secure

```bash
# Acessar endpoint de login e verificar headers
curl -i https://seu_servidor/login

# Procurar por:
# Set-Cookie: session=...; Path=/; Secure; HttpOnly; SameSite=Lax
```

**Esperado:** Flag `Secure` presente.

### Teste 5: Diagnóstico de Configuração

```bash
curl https://seu_servidor/config-diagnostico
```

**Esperado:**
```json
{
  "is_production": true,
  "diagnostico": {
    ...
  },
  "alertas": []
}
```

---

## 8. Troubleshooting

### Problema: Cookie rejeitado no navegador

**Sintoma:** Sessão não persiste, login sempre retorna 401

**Causa:** `SESSION_COOKIE_SECURE=1` mas HTTPS não está ativo

**Solução:**
1. Validar que HTTPS está realmente ativo: `curl -I https://seu_servidor/`
2. Verificar que IIS está enviando `HTTPS=on` header
3. Verificar que regra Force HTTPS não está duplicada

### Problema: Certificado expirado

**Sintoma:** Navegador avisa "HTTPS não confiável", erro de TLS

**Causa:** Certificado venceu

**Solução:**
1. Renovar certificado (Let's Encrypt: `certbot renew`)
2. Importar novo certificado no Windows
3. Atualizar binding IIS
4. Reiniciar site

### Problema: Redirect HTTP→HTTPS resulta em loop

**Sintoma:** Navegador fica redirecionando (erro 310)

**Causa:** Rule habilitada mas HTTPS ainda não está configurado no IIS

**Solução:**
1. Desabilitar rule temporariamente: `enabled="false"`
2. Instalar certificado e binding HTTPS
3. Reabilitar rule

---

## 9. Checklist Pré-Deploy HTTPS

Antes de ativar HTTPS em produção:

- [ ] Certificado obtido e validado
- [ ] Certificado instalado no Windows Server
- [ ] HTTPS binding criado no IIS
- [ ] Certificado não está expirado
- [ ] Firewall permite porta 443
- [ ] SESSION_COOKIE_SECURE será setado como `1`
- [ ] Rule "Force HTTPS" está pronta para ativar
- [ ] Plano de rollback se algo der errado
- [ ] Equipe notificada sobre downtime (breve)

---

## 10. Veredito da Fase C

✅ **HTTPS está pronto para ativação.**

**Implementado:**
- Rule de redirect HTTP→HTTPS em web.config (desabilitada por padrão)
- Documentação de cookies em código
- Checklist de ativação passo-a-passo
- Procedimento de validação

**Risco residual:** Certificado é responsabilidade de infraestrutura (fora escopo de código).

**Próximo passo:** Fase D (Checklist de Deployment Seguro).

---

## 11. Referência Rápida

### Desenvolvimento Local
```
SESSION_COOKIE_SECURE=0
ENVIRONMENT=development
Acesso: http://localhost:5000
```

### Homologação (sem HTTPS)
```
SESSION_COOKIE_SECURE=0
ENVIRONMENT=staging
Acesso: http://seu_servidor/
```

### Homologação (com HTTPS)
```
SESSION_COOKIE_SECURE=1
ENVIRONMENT=staging
Acesso: https://seu_servidor/
```

### Produção
```
SESSION_COOKIE_SECURE=1
ENVIRONMENT=production
HTTPS=on
Acesso: https://seu_dominio.com/
Redirect: http://seu_dominio.com/ → https://seu_dominio.com/
```

---

**Responsável:** Claude Code  
**Data:** 2026-04-10  
**Status:** Fase C concluída. Pronto para Fase D (Checklist de Deployment).
