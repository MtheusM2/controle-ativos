# FASE A — Fechamento Técnico Herdado da Parte 1

**Data:** 2026-04-10  
**Status:** Análise Completa  
**Prioridade:** Crítica (bloqueador de produção)

---

## 1. SESSION_COOKIE_SECURE

### Estado Atual
- **Configurado em:** `web_app/app.py` linha 62
- **Origem:** variável de ambiente `SESSION_COOKIE_SECURE`
- **Valor em desenvolvimento:** `False` (não está no `.env` local)
- **Implementação:** `SESSION_COOKIE_SECURE=SESSION_COOKIE_SECURE` — lê de config.py

### Análise Técnica
O cookie de sessão é transmitido em HTTP desprotegido em desenvolvimento, o que é aceitável. Em produção, quando HTTPS estiver ativo, **é obrigatório** ativar `SESSION_COOKIE_SECURE=True`.

### Recomendação
✅ **Já está correto**. A implementação suporta dois cenários:

1. **Desenvolvimento (HTTP):**
   - `.env` não define `SESSION_COOKIE_SECURE` → padrão False
   - Cookie transmitido normalmente

2. **Produção (HTTPS via IIS):**
   - `.env` define `SESSION_COOKIE_SECURE=1` → True
   - Cookie apenas em canal seguro

### Ação Necessária
Antes de produção plena, no `deploy/windows_server/.env.production` (ou equivalente):
```
SESSION_COOKIE_SECURE=1
```

**Dependência:** Certificado HTTPS configurado no IIS.

---

## 2. Coerência Entre Ambientes

### Estado Atual
- **Desenvolvimento:** Windows 11 + SQLite ou MySQL local
- **Homologação:** (não está definida)
- **Produção:** Windows Server 2019+ + MySQL + IIS + NSSM + Waitress

### Análise Técnica

#### ✅ O que já está bom

1. **Configuração centralizada em `config.py`:**
   - Todas as variáveis lidas de uma única fonte
   - Suporta `.env` local + variáveis de ambiente do SO
   - Validação de variáveis obrigatórias

2. **Factory pattern em `create_app()`:**
   - Permite injeção de configurações
   - Facilita testes com config override
   - Prepara para múltiplos ambientes

3. **Support à S3 storage:**
   - Desenvolvimento: `STORAGE_TYPE=local` (arquivos no disco)
   - Produção/Render: `STORAGE_TYPE=s3` (cloud storage)
   - Abstração completa via `StorageBackend`

4. **Logging estruturado:**
   - Centralizado em `utils/logging_config.py`
   - Nível configurável via `LOG_LEVEL`
   - Diretório configurável via `LOG_DIR`

#### ⚠️ Pontos que precisam de definição

1. **Ambiente de homologação não está documentado:**
   - Não há um `.env.homologacao` ou equivalent
   - Não há SLA ou padrão de teste de homologação
   - Recomendação: Criar setup de homologação em Windows Server com dados de teste

2. **Diferenças entre ambientes não estão documentadas:**
   - DEBUG (True em dev, False em produção)
   - HTTPS (não em dev, sim em produção)
   - Rate limiting (não configurado)
   - Headers de segurança (já estão no `web.config`)

### Recomendação

**Criar matriz de ambientes:**

| Aspecto | Desenvolvimento | Homologação | Produção |
|---------|-----------------|-------------|----------|
| OS | Windows 11 | Windows Server 2019+ | Windows Server 2019+ |
| DB | MySQL local | MySQL 8 cloud/interno | MySQL 8 cloud/interno |
| FLASK_DEBUG | 1 | 0 | 0 |
| SESSION_COOKIE_SECURE | 0 | 1 | 1 |
| HTTPS | ❌ | ✅ | ✅ |
| STORAGE_TYPE | local | s3 (opcional) | s3 |
| LOG_LEVEL | DEBUG | INFO | INFO |
| Rate limiting | ❌ | ✅ | ✅ |

### Ação Necessária
Criar `docs/AMBIENTES.md` com configurações esperadas para cada ambiente.

---

## 3. HTTPS — Necessidade e Status

### Estado Atual
- **Certificado:** Não instalado em desenvolvimento
- **Suporte no código:** ✅ Implementado
- **Headers de segurança:** ✅ Implementados no `web.config`

### Análise Técnica

#### ✅ O que já está implementado

1. **Headers de segurança no `deploy/iis/web.config`:**
   ```xml
   <add name="X-Content-Type-Options"  value="nosniff" />
   <add name="X-Frame-Options"         value="DENY" />
   <add name="Referrer-Policy"         value="strict-origin-when-cross-origin" />
   <add name="Permissions-Policy"      value="geolocation=(), ..." />
   <add name="Content-Security-Policy" value="default-src 'self'; ..." />
   ```

2. **Detecção de HTTPS via `X-Forwarded-Proto`:**
   - IIS escreve `X-Forwarded-Proto: https` quando TLS é usado
   - Flask pode usar isso para validações adicionais

3. **Bloqueio de acesso direto ao Waitress:**
   - IIS proxy reverso em porta 80/443
   - Waitress escuta apenas em 127.0.0.1:8000 (interno)

#### ⚠️ Necessidade de HTTPS

**OBRIGATÓRIO em produção:**
- Dados sensíveis: credenciais, emails, informações de ativos
- Compliance corporativa
- Proteção contra man-in-the-middle

**Em desenvolvimento:**
- ❌ Não é necessário (self-signed certs causam problemas)
- ✅ Stack já está preparado

### Recomendação

**Para produção:**
1. Instalar certificado SSL/TLS no IIS (Let's Encrypt ou CA corporativa)
2. Configurar `SESSION_COOKIE_SECURE=1`
3. Redirecionar HTTP → HTTPS no `web.config`

**Adicionar ao `web.config` em produção:**
```xml
<rule name="Force HTTPS" stopProcessing="true">
  <match url="(.*)" />
  <conditions>
    <add input="{HTTPS}" pattern="off" />
  </conditions>
  <action type="Redirect" url="https://{HTTP_HOST}{REQUEST_URI}" redirectType="Permanent" />
</rule>
```

### Ação Necessária
Antes de produção, obter certificado e instalá-lo no IIS.

---

## 4. Foreign Key de `sequencias_ativo`

### Estado Atual
- **Tabela:** `sequencias_ativo` criada em Parte 1
- **FK:** Existe para `empresa_id` → `empresas(id)`
- **Constraint:** `ON DELETE RESTRICT ON UPDATE CASCADE`
- **Status:** ✅ Validado e funcionando

### Análise Técnica

```sql
CREATE TABLE sequencias_ativo (
    empresa_id     INT          NOT NULL,
    proximo_numero INT UNSIGNED NOT NULL DEFAULT 1,
    PRIMARY KEY (empresa_id),
    CONSTRAINT fk_seq_empresa
        FOREIGN KEY (empresa_id) REFERENCES empresas (id)
        ON DELETE RESTRICT ON UPDATE CASCADE
);
```

**Análise da constraint:**
- ✅ `ON DELETE RESTRICT` — não permite deletar empresa com sequência ativa (proteção)
- ✅ `ON UPDATE CASCADE` — se `empresa_id` mudar (improvável), sequência acompanha
- ✅ Acesso com `SELECT FOR UPDATE` na service — garante atomicidade

### Recomendação
✅ **Já está correto**. Nenhuma mudança necessária.

---

## 5. Variáveis Sensíveis e Secrets

### Estado Atual

#### ❌ Em desenvolvimento
Arquivo `.env` em plaintext:
```
DB_PASSWORD=0201d6cd772bcadd54956af50c747405
FLASK_SECRET_KEY=d617313f4ae10d80f273f7802b10088487f08c8362bf708dc9a17c54896dc5b2
APP_PEPPER=4f72e893d8a5cf9fb7525515a6fac6dce5818c6e96e0f81385f3433364267d56
```

**Risco:** Baixo em desenvolvimento (máquina local), mas não segue boas práticas.

#### ⚠️ Em produção
- `deploy/nssm/install_service.ps1` requer `.env` no servidor
- `.env` fica em plaintext em `C:\controle_ativos\.env`
- Acessível a qualquer processo rodando no servidor

### Análise Técnica

**Problema identificado:**
1. `.env` em plaintext no servidor de produção
2. Sem rotação automática de credenciais
3. Sem versionamento seguro (não vai para git)

### Recomendação

**Estratégia de secrets em produção:**

1. **Opção A — Variáveis de ambiente do Windows:**
   - Definir credenciais como variáveis de ambiente do SO
   - Permissões restritas via NTFS
   - Modificar `config.py` para ler de `os.environ` apenas

2. **Opção B — Azure Key Vault (recomendado para corporativo):**
   - Integração com `DefaultAzureCredential`
   - Rotação automática de credenciais
   - Auditoria integrada
   - Exemplo: [docs/SECRETS_AZURE_KEYVAULT.md] (criar)

3. **Opção C — Arquivo protegido por NTFS (mínimo):**
   - `.env` com permissões restritas (SYSTEM + admin apenas)
   - Documentar em `docs/SECURITY_SECRETS.md`

### Ação Necessária
Escolher estratégia de secrets **ANTES de ir para produção plena**.  
Para MVP (homologação controlada): usar variáveis de ambiente do Windows com permissões restritas.

---

## 6. Backup e Restauração

### Estado Atual
- ❌ Não há scripts de backup automático
- ❌ Não há procedimento documentado de restauração
- ❌ Não há teste de restauração

### Análise Técnica

**Dados críticos a proteger:**
1. **Banco de dados MySQL:**
   - Usuários, empresas, ativos, anexos
   - Estado de sequências de ID

2. **Arquivos de anexos:**
   - Temos `MAX_CONTENT_LENGTH=10 MB`
   - Em storage local: `web_app/static/uploads/`
   - Em S3: bucket com versionamento

3. **Logs de auditoria:**
   - Quando implantados, serão críticos

### Recomendação

**Para produção, implementar:**

1. **Backup de banco de dados:**
   ```powershell
   mysqldump -u opus_app -p controle_ativos > backup_$(Get-Date -Format yyyy-MM-dd_HHmmss).sql
   ```
   - Automatizar com agendador do Windows (Task Scheduler)
   - Reter 30 dias de backups

2. **Backup de arquivos:**
   - Se local: robocopy para share de rede
   - Se S3: versioning habilitado + bucket replication

3. **Teste de restauração:**
   - Mensal em ambiente de teste
   - Documentar tempo de RTO/RPO

### Ação Necessária
Criar `scripts/backup_producao.ps1` e `docs/RESTORE_PROCEDURE.md` **ANTES de produção**.

---

## 7. Resumo de Achados

| Item | Status | Ação | Prioridade |
|------|--------|------|-----------|
| SESSION_COOKIE_SECURE | ✅ Correto | Ativar em produção via .env | Alta |
| Coerência de ambientes | ⚠️ Incompleto | Documentar matriz de ambientes | Média |
| HTTPS | ⚠️ Preparado | Instalar certificado em produção | Crítica |
| FK sequencias_ativo | ✅ Correto | Nenhuma | — |
| Variáveis sensíveis | ❌ Risco | Implementar estratégia de secrets | Crítica |
| Backup/Restauração | ❌ Ausente | Criar scripts e documentação | Crítica |

---

## 8. O Que Entra em Produção Plena

### ✅ Já está pronto para produção controlada (homologação):
- Architecture geral
- SESSION_COOKIE_SECURE (como 0 em homologação, 1 em produção)
- Isolamento por empresa
- CRUD de ativos com segurança básica
- Logging estruturado

### ⏸️ Deve estar pronto ANTES de produção plena:
1. Certificado HTTPS instalado e validado
2. Estratégia de secrets implementada
3. Backups automatizados testados
4. Testes de restauração bem-sucedidos
5. Matriz de ambientes documentada

### ❓ Pode ficar para segundo plano (não bloqueia produção):
- Monitoramento detalhado (será necessário após go-live)
- Rate limiting (será necessário após crescimento)
- Auditoria completa (será implementada em Fase C)

---

## 9. Próximos Passos

### Imediato (para homologação controlada)
- [ ] Criar `.env.homologacao` com `SESSION_COOKIE_SECURE=0`
- [ ] Documentar matriz de ambientes em `docs/AMBIENTES.md`
- [ ] Testar conexão ao banco em ambiente de homologação

### Curto prazo (antes de produção plena)
- [ ] Obter certificado SSL/TLS
- [ ] Instalar certificado no IIS de produção
- [ ] Implementar estratégia de secrets (opção A, B ou C)
- [ ] Criar scripts de backup/restauração
- [ ] Testar restauração completa

### Validação
Antes de aprovar Fase A:
- [ ] Ops/Infra revisa certificado HTTPS
- [ ] Segurança revisa estratégia de secrets
- [ ] DBA valida estratégia de backup/restauração
- [ ] Revisão técnica de coerência entre ambientes

---

## 10. Recomendação Técnica

✅ **Sistema pronto para homologação controlada em 2026-04-10.**

⚠️ **Crítico: Resolver HTTPS + Secrets antes de produção plena.**

---

**Responsável pela análise:** Claude Code  
**Data:** 2026-04-10  
**Versão:** 1.0
