# FASE E — Hardening da Aplicação (Parte 2)

**Data:** 2026-04-10  
**Status:** Mapeamento + Priorização  
**Prioridade:** Alta

---

## 1. O que já está bem implementado

### ✅ Autenticação e Sessão

| Item | Status | Evidência |
|------|--------|-----------|
| Hash de senha | ✅ OK | PBKDF2 + pepper em utils/crypto.py |
| Session cookie HTTPONLY | ✅ OK | SESSION_COOKIE_HTTPONLY=True em web_app/app.py |
| Session cookie SAMESITE | ✅ OK | SESSION_COOKIE_SAMESITE="Lax" |
| Session cookie SECURE | ✅ PREPARADO | Controlado por variável, ativar em produção |
| Session lifetime | ✅ OK | 120 min, configurável |
| Bloqueio por tentativas | ✅ OK | 5 tentativas, 15 min bloqueio |

### ✅ Proteção de Rotas

| Item | Status | Evidência |
|------|--------|-----------|
| Autenticação obrigatória | ✅ OK | Verifica session.get("user_id") em rotas |
| CSRF em formulários | ✅ OK | Token CSRF gerado e validado em utils/csrf.py |
| Isolamento por empresa | ✅ OK | Usuários só veem ativos da própria empresa |
| Controle de acesso | ✅ OK | Perfis e permissões implementados (Fase B) |

### ✅ Headers de Segurança

| Item | Status | Localização |
|------|--------|------------|
| X-Content-Type-Options | ✅ OK | deploy/iis/web.config |
| X-Frame-Options: DENY | ✅ OK | deploy/iis/web.config |
| Referrer-Policy | ✅ OK | deploy/iis/web.config |
| Permissions-Policy | ✅ OK | deploy/iis/web.config |
| CSP básica | ✅ OK | deploy/iis/web.config |

### ✅ Banco de Dados

| Item | Status | Detalhe |
|------|--------|--------|
| Prepared statements | ✅ OK | Parâmetros %s em todas queries |
| Usuário restrito | ✅ OK | opus_app sem GRANT, DROP |
| Foreign keys | ✅ OK | Integridade referencial |
| Índices | ✅ OK | Nas colunas críticas |

### ✅ Upload de Arquivos

| Item | Status | Detalhe |
|------|--------|--------|
| Limite de tamanho | ✅ OK | 10 MB (MAX_CONTENT_LENGTH) |
| Extensões permitidas | ✅ OK | .pdf, .png, .jpg, .jpeg, .webp |
| Validação MIME type | ✅ OK | Verificação de tipo de arquivo |
| Nomes seguros | ✅ OK | secure_filename() do Werkzeug |
| Bloqueio de acesso direto | ✅ OK | IIS bloqueia /static/uploads/ |

### ✅ Logging e Auditoria

| Item | Status | Detalhe |
|------|--------|--------|
| Auditoria de ações críticas | ✅ OK | Tabela auditoria_eventos (Fase C) |
| Rastreamento de IP | ✅ OK | Capturado em logs |
| Rastreamento de usuário | ✅ OK | usuario_id registrado |
| Logs estruturados | ✅ OK | utils/logging_config.py |

---

## 2. Mapeamento de Itens Pendentes

### 🔴 CRÍTICOS — Devem ser feitos antes de produção plena

#### 2.1 HTTPS e Certificado SSL

**O que está faltando:**
- [ ] Certificado SSL/TLS instalado no IIS
- [ ] Redirecionamento HTTP → HTTPS automático
- [ ] Teste de handshake TLS
- [ ] Validação de criptografia end-to-end

**Por quê crítico:**
- Dados sensíveis (credenciais, emails) transmitidos em plaintext sem HTTPS
- Vulnerabilidade a man-in-the-middle attack
- Bloqueador de produção corporativa

**Implementação:**
```
Responsabilidade: Infraestrutura / Ops
Esforço: 2-4 horas (obtenção de certificado + instalação)
Teste: curl -I https://[servidor] (validar status 200)
```

**Rule para web.config (adicionar):**
```xml
<rule name="Force HTTPS" stopProcessing="true">
  <match url="(.*)" />
  <conditions>
    <add input="{HTTPS}" pattern="off" />
  </conditions>
  <action type="Redirect" url="https://{HTTP_HOST}{REQUEST_URI}" />
</rule>
```

#### 2.2 Estratégia de Secrets

**O que está faltando:**
- [ ] .env em plaintext é inseguro em produção
- [ ] Senha DB em arquivo acessível
- [ ] FLASK_SECRET_KEY e APP_PEPPER não rotacionados

**Por quê crítico:**
- Se servidor for comprometido, credenciais do BD expostas
- Comprometimento de BD permite acesso a todas as contas
- Sem rotação, período de exposição indefinido

**Opções de implementação:**

**Opção A — Variáveis de ambiente do Windows (mínimo viável)**
```powershell
# Em setup do servidor
setx DB_PASSWORD "nova_senha_segura" /M
setx FLASK_SECRET_KEY "nova_chave_secreta" /M
setx APP_PEPPER "novo_pepper" /M

# Verificar permissões: Admin only
icacls "%windir%\system32\config\environment" /grant "Administrators:(F)" /T
```

**Opção B — Azure Key Vault (recomendado para corporativo)**
```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

credential = DefaultAzureCredential()
client = SecretClient(vault_url="https://[vault].vault.azure.net/", credential=credential)
db_password = client.get_secret("db-password").value
```

**Opção C — HashiCorp Vault (enterprise)**
Configuração similar ao Azure, mas com mais controle.

**Esforço:** 
- Opção A: 1 hora
- Opção B: 2-3 horas (integração Azure)
- Opção C: 4-6 horas

**Recomendação:** Opção A para MVP, evoluir para B conforme crescer.

#### 2.3 Configuração de Segurança em Produção

**Checklist:**
- [ ] SESSION_COOKIE_SECURE=1 em produção
- [ ] FLASK_DEBUG=0 em produção
- [ ] LOG_LEVEL=INFO em produção
- [ ] HTTPS configurado
- [ ] Certificado válido e não expirado
- [ ] .env protegido (permissões restritas)

**Implementação:** 20 minutos (configuração)

---

### 🟡 IMPORTANTES — Devem ser feitos em Sprint 2.2

#### 3.1 Rate Limiting em Login

**O que está faltando:**
- [ ] Já há bloqueio por tentativas (5 tentativas, 15 min)
- ✅ Implementado em auth_service.py
- [ ] **Falta:** Rate limiting global (por IP, não por conta)

**Por quê importante:**
- Proteção contra força bruta distribuída
- Um atacante com 10 proxies pode tentar 50 vezes em 15 min
- Deve bloquear por IP, não só por conta

**Implementação sugerida:**
```python
# services/rate_limiter_service.py
class RateLimiter:
    def check_login_rate(ip_origem: str, limite: int = 10, janela: int = 300):
        """Máximo 10 tentativas por IP em 5 minutos"""
        cache_key = f"login_attempts:{ip_origem}"
        # Usar Redis ou in-memory dict com TTL
        return tentativas < limite
```

**Esforço:** 1-2 horas

#### 3.2 Proteção de Rotas Administrativas

**O que está faltando:**
- [ ] Rotas de admin não têm proteção de rate limiting
- [ ] Importação CSV (POST /ativos/import/csv) não tem limite
- [ ] Falta proteção de recurso caro (exportação em lote)

**Implementação sugerida:**
```python
@app.post("/ativos/import/csv")
def importar_csv():
    user_id = _obter_user_id_logado()
    if user_id is None:
        return _json_error("Não autenticado", status=401)
    
    # Validação de permissão
    user = auth_service.obter_usuario_por_id(user_id)
    if not eh_admin(user['perfil']):
        return _json_error("Não autorizado", status=403)
    
    # Rate limit: máximo 2 importações por hora por IP
    if not RateLimiter.check_import_rate(obter_ip_cliente(), limite=2, janela=3600):
        return _json_error("Muitas tentativas. Tente novamente em 1 hora", status=429)
    
    # ... resto da lógica
```

**Esforço:** 1-2 horas

#### 3.3 Validação de Campo Editável por Perfil

**O que está faltando:**
- [ ] Operador pode editar alguns campos
- [ ] Admin pode editar qualquer campo
- [ ] Precisamos de granularidade: operador não pode editar `criado_por`

**Implementação:** Esta é mais prioridade LOW, deixar para Sprint 2.3.

#### 3.4 Política de Senha Mais Rigorosa

**O que está faltando:**
- ✅ Há validação básica em utils/validators.py
- [ ] Falta: Expiração de senha (obrigar reset a cada 90 dias)
- [ ] Falta: Histórico de senha (não repetir últimas 5)
- [ ] Falta: Requisitos de complexidade mais altos

**Implementação sugerida:**
```python
# Adicionar a usuarios
alter table usuarios add column (
    senha_alterada_em TIMESTAMP,
    proxima_troca_obrigatoria_em TIMESTAMP,
    senha_hash_anterior VARCHAR(512)  -- Para validar histórico
);

# Ao fazer login
if proxima_troca_obrigatoria_em < CURRENT_TIMESTAMP:
    return error "Sua senha expirou. Atualize-a imediatamente."
```

**Esforço:** 2-3 horas (com testes)

---

### 🟢 MELHORIAS — Podem ficar para Sprint 2.3+

#### 4.1 Criptografia em Repouso

**O que está faltando:**
- [ ] Dados sensíveis (emails, IP) não são criptografados no BD
- [ ] Seria necessário TDE (Transparent Data Encryption) do MySQL

**Viabilidade:** Baixa prioridade (já há proteção via HTTPS + permissões)

#### 4.2 Web Application Firewall (WAF)

**O que está faltando:**
- [ ] Proteção contra SQL injection (já feita via prepared statements ✅)
- [ ] Proteção contra XSS (já feita via Jinja2 escape ✅)
- [ ] WAF externo (como CloudFlare) para DDoS

**Viabilidade:** Para futuro (quando escalar)

#### 4.3 Detecção de Anomalias

**O que está faltando:**
- [ ] Machine learning para detectar padrões suspeitos
- [ ] Alertas automáticos em comportamentos anormais

**Viabilidade:** Muito futuro (Phase 4+)

#### 4.4 Integração SSO/SAML

**O que está faltando:**
- [ ] Login integrado com Active Directory corporativo
- [ ] Reduziria complexidade de gerenciamento de senhas

**Viabilidade:** Para quando escalar (Phase 3)

---

## 3. Tabela de Priorização Completa

| Item | Criticidade | Sprint | Esforço | Implementador |
|------|------------|--------|---------|--|
| HTTPS + Certificado | 🔴 CRÍTICO | 2.1 | 2-4h | Infraestrutura |
| Estratégia de Secrets | 🔴 CRÍTICO | 2.1 | 1-3h | Backend |
| Rate limiting por IP | 🟡 IMPORTANTE | 2.2 | 1-2h | Backend |
| Proteção de rotas admin | 🟡 IMPORTANTE | 2.2 | 1-2h | Backend |
| Expiração de senha | 🟡 IMPORTANTE | 2.2 | 2-3h | Backend |
| Validação campo x perfil | 🟡 IMPORTANTE | 2.3 | 2-3h | Backend |
| Criptografia em repouso | 🟢 MELHORIA | 3+ | 4-6h | Infra/DBA |
| WAF externo | 🟢 MELHORIA | 3+ | Variável | Cloud |
| Detecção anomalias | 🟢 MELHORIA | 4+ | Variável | DataEng |
| SSO/SAML | 🟢 MELHORIA | 3+ | 4-8h | Backend |

---

## 4. Ações para Sprint 2.1 (Esta Sprint)

### ✅ Será feito

1. **Documentação de hardening**
2. **Estratégia de secrets** (Opção A — variáveis Windows)
3. **HTTPS readiness** (documentação, não implementação)
4. **Checklist de segurança** para deployment

### ⏸️ Fica para 2.2

1. Rate limiting por IP
2. Expiração de senha
3. Proteção de recursos caro

---

## 5. Checklist de Deployment Seguro

Antes de liberar para produção:

### Pré-requisitos de Segurança

- [ ] Certificado HTTPS válido e instalado
- [ ] SESSION_COOKIE_SECURE=1
- [ ] Secrets em variáveis de ambiente do SO
- [ ] .env deletado ou protegido (permissões admin-only)
- [ ] FLASK_DEBUG=0
- [ ] LOG_LEVEL=INFO
- [ ] Backup automático configurado
- [ ] Plano de restauração testado

### Testes de Segurança Manuais

- [ ] Acessar sem HTTPS redireciona para HTTPS
- [ ] Token CSRF é validado em POST
- [ ] Usuário de outra empresa não vê dados
- [ ] Admin vê dados de todas as empresas
- [ ] Consulta não pode criar/remover ativos
- [ ] Operador não pode remover ativos
- [ ] Login com 6+ tentativas bloqueia por 15 min
- [ ] Requisição sem autenticação retorna 401
- [ ] Requisição sem permissão retorna 403
- [ ] Upload de arquivo > 10 MB é rejeitado
- [ ] Upload de .exe é rejeitado
- [ ] Password hash está no banco, não plaintext

### Testes de Performance

- [ ] App inicia em < 5 segundos
- [ ] Query típica (listar ativos) < 500ms
- [ ] Não há memory leaks (monitorar 1 hora)

---

## 6. Próximos Passos Imediatos

1. **Sprint 2.1:**
   - ✅ Documentação de hardening (este arquivo)
   - ✅ Documentar estratégia de secrets
   - ✅ Criar checklist para Ops

2. **Sprint 2.2:**
   - ⏳ Implementar rate limiting por IP
   - ⏳ Adicionar expiração de senha
   - ⏳ Testar deployment seguro

3. **Validação com Ops/Segurança:**
   - ⏳ Opus revisa checklist
   - ⏳ Vicente Martins aprova estratégia

---

## 7. Veredito Técnico

✅ **Sistema tem base de segurança sólida.**

**O que está bom:**
- Autenticação robusta
- Proteção contra SQL injection
- Controle de acesso implementado
- Auditoria em lugar
- Headers de segurança

**O que precisa de ação AGORA:**
- HTTPS (crítico)
- Secrets management (crítico)
- Rate limiting (importante)

**Resultado esperado após hardening:**
- Pronto para homologação corporativa
- Pronto para produção em Windows Server
- Compliance mínimo com LGPD
- Base segura para expansão

---

**Responsável:** Claude Code  
**Data:** 2026-04-10  
**Versão:** 1.0
