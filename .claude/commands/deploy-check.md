---
description: Executar checklist completo pré-deploy do controle-ativos para ambiente de produção Linux. Identifica o que está faltando ou incorreto antes de subir o sistema.
---

# /deploy-check — Checklist Pré-Deploy

**Ambiente alvo:** $ARGUMENTS

---

Você vai executar um diagnóstico completo do estado atual do projeto para validar se está pronto para deploy em produção.

Examine os arquivos listados em cada etapa e emita um relatório com status **OK**, **ATENÇÃO** ou **BLOQUEADOR** para cada item.

## 1. Código e Configuração

Verificar:
- `config.py` — todas as variáveis obrigatórias usam `_get_required_str()` ou `_get_int()`?
- `.env.example` — lista todas as variáveis necessárias com descrição? Está atualizado?
- `web_app/app.py` — `FLASK_DEBUG` vem de `config.py`, não hardcodado?
- `gunicorn.conf.py` — configurado para socket Unix (não porta direta)?
- `wsgi.py` — aponta para `create_app()` corretamente?

## 2. Segurança de Aplicação

Verificar:
- `utils/crypto.py` — usa bcrypt com pepper (não MD5/SHA1)?
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

## 4. Arquivos de Deploy

Verificar:
- `deploy/nginx/controle_ativos.conf` — headers de segurança presentes? (`X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`)?
- `deploy/nginx/controle_ativos.conf` — redirecionamento HTTP→HTTPS configurado?
- `deploy/nginx/controle_ativos.conf` — `proxy_pass` aponta para socket Unix (não porta)?
- `deploy/systemd/controle_ativos.service` — `User=`, `EnvironmentFile=`, `Restart=on-failure` configurados?
- `deploy/systemd/controle_ativos.service` — hardening básico: `NoNewPrivileges=true`, `PrivateTmp=true`?
- `scripts/setup_server.sh` — existe e está atualizado?

## 5. Dependências e Compatibilidade

Verificar:
- `requirements.txt` — inclui todas as dependências de produção? (`gunicorn`, `mysql-connector-python`, `reportlab`, `openpyxl`, etc.)
- Sem dependências de desenvolvimento (`pytest`, ferramentas de build) no requirements de produção?
- Verificar versões pinadas — sem ranges abertos (`>=`) que possam causar quebra?

## 6. Gitignore e Arquivos Sensíveis

Verificar:
- `.gitignore` — `.env`, `logs/`, `web_app/static/uploads/`, `__pycache__/`, `.venv/` ignorados?
- `docs_interno_local/` está no `.gitignore`?
- Nenhum arquivo `.env` ou credencial rastreado pelo git?

## 7. Testes

Verificar:
- `pytest.ini` — configurado corretamente?
- `tests/conftest.py` — fixtures funcionais com injeção de services?
- `tests/test_app.py` — testes existentes cobrem os fluxos críticos?

## Relatório Final

Emitir tabela com status de cada categoria:

| Categoria             | Status      | Observações                    |
|-----------------------|-------------|-------------------------------|
| Código e Configuração | OK/ATENÇÃO/BLOQUEADOR | ...                  |
| Segurança             | OK/ATENÇÃO/BLOQUEADOR | ...                  |
| Banco de Dados        | OK/ATENÇÃO/BLOQUEADOR | ...                  |
| Arquivos de Deploy    | OK/ATENÇÃO/BLOQUEADOR | ...                  |
| Dependências          | OK/ATENÇÃO/BLOQUEADOR | ...                  |
| Gitignore             | OK/ATENÇÃO/BLOQUEADOR | ...                  |
| Testes                | OK/ATENÇÃO/BLOQUEADOR | ...                  |

**Veredito final:**
- **PRONTO PARA DEPLOY** — sem bloqueadores
- **CONDICIONAL** — há atenções a resolver, mas nenhum bloqueador crítico
- **NÃO PRONTO** — há bloqueadores que impedem deploy seguro

Listar os **próximos passos** em ordem de prioridade.
