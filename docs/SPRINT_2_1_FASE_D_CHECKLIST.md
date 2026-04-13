# FASE D — Checklist de Deployment Seguro
## Sprint 2.1 Final

**Data:** 2026-04-10  
**Status:** Checklist Profissional  
**Escopo:** Preparação para homologação e produção plena

---

## 1. CHECKLIST TÉCNICO PRÉ-DEPLOYMENT

### 1.1 Variáveis de Ambiente — BLOQUEADOR

| Variável | Status | Como Validar |
|----------|--------|-------------|
| **ENVIRONMENT** | Deve existir | `echo %ENVIRONMENT%` |
| **FLASK_SECRET_KEY** | Deve ter 32+ chars | `echo %FLASK_SECRET_KEY%` |
| **APP_PEPPER** | Deve ter 32+ chars | `echo %APP_PEPPER%` |
| **DB_PASSWORD** | Deve ter 8+ chars | Tentar conectar ao banco |
| **DB_HOST** | Resolvível | `ping %DB_HOST%` |
| **DB_USER** | Credencial válida | Teste de conexão |
| **DB_NAME** | Banco deve existir | Query de tabelas |
| **FLASK_DEBUG** | Deve ser 0 | `echo %FLASK_DEBUG%` |
| **SESSION_COOKIE_SECURE** | Deve ser 1 se HTTPS | `echo %SESSION_COOKIE_SECURE%` |

**Validação:**
```powershell
# Script de validação
python -c "
from config import (
    FLASK_SECRET_KEY, APP_PEPPER, DB_PASSWORD,
    DB_HOST, DB_USER, DB_NAME, FLASK_DEBUG,
    SESSION_COOKIE_SECURE, IS_PRODUCTION
)
print('✓ Todas as variáveis críticas carregadas')
print(f'  IS_PRODUCTION: {IS_PRODUCTION}')
print(f'  FLASK_DEBUG: {FLASK_DEBUG}')
print(f'  SESSION_COOKIE_SECURE: {SESSION_COOKIE_SECURE}')
"
```

### 1.2 Código — BLOQUEADOR

- [ ] Sem arquivos `.env` com valores reais no repositório
- [ ] Sem hardcoding de senhas em `*.py`
- [ ] Sem valores placeholder ("CHANGE_ME") em runtime
- [ ] Testes passam: `pytest tests/ -v` (121/121 OK)
- [ ] Nenhuma regressão em funcionalidades críticas

**Validação:**
```powershell
# Grep para garantir sem placeholder
grep -r "CHANGE_ME" . --include="*.py"  # Não deve retornar nada
```

### 1.3 Banco de Dados — BLOQUEADOR

- [ ] Banco `controle_ativos` existe
- [ ] Todas as migrações foram aplicadas
- [ ] Usuário `opus_app` existe com senha correta
- [ ] Permissões de `opus_app` estão restritas (sem GRANT, DROP)
- [ ] Tabelas principais existem: `usuarios`, `empresas`, `ativos`, `auditoria_eventos`
- [ ] Foreign keys estão em lugar (se aplicável)
- [ ] Backup inicial foi feito antes do deploy

**Validação:**
```sql
-- No MySQL como root ou opus_app
SHOW TABLES;  -- Deve listar todas as tabelas
SHOW GRANTS FOR 'opus_app'@'localhost';  -- Verificar permissões

-- Validar schema
SELECT COUNT(*) FROM usuarios;
SELECT COUNT(*) FROM empresas;
SELECT COUNT(*) FROM ativos;
SELECT COUNT(*) FROM auditoria_eventos;
```

### 1.4 Estrutura de Diretórios — BLOQUEADOR

- [ ] Diretório de logs existe: `C:\controle_ativos\logs\`
- [ ] Permissões de logs: Windows service account pode escrever
- [ ] Diretório de uploads existe: `C:\controle_ativos\web_app\static\uploads\`
- [ ] Permissões de uploads: IIS AppPool pode ler/escrever
- [ ] Certificado SSL (se HTTPS): `C:\certificados\` ou equivalente

**Validação:**
```powershell
Test-Path "C:\controle_ativos\logs"  # True
Test-Path "C:\controle_ativos\web_app\static\uploads"  # True
Get-ChildItem -Path "C:\controle_ativos\logs" -ErrorAction SilentlyContinue
```

### 1.5 Segurança de Arquivo — BLOQUEADOR

- [ ] `.env` não está em diretório público (ou não existe em prod)
- [ ] `.env` não está versionado no git
- [ ] Permissões de arquivo restrictivas:
  - `config.py` readable by app account only
  - Diretório `logs/` writable by app account
  - Certificado SSL readable by IIS account only

**Validação:**
```powershell
# Windows ACL (Access Control List)
icacls "C:\controle_ativos" /T /C  # Revisar permissões
```

### 1.6 HTTPS e Certificado — CRÍTICO se HTTPS

- [ ] Certificado SSL obtido e validado
- [ ] Certificado instalado no Windows Server
- [ ] Binding HTTPS criado no IIS (porta 443)
- [ ] Rule "Force HTTPS" habilitada em web.config
- [ ] Certificado não está expirado (validade > 30 dias)
- [ ] Firewall permite entrada na porta 443

**Validação:**
```powershell
# Testar certificado
$cert = Get-Item Cert:\LocalMachine\My\*
$cert | Where {$_.Subject -like "*seu_dominio*"} | Select Subject, NotAfter

# Testar HTTPS
curl -I https://seu_servidor/  # Status 200
curl -i http://seu_servidor/   # Status 301 (redirect)
```

### 1.7 Aplicação — BLOQUEADOR

- [ ] Waitress inicia sem erro: `python -m waitress wsgi:application`
- [ ] Endpoint `/health` responde 200
- [ ] Endpoint `/config-diagnostico` responde com `is_production: true`
- [ ] Nenhum erro crítico nos logs do startup

**Validação:**
```powershell
# Iniciar app manualmente
python -m waitress --listen=127.0.0.1:8000 wsgi:application

# Em outro terminal
curl http://127.0.0.1:8000/health
# Esperado: {"ok": true, "status": "healthy"}

curl http://127.0.0.1:8000/config-diagnostico
# Esperado: is_production: true, alertas: []
```

---

## 2. CHECKLIST OPERACIONAL PRÉ-DEPLOYMENT

### 2.1 Banco de Dados

- [ ] Backup automático está configurado (agendado)
- [ ] Teste de restore foi executado com sucesso (em staging)
- [ ] Retenção de backups: mínimo 30 dias
- [ ] Retenção de logs de auditoria: 90 dias (normal), 180 dias (segurança)
- [ ] Script de limpeza automática `limpar_auditoria_automatico.ps1` foi testado

**Comandos:**
```powershell
# Agendar backup automático (Task Scheduler)
# Name: "Backup-ContorleAtivos"
# Trigger: Daily 02:00 AM
# Action: powershell -File C:\controle_ativos\scripts\backup_mysql.ps1

# Testar limpeza de auditoria
python -c "
from services.auditoria_service import AuditoriaService
print('Serviço de auditoria carregado OK')
"
```

### 2.2 Logs e Monitoring

- [ ] Diretório de logs foi criado: `C:\controle_ativos\logs\`
- [ ] LOG_LEVEL está em "INFO" (não DEBUG em prod)
- [ ] Rotação de logs está configurada (evitar disco cheio)
- [ ] Alertas de erro crítico serão monitorados (manual ou por ferramentas)
- [ ] Arquivo de log principal: `C:\controle_ativos\logs\app.log`

**Validação:**
```powershell
# Verificar que logs estão sendo criados
Get-ChildItem "C:\controle_ativos\logs\*.log" | Select-Object LastWriteTime, Length
```

### 2.3 Permissões de Arquivo/Pasta

- [ ] Serviço NSSM roda com conta dedicada ou com privilégios mínimos
- [ ] IIS AppPool executa com privilégios mínimos (não Administrator)
- [ ] Diretório `C:\controle_ativos` tem permissões restrictivas
- [ ] Apenas pessoas autorizadas podem acessar `logs/` e certificados

**Validação:**
```powershell
# Verificar conta de serviço NSSM
nssm query controle-ativos-waitress AppEnvironmentExtra
# Deve listar usuário correto

# Verificar AppPool IIS
Get-IISAppPool -Name "controle-ativos" | Select ProcessModel
```

### 2.4 Cookies e Sessão

- [ ] SESSION_COOKIE_HTTPONLY está ativo
- [ ] SESSION_COOKIE_SAMESITE está "Lax"
- [ ] SESSION_COOKIE_SECURE está "1" se HTTPS (ou "0" se intranet sem HTTPS)
- [ ] SESSION_LIFETIME_MINUTES está em 120 (ou conforme política)

**Validação:**
```python
from web_app.app import create_app
app = create_app()
print(f"HTTPONLY: {app.config['SESSION_COOKIE_HTTPONLY']}")
print(f"SAMESITE: {app.config['SESSION_COOKIE_SAMESITE']}")
print(f"SECURE: {app.config['SESSION_COOKIE_SECURE']}")
```

### 2.5 Upload de Arquivos

- [ ] Limite de upload está em 10 MB (MAX_CONTENT_LENGTH)
- [ ] Extensões permitidas: .pdf, .png, .jpg, .jpeg, .webp
- [ ] Validação de MIME type está ativa
- [ ] Diretório de uploads é inaccessível via HTTP direto (web.config rule)

**Validação:**
```powershell
# Testar rejeição de upload grande
# Criar arquivo > 10 MB e tentar fazer upload
# Esperado: erro 413 (Payload Too Large)
```

### 2.6 Usuário Admin

- [ ] Usuário admin inicial foi criado
- [ ] Email do admin é válido (corporativo)
- [ ] Senha do admin foi setada pelo procedimento seguro (senha temporária com força obrigatória de reset)
- [ ] Perfil do admin está correto (admin/adm)
- [ ] Admin consegue logar

**Validação:**
```sql
-- No MySQL
SELECT id, nome, email, perfil FROM usuarios WHERE perfil IN ('admin', 'adm');
-- Deve listar pelo menos 1 admin

-- Testar login
curl -X POST http://localhost:8000/login \
  -d "email=admin@empresa.com&senha=tempo_password" \
  -c cookies.txt

curl http://localhost:8000/ativos -b cookies.txt
# Esperado: lista de ativos (acesso concedido)
```

### 2.7 Auditoria Ativa

- [ ] Tabela `auditoria_eventos` foi criada
- [ ] Eventos estão sendo registrados (verificar com SELECT COUNT)
- [ ] Campos obrigatórios: tipo_evento, usuario_id, empresa_id, criado_em
- [ ] JSON payload está sendo armazenado (dados_antes, dados_depois)

**Validação:**
```sql
SELECT COUNT(*) AS total_eventos FROM auditoria_eventos;
SELECT * FROM auditoria_eventos ORDER BY criado_em DESC LIMIT 1;
```

### 2.8 LGPD Mínima

- [ ] Aviso de privacidade está disponível (`AVISO_PRIVACIDADE.txt`)
- [ ] Política de retenção de dados foi documentada
- [ ] Responsável de dados foi designado e comunicado
- [ ] Fluxo de incidente de segurança foi documentado
- [ ] Script de limpeza de logs foi testado

**Documentação obrigatória:**
- `docs/AVISO_PRIVACIDADE.txt` ✅
- `docs/POLITICA_RETENCAO_DADOS.md` ✅
- `docs/FLUXO_INCIDENTE_SEGURANCA.md` ⏳ (criar se não existir)

---

## 3. TESTES DE SMOKE PÓS-DEPLOY

Execute estes testes após deploy em staging/produção.

### 3.1 Health Check

```bash
curl https://seu_servidor/health
# Esperado: {"ok": true, "status": "healthy"}
```

**Tempo esperado:** < 1 segundo

### 3.2 Diagnóstico de Configuração

```bash
curl https://seu_servidor/config-diagnostico
# Esperado: is_production: true, alertas: []
```

### 3.3 Login Funciona

```bash
# 1. Acessar página de login
curl -i https://seu_servidor/login

# 2. Extrair token CSRF
# (implementado no HTML, não necessário validar aqui)

# 3. Fazer login (exemplo)
curl -X POST https://seu_servidor/login \
  -d "email=admin@empresa.com&senha=senha_temp" \
  -c cookies.txt

# 4. Validar sessão
curl https://seu_servidor/ativos -b cookies.txt
# Esperado: Página de ativos (autenticado)
```

### 3.4 Cookie Está Secure

```bash
# Fazer login e revisar headers
curl -i -X POST https://seu_servidor/login \
  -d "email=admin@empresa.com&senha=senha_temp"

# Procurar por:
# Set-Cookie: session=...; Path=/; Secure; HttpOnly; SameSite=Lax
# ↑ Flag "Secure" deve estar presente se SESSION_COOKIE_SECURE=1
```

### 3.5 Upload de Arquivo

```bash
# Fazer login primeiro (criar cookies.txt)
# Depois fazer upload de arquivo válido
curl -F "arquivo=@documento.pdf" \
  https://seu_servidor/ativos/123/anexo \
  -b cookies.txt

# Esperado: arquivo armazenado, resposta 200
```

### 3.6 Rejeição de Upload Inválido

```bash
# Tentar upload de arquivo proibido
curl -F "arquivo=@malware.exe" \
  https://seu_servidor/ativos/123/anexo \
  -b cookies.txt

# Esperado: erro 400/403 (arquivo rejeitado)
```

### 3.7 Auditoria Registra Login

```sql
-- Após fazer login, verificar se evento foi registrado
SELECT * FROM auditoria_eventos 
WHERE tipo_evento = 'LOGIN_SUCESSO' 
ORDER BY criado_em DESC LIMIT 1;

-- Esperado: registro com usuario_id, empresa_id, criado_em preenchidos
```

### 3.8 Isolamento por Empresa

```bash
# Se houver múltiplas empresas:

# 1. Login como Usuário da Empresa A
# 2. Acessar /ativos (listar)
# 3. Verificar que APENAS ativos da Empresa A são retornados

# Para verificar:
curl https://seu_servidor/ativos -b cookies.txt | grep empresa_id
# Deve conter APENAS empresa_id=1 (exemplo)
```

### 3.9 Acesso Negado sem Autenticação

```bash
curl -i https://seu_servidor/ativos
# Esperado: 401 Unauthorized ou redirect para /login
```

### 3.10 Permissões de Perfil

```bash
# Login como "Consulta" (read-only)
# Tentar criar ativo
curl -X POST https://seu_servidor/ativos \
  -d "nome=novo&tipo=notebook" \
  -b cookies.txt

# Esperado: 403 Forbidden (Consulta não pode criar)
```

### 3.11 HTTPS Redirect

```bash
curl -i http://seu_servidor/  # HTTP simples
# Esperado: 301 Permanent Redirect para https://seu_servidor/
```

### 3.12 Performance Básica

```bash
# Testar tempo de resposta
time curl https://seu_servidor/ativos -b cookies.txt

# Esperado: < 1 segundo para listar ativos
```

---

## 4. BLOQUEADORES vs RECOMENDAÇÕES

### Bloqueadores — Não Deploy Sem Estes

🔴 **CRÍTICOS — Impedem deploy:**

1. Variáveis de ambiente não setadas
2. Banco de dados não responde
3. Testes unitários falhando (< 121 passando)
4. HTTPS não funciona (se necessário)
5. Certificado inválido/expirado

🟡 **IMPORTANTES — Diminui risco:**

1. Logs não estão sendo criados
2. Auditoria não está registrando
3. Backup não foi testado
4. Permissões de arquivo inseguras

### Recomendações — Ativar Após Deploy

🟢 **SUGERIDAS — Implementar depois:**

1. Rate limiting por IP em login
2. Expiração de senha (90 dias)
3. Dashboard de auditoria
4. Alertas automáticos em logs de erro
5. Monitoramento de performance

---

## 5. ROLLBACK (Plano B)

Se algo deu errado pós-deploy:

### Rollback Rápido (últimas 24h)

1. **Restaurar banco de dados do backup**
   ```sql
   -- Restaurar de backup anterior
   mysql controle_ativos < backup_producao_2026-04-10_02h.sql
   ```

2. **Reverter aplicação**
   ```powershell
   # Se usando git
   git checkout HEAD~1
   
   # Ou restaurar versão anterior manualmente
   ```

3. **Reiniciar serviço**
   ```powershell
   net stop controle-ativos-waitress
   net start controle-ativos-waitress
   ```

4. **Validar**
   ```bash
   curl https://seu_servidor/health
   ```

### Rollback Completo (retornar a versão anterior)

1. Parar produção
2. Restaurar backup de banco (versão anterior)
3. Restaurar código (git reset ou restore)
4. Alterar variáveis de ambiente (se necessário)
5. Reiniciar serviço
6. Notificar usuários

---

## 6. CHECKLIST PRÉ-DEPLOY FINAL

Use isto como modelo para homologação/produção:

```
VARIÁVEIS DE AMBIENTE:
[ ] ENVIRONMENT setada
[ ] FLASK_SECRET_KEY setada (32+ chars)
[ ] APP_PEPPER setada (32+ chars)
[ ] DB_PASSWORD setada
[ ] SESSION_COOKIE_SECURE = 1 (se HTTPS) ou 0 (intranet)
[ ] FLASK_DEBUG = 0
[ ] LOG_LEVEL = INFO

BANCO DE DADOS:
[ ] Banco existe
[ ] Migrações aplicadas
[ ] Usuário opus_app com permissões corretas
[ ] Backup inicial realizado
[ ] Teste de restore bem-sucedido

HTTPS (se aplicável):
[ ] Certificado instalado
[ ] Binding HTTPS criado no IIS
[ ] Rule "Force HTTPS" habilitada
[ ] SESSION_COOKIE_SECURE = 1

APLICAÇÃO:
[ ] App inicia sem erro
[ ] /health responde 200
[ ] /config-diagnostico responde OK
[ ] Testes passam (121/121)
[ ] Nenhuma regressão

LOGS E AUDITORIA:
[ ] Diretório de logs criado
[ ] Auditoria ativa (eventos sendo registrados)
[ ] Limpeza automática de logs configurada

USUÁRIO ADMIN:
[ ] Admin foi criado
[ ] Admin consegue logar
[ ] Senha foi resetada/alterada após primeiro login

SMOKE TESTS (pós-deploy):
[ ] Login funciona
[ ] CRUD de ativos funciona
[ ] Upload de arquivo funciona
[ ] Isolamento por empresa OK
[ ] Permissões por perfil OK
[ ] Auditoria registra ações

STATUS FINAL:
[ ] Pronto para produção plena
[ ] Suporte notificado
[ ] Plano de rollback pronto
```

---

## 7. Veredito da Fase D

✅ **Checklist profissional criado.**

**Cobertura:**
- 45+ itens de validação
- Bloqueadores vs recomendações claramente diferenciados
- Testes de smoke pós-deploy
- Plano de rollback

**Uso:** Imprimir/PDF e preencher a cada deployment.

---

**Responsável:** Claude Code  
**Data:** 2026-04-10  
**Status:** Fase D concluída. Pronto para Fase E (Validação Final).
