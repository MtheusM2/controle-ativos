# CLAUDE.md — controle-ativos

> Base de conhecimento do projeto para o Claude Code.
> Este arquivo é carregado automaticamente em toda sessão.

---

## Identidade do Projeto

**Nome:** controle-ativos
**Tipo:** Sistema corporativo interno de gestão de ativos de TI
**Repositório:** MtheusM2/controle-ativos
**Stack:** Python 3.11 · Flask 2.3 · MySQL 8 · Jinja2 · HTML/CSS/JS · Waitress · IIS · NSSM
**Ambiente de desenvolvimento:** Windows 11; produção em Windows Server

---

## Arquitetura da Aplicação

```
controle_ativos/
├── app.py                  # Entry point de desenvolvimento
├── wsgi.py                 # Entry point de produção (Waitress target: wsgi:application)
├── main.py                 # Alias de entry point
├── config.py               # Leitura centralizada de variáveis de ambiente
├── waitress_conf.py        # Configuração do Waitress (host, porta, threads)
│
├── web_app/
│   ├── app.py              # create_app() — factory pattern com injeção de services
│   ├── routes/
│   │   ├── auth_routes.py  # Login, logout, registro, recuperação de senha, configurações
│   │   └── ativos_routes.py# CRUD de ativos, filtros, exportação, anexos
│   ├── templates/          # Jinja2 — base.html + partials (sidebar, topbar, flash)
│   └── static/css/style.css
│
├── services/               # Camada de negócio (sem acesso direto ao banco de dados)
│   ├── auth_service.py     # AuthService — autenticação, sessão, recuperação
│   ├── ativos_service.py   # AtivosService — CRUD de ativos com escopo por empresa
│   ├── ativos_arquivo_service.py # Gestão de anexos físicos
│   ├── empresa_service.py  # EmpresaService — listagem de empresas
│   └── sistema_ativos.py   # Facade de nível superior
│
├── models/
│   ├── ativos.py           # Dataclass Ativo
│   └── usuario.py          # Dataclass Usuario
│
├── database/
│   ├── connection.py       # cursor_mysql() — context manager
│   ├── schema.sql          # Schema completo (source of truth)
│   ├── init_db.py          # Script de inicialização
│   ├── migrations/         # Migrações SQL numeradas (001_, 002_, ...)
│   └── security/           # Scripts de segurança do banco
│
├── utils/
│   ├── crypto.py           # Hash de senha com pepper (PBKDF2)
│   ├── csrf.py             # Geração e validação de tokens CSRF (itsdangerous)
│   ├── validators.py       # Validação de campos de ativo
│   ├── validacoes.py       # Validação de campos de usuário
│   └── logging_config.py   # Configuração de logging estruturado
│
├── deploy/
│   ├── iis/web.config      # Reverse proxy IIS + headers de segurança
│   └── nssm/install_service.ps1  # Instala Waitress como serviço Windows
│
├── scripts/                # Scripts PowerShell (setup, diagnóstico, simulação)
├── tests/                  # pytest — conftest.py com injeção de services mockados
└── docs/                   # Documentação pública do deploy e segurança
```

---

## Modelo de Dados — Entidades Principais

| Entidade    | Tabela       | Chave primária        | Notas                                            |
|-------------|-------------|----------------------|--------------------------------------------------|
| Empresa     | `empresas`   | `id` INT AUTO        | Multi-tenant: cada usuário pertence a 1 empresa  |
| Usuário     | `usuarios`   | `id` INT AUTO        | Perfis: `usuario` ou `adm`                       |
| Ativo       | `ativos`     | `id` VARCHAR(20)     | ID alfanumérico customizado (ex: `NTB-001`)      |
| Arquivo     | `ativos_arquivos` | `id` INT AUTO   | Anexos físicos vinculados a um ativo             |

**Regras de negócio críticas:**
- Usuário comum acessa **apenas** ativos da própria `empresa_id`
- Admin (`perfil = 'adm'` ou `'admin'`) acessa ativos de **todas** as empresas
- Ativo com `status = 'Em Uso'` **exige** `usuario_responsavel` preenchido (validado na aplicação)
- Migrações são aplicadas sequencialmente via scripts numerados em `database/migrations/`

---

## Segurança — Pontos Críticos

| Mecanismo                | Implementação                                               |
|--------------------------|-------------------------------------------------------------|
| Hash de senha            | PBKDF2 + pepper via `utils/crypto.py`                       |
| Sessão Flask             | `SESSION_COOKIE_HTTPONLY=True`, `SAMESITE=Lax`, `SECURE` em prod |
| Bloqueio de login        | `tentativas_login_falhas` + `bloqueado_ate` na tabela usuarios |
| Usuário de banco         | `opus_app` — permissões mínimas (sem GRANT, sem DROP)       |
| Upload de arquivos       | `MAX_CONTENT_LENGTH = 10 MB`, validação de extensão no service |
| LGPD                     | Dados pessoais: `nome`, `email` de usuários; adequação em andamento |

**NUNCA** commitar arquivos `.env`, credenciais ou segredos. O `.gitignore` já os exclui.

---

## Padrões de Desenvolvimento

### Python / Flask
- Serviços **nunca** acessam o banco diretamente — usam `cursor_mysql()` de `database/connection.py`
- Factory pattern em `create_app()` com injeção de services para facilitar testes
- Exceções de domínio explícitas (ex: `AtivoNaoEncontrado`, `CredenciaisInvalidas`) — nunca exceções genéricas
- Respostas JSON padronizadas: `{"ok": True/False, "mensagem"/"erro": "..."}` + status HTTP correto
- Variáveis de ambiente lidas **apenas** em `config.py`

### Banco de Dados
- Queries com parâmetros `%s` — nunca interpolação de strings
- `cursor_mysql()` retorna tupla `(conn, cur)` — sempre desempacotar como `with cursor_mysql() as (conn, cur):`
- `cursor_mysql()` usa `dictionary=True` por padrão (retorna dicts ao invés de tuples)
- Novas colunas → nova migração SQL numerada em `database/migrations/`
- Schema em `database/schema.sql` é a source of truth para novos ambientes
- **Importante:** `cursor_mysql()` controla auto-commit; conexão é commitada ao sair do bloco `with` ou faz rollback em caso de exceção

### Frontend (Jinja2 + CSS + JS)
- `base.html` é o layout principal com `{% block content %}`
- Partials em `templates/partials/`: `sidebar.html`, `topbar.html`, `flash_messages.html`
- CSS em `web_app/static/css/style.css` — sem frameworks externos (Bootstrap não está no projeto)
- Formulários usam `fetch()` com JSON para rotas de ação; navegação tradicional para GET
- Flash messages: categorias `success`, `danger`, `info`, `warning`
- **Templates em uso:** `index.html` (login), `register.html` (cadastro), `recovery.html` (recuperação), `dashboard.html`, `ativos.html`, `novo_ativo.html`, `editar_ativo.html`, `detalhe_ativo.html`, `importar_ativos.html`, `configuracoes.html`

### Testes
- Framework: pytest com configuração em `pytest.ini`
- `conftest.py` injeta services mockados via `service_overrides` do `create_app()`
- **Não usar mocks de banco** — serviços de teste usam implementações reais com banco de teste isolado
- Rodar testes: `pytest tests/`

---

## Comandos Frequentes

```powershell
# Desenvolvimento local
scripts/start_local.ps1

# Simular produção (Waitress, sem debug)
scripts/simulate_production.ps1

# Testes
pytest tests/ -v

# Diagnóstico de configuração
---

## Correção de Schema Parcial (Migration 006)

**Problema:** Import de ativos retorna HTTP 500 ("Unknown column 'codigo_interno'")

**Causa Raiz:** Migration 006 não aplicada (usuario `opus_app` sem permissão ALTER TABLE)

**Solução Implementada:** Sistema detecta schema real em runtime e adapta queries dynamicamente

**Status:** ✅ Implementado e testado | ⏳ Migration 006 pendente (DBA/admin)

**Detalhes:**
- Código agora suporta schema com 15 colunas (legacy) OU 45+ colunas (pós-migration)
- `diagnosticar_schema_ativos()` retorna status de cada coluna
- Imports descartam apenas campos indisponíveis no banco, com logging
- Zero data loss garantido durante transição

**Próximas Etapas (Operacional):**
1. Restart serviço NSSM e validar dashboard/import sem erros
2. DBA aplica migration 006: `docs/MIGRATION_006_SCHEMA_PARTIAL.md`
3. Restart serviço e confirmar "Schema completo" nos logs

**Documentação:** `docs/MIGRATION_006_SCHEMA_PARTIAL.md` | `RELATORIO_CORRECAO_500_ERROR.md`

---


- **Servidor:** Windows Server 2019+
- **Process manager:** NSSM → `deploy/nssm/install_service.ps1`
- **Reverse proxy:** IIS (ARR + URL Rewrite) → `deploy/iis/web.config`
- **WSGI server:** Waitress → `waitress_conf.py` (target: `wsgi:application`)
- **Path de instalação:** `C:\controle_ativos`
- **Documentação completa:** `docs/DEPLOYMENT.md`
- **Rotação de credenciais DB:** `docs/SECURITY_DB_ROTATION_GUIDE.md`

---

## Agentes Disponíveis

| Agent                  | Quando Acionar                                              |
|------------------------|-------------------------------------------------------------|
| `backend-engineer`     | Lógica de negócio, services, rotas Flask, models, config    |
| `frontend-engineer`    | Templates Jinja2, CSS, JavaScript, UX/UI de telas           |
| `security-auditor`     | Revisão de segurança, hardening, análise de vulnerabilidades |
| `db-architect`         | Schema, migrações SQL, queries, índices, performance         |
| `deploy-engineer`      | IIS, NSSM, Waitress, scripts de deploy, ambiente Windows Server |
| `qa-engineer`          | Escrita e revisão de testes, cobertura, qualidade de código  |

---

## Comandos Disponíveis (Skills)

| Comando              | Descrição                                              |
|----------------------|--------------------------------------------------------|
| `/feature`           | Implementar nova funcionalidade end-to-end             |
| `/bugfix`            | Diagnosticar e corrigir um bug                         |
| `/security-review`   | Auditoria de segurança em um arquivo ou módulo         |
| `/db-migration`      | Criar nova migração SQL para o banco                   |
| `/deploy-check`      | Checklist pré-deploy para ambiente de produção         |
| `/refactor`          | Refatoração cirúrgica de código existente              |
| `/lgpd-check`        | Verificação de adequação prática à LGPD                |

---

## O que NÃO Fazer

- Não usar `SELECT *` — especificar colunas explicitamente
- Não interpolar variáveis em queries SQL — usar parâmetros `%s`
- Não escrever lógica de negócio em rotas — colocar nos services
- Não commitar `.env`, `logs/`, arquivos de upload ou `docs_interno_local/`
- Não criar helpers genéricos para uso único — só abstrair quando há 3+ usos reais
- Não adicionar dependências externas sem avaliar impacto de segurança e licença
- Não quebrar a interface `create_app()` — manter suporte a `service_overrides`

## Regra obrigatória de contrato entre camadas

Sempre que um campo do domínio mudar de nome ou um novo objeto de mapeamento for introduzido, revisar obrigatoriamente:
- parser
- mapper
- validators
- services
- rotas web
- templates/JSON
- auditoria/log
- testes unitários
- testes de integração

Nunca assumir que nomes antigos e novos coexistem sem uma camada explícita de compatibilidade.

Todo bug de integração deve gerar:
1. correção da causa raiz
2. teste de regressão
3. verificação dos consumidores e produtores do mesmo contrato


# Regras obrigatórias do projeto

## Objetivo
Evitar regressões, inconsistências de contrato entre camadas e erros fantasmas no sistema de gestão de ativos.

## Antes de qualquer alteração
1. Ler traceback completo quando houver erro.
2. Identificar causa raiz antes de refatorar.
3. Mapear fluxo ponta a ponta:
   - rota
   - service
   - utils
   - validators
   - model
   - banco
   - template/json
4. Verificar contratos entre produtor e consumidor de dados.

## Regra de contratos
Sempre que uma função consumir objetos produzidos por outra camada, validar:
- nome real dos atributos
- tipo real em runtime
- type hints
- dataclass/DTO real
- formato usado em testes
- compatibilidade entre preview e confirmação

Nunca assumir estrutura sem verificar a definição real do objeto.

## Regra de correção
Toda correção deve:
- atacar causa raiz
- incluir comentários no código alterado
- verificar impactos correlatos
- adicionar ou ajustar testes de regressão

## Testes obrigatórios quando houver bug
Criar ou revisar:
- teste unitário da função quebrada
- teste unitário do contrato do objeto envolvido
- teste de integração do fluxo principal
- teste de regressão reproduzindo o erro real

## Checklist anti-erro fantasma
Verificar sempre:
- nomes de campos iguais entre frontend/backend
- dict vs objeto
- atributo vs chave
- listas homogêneas
- normalização consistente
- mensagens de erro compatíveis com a causa real
- mocks alinhados com produção

## Proibição
Não declarar “corrigido” sem:
- rodar testes relevantes
- validar o fluxo manualmente
- verificar se o erro pode reaparecer em outra etapa do pipeline