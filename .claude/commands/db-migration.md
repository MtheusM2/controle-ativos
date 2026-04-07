---
description: Criar nova migração SQL para o banco de dados do controle-ativos, seguindo os padrões e convenções do projeto.
---

# /db-migration — Criar Migração SQL

**Descrição da mudança:** $ARGUMENTS

---

Você vai criar uma nova migração SQL para o projeto **controle-ativos**.

## Passo 1 — Determinar o número da próxima migração

Liste os arquivos em `database/migrations/` e identifique o maior número existente.
O próximo número é esse + 1, com 3 dígitos (ex: se existir `005_`, criar `006_`).

## Passo 2 — Definir nome do arquivo

Formato: `NNN_descricao_em_snake_case.sql`
- Sem acentos, sem espaços
- Descrição deve indicar o que a migração faz: `adicionar_coluna_X_em_Y`, `criar_tabela_Z`, `renomear_coluna_A_para_B`

## Passo 3 — Escrever a migração

### Template base

```sql
-- =========================================================
-- MIGRAÇÃO NNN: <descrição legível do que muda e por quê>
-- Data: YYYY-MM-DD
-- =========================================================

USE controle_ativos;

-- <instrução SQL>

-- ROLLBACK: <instrução SQL inversa para reverter>
```

### Regras obrigatórias

**ADD COLUMN em tabela com dados existentes:**
```sql
-- Sempre com DEFAULT explícito para NOT NULL
ALTER TABLE usuarios
    ADD COLUMN nova_coluna TINYINT(1) NOT NULL DEFAULT 0 AFTER coluna_existente;
```

**DROP COLUMN (destrutivo — exige cautela):**
```sql
-- Verificar se nenhuma query da aplicação usa esta coluna antes de executar
-- Fazer backup antes de aplicar em produção
ALTER TABLE ativos DROP COLUMN coluna_obsoleta;
-- ROLLBACK: ALTER TABLE ativos ADD COLUMN coluna_obsoleta VARCHAR(100) NULL;
```

**Adicionar índice:**
```sql
-- Apenas se o campo vai ser usado em WHERE, JOIN ou ORDER BY
CREATE INDEX idx_tabela_campo ON tabela (campo);
-- ROLLBACK: DROP INDEX idx_tabela_campo ON tabela;
```

**Nova tabela:**
```sql
CREATE TABLE IF NOT EXISTS nova_tabela (
    id INT NOT NULL AUTO_INCREMENT,
    campo VARCHAR(100) NOT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
-- ROLLBACK: DROP TABLE IF EXISTS nova_tabela;
```

## Passo 4 — Atualizar database/schema.sql

Após criar a migração, refletir a mudança no `database/schema.sql` (source of truth para novos ambientes).
Exemplo: se adicionou coluna, adicionar a coluna também na definição `CREATE TABLE` do schema.

## Passo 5 — Verificar impacto na aplicação

Se a migração:
- Adiciona coluna → verificar se o service ou model precisa ser atualizado para ler/escrever o novo campo
- Renomeia coluna → buscar todas as queries que referenciam o nome antigo (`Grep` por `"nome_antigo"`)
- Remove coluna → garantir que nenhuma query referencia a coluna removida
- Cria tabela → o service correspondente deve ser criado ou atualizado

## Passo 6 — Instrução de aplicação

Ao final, informar o comando para aplicar a migração:

```bash
# Em desenvolvimento
mysql -u root -p controle_ativos < database/migrations/NNN_descricao.sql

# Em produção (como opus_app ou usuário com DDL permitido na migração)
mysql -u DB_USER -p controle_ativos < database/migrations/NNN_descricao.sql
```
