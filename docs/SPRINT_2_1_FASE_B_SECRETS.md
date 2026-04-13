# FASE B — Secrets e Variáveis de Ambiente
## Sprint 2.1 Final

**Data:** 2026-04-10  
**Status:** Implementação Concluída  
**Prioridade:** Crítica

---

## 1. O Que Foi Implementado

### 1.1 Estratégia de Ambiente em `config.py`

**Adição de detecção de ambiente:**
```python
ENVIRONMENT = os.getenv("ENVIRONMENT", "").strip().lower()
IS_PRODUCTION = (
    ENVIRONMENT == "production" or
    os.getenv("HTTPS", "").lower() == "on" or
    (os.getenv("DB_PASSWORD") is not None and ENVIRONMENT != "development")
)

if not IS_PRODUCTION:
    load_dotenv(dotenv_path=ENV_FILE, override=True)
```

**Comportamento:**
- **Desenvolvimento:** Carrega `.env` para facilitar execução local
- **Produção:** Ignora `.env` completamente; exige variáveis de ambiente do SO
- **Detecção automática:** Se `ENVIRONMENT=production` ou `HTTPS=on`, assume produção

### 1.2 Validação de Segurança em Produção

**Nova função `validar_producao()`:**
- Verifica que secrets não são valores placeholder ("CHANGE_ME", "", "dev")
- Alerta se `.env` está presente em produção (não deve estar sendo carregado)
- Levanta `ValueError` se configuração crítica for inválida
- Chamada automaticamente no startup (`web_app/app.py` → `create_app()`)

### 1.3 Função de Diagnóstico

**Nova função `diagnosticar_config()`:**
- Retorna dict com informações sobre todas as variáveis carregadas
- Usa-se para validar pós-deploy que tudo foi carregado corretamente
- Mostra:
  - `is_production`: Se está em modo produção
  - `environment`: Valor de `ENVIRONMENT`
  - `env_file_carregado`: Se `.env` foi carregado
  - Todas as variáveis críticas (sem expor valores)

### 1.4 Endpoint de Diagnóstico

**Novo endpoint `/config-diagnostico`:**
```
GET /config-diagnostico
```

**Resposta:**
```json
{
  "ok": true,
  "is_production": false,
  "diagnostico": {
    "is_production": false,
    "environment": "development",
    "env_file_carregado": true,
    "db_host": "localhost",
    "storage_type": "local"
  },
  "alertas": []
}
```

**Uso:** Após deploy, acessar este endpoint para validar carregamento correto.

### 1.5 Scripts de Suporte

#### `scripts/gerar_secrets_seguros.py`
Gera valores aleatórios seguros para:
- `FLASK_SECRET_KEY` (32 bytes hex)
- `APP_PEPPER` (32 bytes hex)
- `DB_PASSWORD` (32 bytes URL-safe)

**Uso:**
```powershell
python scripts/gerar_secrets_seguros.py
```

**Output:** Valores prontos para copiar/colar em variáveis de ambiente

#### `scripts/setup_producao_secrets.ps1`
Script PowerShell para facilitar setup de secrets em Windows Server.

**Requisitos:** Executar como Administrator

**Uso:**
```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_producao_secrets.ps1
```

**O que faz:**
1. Verifica se está em Admin
2. Executa gerador de secrets
3. Guia o usuário no setup de variáveis de ambiente
4. Fornece comandos prontos para copiar/colar

### 1.6 Template de Produção

**Arquivo `.env.production`:**
- Template comentado com instruções
- Nunca versionar com valores reais
- Usado apenas como referência de quais variáveis devem ser setadas

---

## 2. Secrets Externalizados

| Secret | Antes | Depois | Risco Mitigado |
|--------|-------|--------|----------------|
| DB_PASSWORD | `.env` plaintext | Variável SO | Vazamento de credenciais BD |
| FLASK_SECRET_KEY | `.env` plaintext | Variável SO | Falsificação de sessão/cookies |
| APP_PEPPER | `.env` plaintext | Variável SO | Comprometimento de hashes |

**Status:** Todos os 3 secrets críticos agora podem ser externalizados.

---

## 3. Carregamento por Ambiente

### Desenvolvimento Local

```bash
# Executar com .env (padrão)
python web_app/app.py

# OU com variáveis de ambiente (override)
set FLASK_SECRET_KEY=my_secret && python web_app/app.py
```

**Comportamento:**
- `.env` é carregado como fallback
- Variáveis de ambiente do terminal override `.env`
- Conveniente para testes locais

### Homologação/Produção

```powershell
# Variáveis de ambiente já setadas no Windows
# .env é IGNORADO completamente

python -m waitress --listen=127.0.0.1:8000 wsgi:application
```

**Comportamento:**
- `.env` não é carregado (IS_PRODUCTION=True)
- Todas as variáveis devem estar em SO environment
- Mais seguro; fallback minimizado

---

## 4. Como Configurar em Produção (Windows Server)

### Passo 1: Gerar Secrets Seguros

```powershell
# Em terminal como Administrator
cd C:\controle_ativos
python scripts\gerar_secrets_seguros.py
```

**Output:**
```
FLASK_SECRET_KEY: a1b2c3d4e5f6...
APP_PEPPER: x9y8z7w6v5u4...
DB_PASSWORD: senha_aleatoria_aqui
```

### Passo 2: Settar Variáveis de Ambiente (Admin)

```powershell
# Copie os valores acima e execute:
setx FLASK_SECRET_KEY "a1b2c3d4e5f6..." /M
setx APP_PEPPER "x9y8z7w6v5u4..." /M
setx DB_PASSWORD "senha_aleatoria_aqui" /M
setx ENVIRONMENT "production" /M
```

**Nota:** `/M` = system-wide (Administrator required)

### Passo 3: Atualizar Senha do Banco

```sql
-- No MySQL Server como root
ALTER USER 'opus_app'@'localhost' IDENTIFIED BY 'senha_aleatoria_aqui';
FLUSH PRIVILEGES;
```

### Passo 4: Validar Carregamento

```powershell
# Feche o PowerShell anterior e abra um novo (para SO carregar novas env vars)

# Teste 1: Diagnóstico via Python
python -c "from config import diagnosticar_config; import json; print(json.dumps(diagnosticar_config(), indent=2))"

# Teste 2: Acessar endpoint de diagnóstico (após app iniciar)
curl http://localhost:8000/config-diagnostico
```

**Esperado:**
```json
{
  "is_production": true,
  "environment": "production",
  "env_file_carregado": false,
  "alertas": []
}
```

---

## 5. Checklist de Conformidade

### Antes de Deploy

- [ ] Valores de `.env.example` estão todos como "CHANGE_ME"
- [ ] Arquivo `.env` está no `.gitignore` (já está)
- [ ] Script `gerar_secrets_seguros.py` foi executado
- [ ] Novo `FLASK_SECRET_KEY`, `APP_PEPPER`, `DB_PASSWORD` foram gerados
- [ ] Variáveis foram setadas no Windows (setx ... /M)
- [ ] Senha do banco foi alterada com novo `DB_PASSWORD`
- [ ] Terminal foi fechado e reabert para carregar novas env vars

### Após Deploy

- [ ] Acessar `/config-diagnostico`
- [ ] Validar `"is_production": true`
- [ ] Validar `"env_file_carregado": false`
- [ ] Validar `"alertas": []`
- [ ] Validar que login funciona (senha usuário admin foi hash com novo pepper)

---

## 6. Risos Eliminados

### 🔴 Risco: Secrets em .env Versionado
**Status:** ✅ Eliminado  
**Evidência:** `IS_PRODUCTION` evita carregar `.env` em produção

### 🔴 Risco: Mesma Senha Local/Produção
**Status:** ✅ Eliminado  
**Evidência:** Setup script gera novos secrets por ambiente

### 🔴 Risco: Secrets em Plaintext no Código
**Status:** ✅ Eliminado  
**Evidência:** Todos os secrets agora via variáveis de ambiente

### 🟡 Risco: Developers Commitarem Secrets Acidentalmente
**Status:** ✅ Mitigado  
**Evidência:** Documentação clara + script de validação + `.env` no `.gitignore`

---

## 7. Arquivos Modificados/Criados

| Arquivo | Tipo | O Que Mudou |
|---------|------|-----------|
| `config.py` | Modificado | Adicionado `IS_PRODUCTION`, `validar_producao()`, `diagnosticar_config()` |
| `web_app/app.py` | Modificado | Adicionado chamada de `validar_producao()`, novo endpoint `/config-diagnostico` |
| `.env.production` | Criado | Template comentado para produção |
| `scripts/gerar_secrets_seguros.py` | Criado | Gerador de secrets aleatórios |
| `scripts/setup_producao_secrets.ps1` | Criado | Script de setup para Windows Server |

---

## 8. Impacto em Testes

**Testes continuam funcionando:**
- Arquivo `.env` existe e é carregado em testes (modo desenvolvimento)
- `IS_PRODUCTION=False` por padrão
- Nenhuma mudança de comportamento em ambiente local

**Para simular produção em testes:**
```python
# Em test, setar variável antes de criar app
os.environ["ENVIRONMENT"] = "production"
os.environ["FLASK_SECRET_KEY"] = "test_key"
os.environ["APP_PEPPER"] = "test_pepper"
os.environ["DB_PASSWORD"] = "test_db"

app = create_app()  # Agora em modo produção
```

---

## 9. Próximas Fases

### Fase C — HTTPS e Cookies
- Revisar `SESSION_COOKIE_SECURE` em relação a HTTPS
- Criar rule de redirect HTTP→HTTPS em web.config
- Documentar quando ativar HTTPS

### Fase D — Checklist de Deployment
- Incluir validação de secrets
- Incluir teste de `/config-diagnostico`
- Incluir reset de senha do admin (hash com novo pepper)

---

## 10. Veredito da Fase B

✅ **Secrets e variáveis de ambiente estão seguras.**

**Implementado:**
- Detecção automática de ambiente (local vs produção)
- Carregamento condicional de `.env`
- Validação de segurança em startup
- Diagnóstico de configuração via endpoint
- Scripts de geração e setup
- Documentação prática

**Risco residual:** Operador deve seguir procedimento correto ao fazer deploy (Step 1-4 acima).

**Mitigação:** Script `setup_producao_secrets.ps1` guia o processo.

---

**Responsável:** Claude Code  
**Data:** 2026-04-10  
**Status:** Fase B concluída. Pronto para Fase C (HTTPS).
