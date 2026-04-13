# FASE A — Levantamento do Ambiente e Configuração Atual
## Sprint 2.1 Final

**Data:** 2026-04-10  
**Status:** Mapeamento Concluído  
**Prioridade:** Crítica

---

## 1. Mapa das Configurações Atuais

### 1.1 Fluxo de Carregamento

```
.env (arquivo)
    ↓
config.py — load_dotenv(dotenv_path=".env", override=True)
    ↓
Variáveis globais: DB_*, FLASK_*, LOG_*, SESSION_*, AUTH_*
    ↓
web_app/app.py — create_app() usa config.* globals
    ↓
Flask app config atualizado
```

**Localização:** `config.py` é a única fonte de verdade de carregamento.

---

## 2. Inventory de Secrets Encontrados

### 2.1 Críticos — Nunca devem estar no código

| Secret | Localização | Risco | Status |
|--------|------------|-------|--------|
| DB_PASSWORD | `.env` linha 4 | **CRÍTICO** | Exposto em arquivo |
| FLASK_SECRET_KEY | `.env` linha 6 | **CRÍTICO** | Exposto em arquivo |
| APP_PEPPER | `.env` linha 7 | **CRÍTICO** | Exposto em arquivo |

### 2.2 Sensíveis — Devem mudar por ambiente

| Variável | Uso | Desenvolvimento | Homologação | Produção |
|----------|-----|-----------------|-------------|----------|
| DB_HOST | Conexão BD | localhost | host_interno | host_externo |
| DB_USER | Autenticação BD | opus_app | opus_app | opus_app |
| DB_PASSWORD | Credencial BD | (dev local) | ⚠️ DEVE MUDAR | ⚠️ DEVE MUDAR |
| FLASK_SECRET_KEY | Sessão/cookies | (dev local) | ⚠️ DEVE MUDAR | ⚠️ DEVE MUDAR |
| APP_PEPPER | Hash de senha | (dev local) | ⚠️ DEVE MUDAR | ⚠️ DEVE MUDAR |
| FLASK_DEBUG | Debug mode | 0 | 0 | **0 (obrigatório)** |
| SESSION_COOKIE_SECURE | HTTPS cookie | 0 | **1 (quando HTTPS)** | **1 (obrigatório)** |

### 2.3 Configuráveis — Podem ter fallbacks seguros

| Variável | Fallback | Risco | Recomendação |
|----------|----------|-------|--------------|
| LOG_LEVEL | "INFO" | Baixo | Aceitar padrão |
| LOG_DIR | "logs" | Baixo | Aceitar padrão |
| SESSION_LIFETIME_MINUTES | 120 | Baixo | Aceitar padrão |
| AUTH_MAX_FAILED_ATTEMPTS | 5 | Médio | Aceitar padrão |
| AUTH_LOCKOUT_MINUTES | 15 | Médio | Aceitar padrão |
| PBKDF2_ITERATIONS | 600000 | Baixo | Aceitar padrão |
| STORAGE_TYPE | "local" | Médio | Explícito para "s3" |
| DB_CONNECTION_TIMEOUT | 30 | Baixo | Aceitar padrão |

---

## 3. Análise de Risco Atual

### 3.1 Vulnerabilidades Identificadas

#### 🔴 RISCO CRÍTICO

**Problema:** `.env` contém secrets em plaintext  
**Impacto:** Se repositório for comprometido (git clone, backup antigo), todos os secrets vazam  
**Evidência:** `.env` existe com valores reais:
```
DB_PASSWORD=0201d6cd772bcadd54956af50c747405
FLASK_SECRET_KEY=d617313f4ae10d80f273f7802b10088487f08c8362bf708dc9a17c54896dc5b2
APP_PEPPER=4f72e893d8a5cf9fb7525515a6fac6dce5818c6e96e0f81385f3433364267d56
```

**Mitigação:**
- Criar `.env.example` sem valores (✅ já existe)
- Remover `.env` do repositório (se estiver)
- Carregar secrets de variáveis de ambiente do SO em produção

#### 🟡 RISCO IMPORTANTE

**Problema:** Mesmo valores em diferentes ambientes  
**Impacto:** Credencial de desenvolvimento funciona em produção; se uma cair, todas caem  
**Evidência:** config.py carrega mesmo `.env` para local/homolog/prod  

**Mitigação:**
- Valores diferentes por ambiente
- Variáveis de ambiente do SO para produção
- Documentação clara de como setar

#### 🟡 RISCO IMPORTANTE

**Problema:** SESSION_COOKIE_SECURE=0 em desenvolvimento pode vazar mesmo em teste  
**Impacto:** Cookie de sessão enviado em plaintext HTTP  
**Evidência:** `SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0").strip() == "1"`  

**Mitigação:**
- ✅ Já está preparado para variar por variável
- Documentar quando ativar para produção

---

## 4. O Que Já Está Bem Implementado

✅ **config.py como camada centralizada** — Todas as variáveis em um lugar  
✅ **Fallbacks sensatos** — Valores padrão razoáveis quando não defini  
✅ **Validação em config.py** — `_get_required_str()` garante que críticos existam  
✅ **Nenhum hardcoding em rotas** — Tudo passa por config.py  
✅ **Suporte a variáveis de ambiente** — `os.getenv()` já é usado  
✅ `.env.example` existe e documenta o que mudar  
✅ Cookies já têm HTTPONLY e SAMESITE  

---

## 5. O Que Precisa Mudar

### 5.1 Estrutura de Carregamento de Secrets

**Atual:**
- Todos os secrets em `.env` (local/versionado)

**Desejado:**
```
Desenvolvimento:
  .env local (com valores de teste)
  
Homologação/Produção:
  Variáveis de ambiente do SO / Azure Key Vault
  (NÃO deve carregar .env)
```

### 5.2 Estratégia de Fallback Seguro

**Atual:**
- `.env` carregado sempre

**Desejado:**
```
if RUNNING_IN_PRODUCTION:
    # Não carregar .env; usar SO env vars
else:
    # Desenvolvimento: carregar .env como fallback
```

### 5.3 Validação Clara

**Atual:**
- `_get_required_str()` valida mas mensagem genérica

**Desejado:**
- Mensagem clara por ambiente indicando se é fallback
- Log de quais secrets foram carregados de onde

---

## 6. Arquivos Impactados para Ajuste

| Arquivo | Mudança | Prioridade |
|---------|---------|-----------|
| `config.py` | Adicionar lógica de ambiente (PROD vs DEV) | 🔴 ALTA |
| `.env` | Remover valores reais, manter como fallback de teste | 🔴 ALTA |
| `.gitignore` | Garantir `.env` está excluído | 🔴 ALTA |
| `web_app/app.py` | Nenhuma (carregamento já centralizado) | ✅ OK |
| `waitress_conf.py` | Nenhuma (já usa variáveis) | ✅ OK |
| Documentação | Criar guia de setp por ambiente | 🔴 ALTA |

---

## 7. Recomendações para Próximas Fases

### Fase B — Secrets

1. Adicionar flag `IS_PRODUCTION` em config.py
2. Modificar `load_dotenv()` para condicional
3. Criar função de diagnóstico de secrets
4. Documentar setp por ambiente

### Fase C — HTTPS

1. Revisar SESSION_COOKIE_SECURE vs HTTPS
2. Documentar quando ativar HTTPS
3. Criar rule de redirect HTTP→HTTPS para web.config

### Fase D — Checklist

1. Incluir validação de secrets
2. Incluir teste de carregamento de variáveis
3. Incluir teste pós-deploy

---

## 8. Veredito da Fase A

✅ **Sistema tem boa estrutura de configuração.**

**Pontos fortes:**
- Centralização em config.py
- Uso de variáveis de ambiente já implementado
- Validação de variáveis obrigatórias
- Fallbacks sensatos

**Pontos de risco:**
- Secrets em `.env` arquivo (risco se versionado)
- Mesmos valores local/homolog/prod
- Falta lógica de ambiente para conditionalizar carregamento

**Ação necessária:**
- Criar lógica de ambiente (PROD vs DEV) em config.py
- Documentar setp claro por ambiente
- Garantir `.env` excluso do git
- Criar script de validação pós-deploy

---

**Responsável:** Claude Code  
**Data:** 2026-04-10  
**Status:** Análise concluída. Pronto para Fase B.
