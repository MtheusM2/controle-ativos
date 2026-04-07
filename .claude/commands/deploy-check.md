---
description: Executar checklist completo pré-deploy do controle-ativos para ambiente de produção Windows Server. Identifica o que está faltando ou incorreto antes de subir o sistema.
---

# /deploy-check — Checklist Pré-Deploy (Windows Server)

**Ambiente alvo:** $ARGUMENTS

---

Você vai executar um diagnóstico completo do estado atual do projeto para validar se está pronto para deploy em produção no **Windows Server + IIS + Waitress + NSSM**.

Examine os arquivos listados em cada etapa e emita um relatório com status **OK**, **ATENÇÃO** ou **BLOQUEADOR** para cada item.

## 1. Código e Configuração

Verificar:
- `config.py` — todas as variáveis obrigatórias usam `_get_required_str()` ou `_get_int()`?
- `.env.example` — lista todas as variáveis necessárias com descrição? Está atualizado?
- `web_app/app.py` — `FLASK_DEBUG` vem de `config.py`, não hardcodado?
- `wsgi.py` — aponta para `create_app()` / `application` corretamente?
- `waitress_conf.py` — thread count, body size limit e HOST configurados?

## 2. Segurança de Aplicação

Verificar:
- `utils/crypto.py` — usa PBKDF2 com pepper (não MD5/SHA1/bcrypt sem pepper)?
- `web_app/routes/auth_routes.py` — `session.clear()` antes de `session["user_id"]`?
- `web_app/app.py` — `SESSION_COOKIE_HTTPONLY=True`, `SAMESITE="Lax"`, `MAX_CONTENT_LENGTH` configurado?
- `services/ativos_service.py` — filtros por `empresa_id` em todas as queries de listagem?
- Nenhum `FLASK_DEBUG=1` hardcodado em qualquer arquivo do projeto?

## 3. Banco de Dados

Verificar:
- `database/schema.sql` — reflete o estado atual incluindo todas as migrações?
- `database/migrations/` — listar todas as migrações; estão numeradas sequencialmente?
- `database/security/001_create_opus_app.sql` — usuário de produção com permissões mínimas?
- `.env.example` inclui `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME`?

## 4. Arquivos de Deploy Windows

Verificar:
- `deploy/iis/web.config` — existe e está configurado?
  - [ ] `proxy_pass` aponta para `http://127.0.0.1:8000`?
  - [ ] Headers de segurança presentes? (`X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Content-Security-Policy`)
  - [ ] Bloqueio de acesso direto a `static/uploads/` (HTTP 403)?
  - [ ] `maxAllowedContentLength` alinhado com `MAX_CONTENT_LENGTH` do Flask (10 MB)?
- `deploy/nssm/install_service.ps1` — existe e está atualizado?
  - [ ] Aponta para `.venv\Scripts\python.exe`?
  - [ ] Comando Waitress usa `wsgi:application`?
  - [ ] Lê variáveis do `.env`?
  - [ ] Configura logs em `logs\`?
  - [ ] Configura restart automático em falha?
- `scripts/setup_server.ps1` — existe e cobre virtualenv, diretórios e diagnóstico?
- `waitress_conf.py` — configurado corretamente?

## 5. Dependências e Compatibilidade

Verificar:
- `requirements.txt` — inclui todas as dependências de produção? (`waitress`, `mysql-connector-python`, `reportlab`, `openpyxl`, etc.)
- `waitress` presente e sem Gunicorn como dependência obrigatória?
- Versões pinadas — sem ranges abertos (`>=`) que possam causar quebra?

## 6. Gitignore e Arquivos Sensíveis

Verificar:
- `.gitignore` — `.env`, `logs/`, `web_app/static/uploads/`, `__pycache__/`, `.venv/` ignorados?
- `docs_interno_local/` está no `.gitignore`?
- Nenhum arquivo `.env` ou credencial rastreado pelo git?

## 7. Testes

Verificar:
- `pytest.ini` — configurado corretamente?
- `tests/conftest.py` — fixtures funcionais com injeção de services?
- Testes existentes cobrem os fluxos críticos (auth, ativos, export)?

## 8. Documentação

Verificar:
- `docs/DEPLOYMENT.md` — passo a passo correto para Windows Server?
- `docs/SETUP_SERVIDOR_ZERADO.md` — existe e cobre setup desde servidor zerado?
- `README.md` — seção Deployment reflete stack Windows Server (IIS + Waitress + NSSM)?

## Relatório Final

Emitir tabela com status de cada categoria:

| Categoria             | Status                   | Observações                    |
|-----------------------|--------------------------|-------------------------------|
| Código e Configuração | OK/ATENÇÃO/BLOQUEADOR    | ...                           |
| Segurança             | OK/ATENÇÃO/BLOQUEADOR    | ...                           |
| Banco de Dados        | OK/ATENÇÃO/BLOQUEADOR    | ...                           |
| Arquivos de Deploy    | OK/ATENÇÃO/BLOQUEADOR    | ...                           |
| Dependências          | OK/ATENÇÃO/BLOQUEADOR    | ...                           |
| Gitignore             | OK/ATENÇÃO/BLOQUEADOR    | ...                           |
| Testes                | OK/ATENÇÃO/BLOQUEADOR    | ...                           |
| Documentação          | OK/ATENÇÃO/BLOQUEADOR    | ...                           |

**Veredito final:**
- **PRONTO PARA DEPLOY** — sem bloqueadores
- **CONDICIONAL** — há atenções a resolver, mas nenhum bloqueador crítico
- **NÃO PRONTO** — há bloqueadores que impedem deploy seguro

Listar os **próximos passos** em ordem de prioridade.
