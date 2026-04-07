---
description: Implementar nova funcionalidade no controle-ativos de forma end-to-end — backend, frontend, banco e testes.
---

# /feature — Implementar nova funcionalidade

**Funcionalidade solicitada:** $ARGUMENTS

---

Você vai implementar essa funcionalidade no projeto **controle-ativos** seguindo o processo abaixo. Não pule etapas.

## 1. Entender o escopo antes de escrever código

Responda antes de começar:
- Quais tabelas do banco são afetadas? Nova migração SQL é necessária?
- Quais services precisam ser criados ou modificados?
- Quais rotas HTTP são necessárias (GET/POST, URL, resposta esperada)?
- Quais templates precisam ser criados ou modificados?
- Qual regra de controle de acesso se aplica (usuário comum vs admin, escopo por empresa)?

## 2. Banco de dados (se necessário)

Se a feature requer nova coluna ou tabela:
1. Criar migração SQL em `database/migrations/NNN_descricao.sql`
2. Seguir o padrão: `ALTER TABLE ... ADD COLUMN` com `DEFAULT` explícito
3. Adicionar índice se o campo será usado em filtros
4. Atualizar `database/schema.sql` com a alteração

## 3. Model (se necessário)

Se a feature introduz novo tipo de dado:
- Criar ou atualizar dataclass em `models/`
- Tipos simples, sem lógica de negócio nos models

## 4. Service

- Criar ou estender service em `services/`
- Toda lógica de negócio fica aqui — nunca na rota
- Definir exceções de domínio explícitas para casos de erro
- Validar permissões de acesso por `empresa_id` antes de qualquer operação
- Usar `cursor_mysql()` com parâmetros `%s` — sem interpolação

## 5. Rota Flask

- Registrar rota em `web_app/routes/ativos_routes.py` ou `auth_routes.py`
- Rota é thin controller: valida entrada → chama service → formata resposta
- Resposta JSON: `{"ok": True/False, "mensagem"/"erro": "...", ...payload}`
- Status HTTP correto: 200, 201, 400, 401, 403, 404, 409

## 6. Template (se necessário)

- Criar ou modificar template em `web_app/templates/`
- Herdar de `base.html` com `{% extends "base.html" %}`
- Usar partials existentes (`flash_messages.html`, `sidebar.html`, `topbar.html`)
- Formulários com `fetch()` JSON para rotas de ação; GET tradicional para páginas
- Exibir estado de loading e feedback de erro/sucesso

## 7. Testes

Para cada caminho da feature, escrever ou atualizar teste em `tests/`:
- Caminho feliz (operação bem-sucedida)
- Casos de erro esperados (validação, permissão, não encontrado)
- Caso de lista vazia (se a feature lista registros)

## 8. Verificação final

Antes de concluir, confirmar:
- [ ] `pytest tests/ -v` — todos os testes passando
- [ ] Nenhum `SELECT *` introduzido — colunas explícitas
- [ ] Nenhuma variável de ambiente lida fora de `config.py`
- [ ] Nenhuma lógica de negócio na rota
- [ ] Nenhum segredo hardcodado
- [ ] Controle de acesso verificado antes de qualquer operação no banco
- [ ] Migração SQL criada se necessário
