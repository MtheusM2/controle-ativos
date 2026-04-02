# Guia de Rotação de Acesso MySQL (Opus Assets)

Este guia descreve como remover dependência de `root` no runtime da aplicação,
padronizar configuração via `.env` e validar a conexão com usuário dedicado.

## 1) Criar usuário dedicado no MySQL

Execute o script SQL com uma conta administrativa:

```sql
SOURCE database/security/001_create_opus_app.sql;
```

Alternativa via terminal MySQL:

```sql
CREATE USER IF NOT EXISTS 'opus_app'@'localhost' IDENTIFIED BY 'CHANGE_ME_STRONG_PASSWORD';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX ON `controle_ativos`.* TO 'opus_app'@'localhost';
FLUSH PRIVILEGES;
```

## 2) Atualizar arquivo .env

Configure o `.env` com os valores de produção/local adequados:

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=opus_app
DB_PASSWORD=SUA_SENHA_FORTE
DB_NAME=controle_ativos
FLASK_SECRET_KEY=SUA_CHAVE_SECRETA
APP_PEPPER=SEU_PEPPER_SEGURO
```

## 3) Rodar diagnóstico de configuração

No diretório raiz do projeto:

```bash
python scripts/diagnose_runtime_config.py
```

Resultado esperado:
- caminho do `.env` carregado
- variáveis DB em runtime
- segredos mascarados
- status de conexão MySQL

## 4) Testar conexão SQL efetiva

```bash
python scripts/test_db_connection.py
```

Resultado esperado:
- `Conexão com banco: SUCESSO`
- `CURRENT_USER()` retornando `opus_app@localhost` (ou equivalente)
- `DATABASE()` retornando `controle_ativos`

## 5) Validar aplicação web

Execute a aplicação normalmente e teste:
- autenticação
- CRUD de ativos
- filtros
- upload
- recuperação de senha

## 6) Confirmar que não usa root

Confirmações objetivas:
- `DB_USER=opus_app` no `.env`
- scripts de diagnóstico sem menção a `root`
- `CURRENT_USER()` no teste retornando `opus_app@localhost`
