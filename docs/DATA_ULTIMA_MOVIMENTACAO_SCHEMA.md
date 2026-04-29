## `data_ultima_movimentacao` - schema seguro

Este sistema trata `data_ultima_movimentacao` como campo opcional de movimentação.
O código agora tolera schema parcial, mas o schema definitivo deve conter a coluna para registrar a última movimentação do ativo.

Se a coluna ainda não existir, um DBA pode aplicá-la com um usuário administrador do MySQL:

```sql
ALTER TABLE ativos
    ADD COLUMN IF NOT EXISTS data_ultima_movimentacao DATETIME NULL DEFAULT NULL AFTER updated_at;
```

Observações:
- Execute apenas com conta administrativa/root.
- Não usar `opus_app` para `ALTER TABLE`.
- A aplicação não depende de `.env` para esta alteração.
- O tipo `DATETIME NULL` é seguro para o objetivo da aplicação; o código só precisa da presença da coluna, não de um tipo específico para a leitura.
