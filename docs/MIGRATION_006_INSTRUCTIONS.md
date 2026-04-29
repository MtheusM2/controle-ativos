## Migration 006 — Instruções para DBA

Resumo
------
Arquivo: `database/migrations/006_cadastro_base_e_especificacoes_ativos.sql`

Objetivo: aplicar alterações de schema (ALTER TABLE) que adicionam colunas opcionais usadas pela versão atual do aplicativo.

IMPORTANTE: esta migration executa `ALTER TABLE` — deve ser aplicada por um usuário administrador do MySQL (root/DBA).
Nunca execute esta migration usando o usuário da aplicação (`opus_app`).

Local do arquivo
-----------------
`C:\Users\OPUSMANUALSERVER\Documents\sistema\controle-ativos\database\migrations\006_cadastro_base_e_especificacoes_ativos.sql`

Passos seguros (Windows, linha de comando MySQL)
----------------------------------------------
1. Fazer backup do banco antes de qualquer alteração:

   - Exemplo (não inclui senha explicitamente; o prompt pedirá a senha do usuário administrativo):

```powershell
mysqldump -u root -p --routines --triggers --events controle_ativos > controle_ativos_pre_mig_006.sql
```

2. Revisar o arquivo `006_...sql` para entender mudanças e índices adicionados.

3. Em janela com privilégios de administrador (conta MySQL com ALTER TABLE), aplicar a migration:

```powershell
mysql -u root -p controle_ativos < "C:\Users\OPUSMANUALSERVER\Documents\sistema\controle-ativos\database\migrations\006_cadastro_base_e_especificacoes_ativos.sql"
```

4. Verificar se colunas foram aplicadas (exemplo seguro sem expor senhas):

```powershell
mysql -u root -p -e "USE controle_ativos; SHOW COLUMNS FROM ativos LIKE 'codigo_interno'\G"
```

5. Testar a aplicação em staging/produção controlada:

   - Reinicie o serviço Windows `controle_ativos` (NSSM/Waitress) quando pronto.
   - Verifique logs e endpoints `/health` e `/dashboard`.

Notas de segurança e operações
------------------------------
- Não inserir senhas em arquivos versionados.
- Não execute `ALTER TABLE` com o usuário `opus_app` — ele deve permanecer sem privilégios DDL.
- Considere aplicar migration em janela de manutenção; índices adicionais podem afetar performance durante execução.
- Se não for possível downtime, avalie aplicar em réplica ou durante janela de baixa atividade.

Se precisar de assistência, forneça ao DBA este documento e o caminho para o arquivo de migration; não compartilhe credenciais.
