# Problema de Schema - Migration 006 Pendente

## Resumo Técnico

O sistema `controle-ativos` possui uma discrepância entre o schema esperado (código) e o schema atual do banco de dados MySQL.

**Sintoma:** Erro HTTP 500 ao tentar importar ativos (erro SQL: "Unknown column 'codigo_interno' in 'field list'")

**Causa Raiz:** 
- Migration 006 (`database/migrations/006_cadastro_base_e_especificacoes_ativos.sql`) não foi aplicada ao banco
- O usuário operacional `opus_app` não possui permissão `ALTER TABLE` no schema `controle_ativos`
- O código tentava referenciar colunas que não existem na tabela `ativos`

**Status da Correção Temporária:**
- ✅ Código implementado com seleção dinâmica de colunas (columns runtime-detection)
- ✅ Sistema operacional sem erros 500 para schema parcial
- ✅ Seleciona apenas colunas que existem no banco real
- ⏳ Aguardando execução permanente da migration

---

## Solução Permanente (para o DBA/Administrador MySQL)

### Pré-requisitos
- Acesso administrativo ao servidor MySQL
- Permissões para executar `ALTER TABLE` na database `controle_ativos`

### Opção A: Aplicar Migration (Recomendado)

```bash
# Navegar até o diretório do projeto
cd C:\Users\OPUSMANUALSERVER\Documents\sistema\controle-ativos

# Executar migration como usuário administrador (root)
# Substitua os placeholders:
# - DB_HOST: servidor MySQL (ex: 127.0.0.1)
# - DB_PORT: porta (ex: 3306)
# - DB_PASS: senha do root

mysql -h <DB_HOST> -P <DB_PORT> -u root -p<DB_PASS> controle_ativos < database/migrations/006_cadastro_base_e_especificacoes_ativos.sql
```

### Opção B: Executar Migration em Python

```bash
cd C:\Users\OPUSMANUALSERVER\Documents\sistema\controle-ativos

# Criar script seguro (sem expor senha):
python -c "
import mysql.connector
import sys

# Conectar como administrador
config = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': input('MySQL root password: '),
    'database': 'controle_ativos',
    'autocommit': False
}

try:
    conn = mysql.connector.connect(**config)
    cur = conn.cursor()
    
    with open('database/migrations/006_cadastro_base_e_especificacoes_ativos.sql', 'r') as f:
        for stmt in f.read().split(';'):
            if stmt.strip() and not stmt.strip().startswith('--'):
                cur.execute(stmt)
    
    conn.commit()
    print('✓ Migration 006 applied successfully')
    conn.close()
except Exception as e:
    print(f'✗ Error: {e}', file=sys.stderr)
    sys.exit(1)
"
```

### Opção C: Grant Permission + Application Migration

Se a política de segurança permitir que `opus_app` execute migrações (não recomendado para produção):

```sql
-- Conectar como root MySQL
mysql -h 127.0.0.1 -u root -p

-- No cliente MySQL:
USE controle_ativos;

-- Conceder permission temporária para aplicar migration
GRANT ALTER ON controle_ativos.* TO 'opus_app'@'localhost';
FLUSH PRIVILEGES;

-- Aplicar migration
SOURCE database/migrations/006_cadastro_base_e_especificacoes_ativos.sql;

-- Revogar permission após migration (segurança - aplicação não precisa de ALTER)
REVOKE ALTER ON controle_ativos.* FROM 'opus_app'@'localhost';
FLUSH PRIVILEGES;
```

---

## Verificação Após Aplicação

### Verificar se a migration foi aplicada:

```sql
mysql -h 127.0.0.1 -u opus_app -p<opus_app_password> controle_ativos -e \
  "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS \
   WHERE TABLE_NAME='ativos' AND COLUMN_NAME='codigo_interno';"
```

Se retornar `1`, a coluna existe e a migration foi bem-sucedida.

### Verificar lista de novas colunas:

```sql
mysql -h 127.0.0.1 -u opus_app -p<opus_app_password> controle_ativos -e \
  "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS \
   WHERE TABLE_NAME='ativos' \
   ORDER BY ORDINAL_POSITION;"
```

---

## O que a Migration 006 Adiciona

A migration 006 adiciona as seguintes colunas opcionais (NULL) à tabela `ativos`:

| Campo | Tipo | Propósito |
|-------|------|----------|
| `codigo_interno` | VARCHAR(50) | Código interno do ativo pela empresa |
| `serial` | VARCHAR(120) | Número de série do equipamento |
| `descricao` | VARCHAR(255) | Descrição livre do ativo |
| `categoria` | VARCHAR(100) | Categoria do ativo |
| `tipo_ativo` | VARCHAR(50) | Tipo normalizado (ex: "Notebook", "Monitor") |
| `condicao` | VARCHAR(50) | Condição física ("Novo", "Bom", "Regular", "Ruim") |
| `localizacao` | VARCHAR(120) | Localização física dentro da unidade |
| `setor` | VARCHAR(100) | Setor/departamento (alias para compatibilidade) |
| `email_responsavel` | VARCHAR(255) | Email do responsável |
| `data_compra` | DATE | Data da compra |
| `valor` | DECIMAL(12,2) | Valor de compra |
| `observacoes` | TEXT | Observações livres |
| `detalhes_tecnicos` | VARCHAR(255) | Especificações técnicas |
| `processador` | VARCHAR(120) | CPU do equipamento |
| `ram` | VARCHAR(60) | Memória RAM |
| `armazenamento` | VARCHAR(120) | Tipo/tamanho de armazenamento |
| `sistema_operacional` | VARCHAR(120) | SO instalado |
| `carregador` | VARCHAR(120) | Info do carregador/fonte |
| `teamviewer_id` | VARCHAR(100) | ID TeamViewer |
| `anydesk_id` | VARCHAR(100) | ID AnyDesk |
| `nome_equipamento` | VARCHAR(120) | Hostname/nome do computador |
| `hostname` | VARCHAR(120) | Hostname (alias) |
| `imei_1` | VARCHAR(40) | IMEI principal (celulares) |
| `imei_2` | VARCHAR(40) | IMEI secundário (celulares) |
| `numero_linha` | VARCHAR(40) | Número de telefone/linha |
| `operadora` | VARCHAR(80) | Operadora de telefonia |
| `conta_vinculada` | VARCHAR(120) | Conta associada (ex: iCloud, Google) |
| `polegadas` | VARCHAR(30) | Tamanho de tela |
| `resolucao` | VARCHAR(60) | Resolução de tela |
| `tipo_painel` | VARCHAR(60) | Tipo de painel (IPS, TN, etc) |
| `entrada_video` | VARCHAR(120) | Tipos de entrada de vídeo |
| `fonte_ou_cabo` | VARCHAR(120) | Info de fontes/cabos |

---

## Comportamento do Sistema Durante o Schema Parcial

Enquanto a migration 006 não é aplicada, o sistema:

✅ **Funciona corretamente para:**
- Listar ativos (colunas novas retornam como NULL)
- Criar ativos (campos novos ignorados se não existem no banco)
- Importar ativos (apenas campos compatíveis com o banco são importados)
- Dashboard e relatórios (colunas ausentes não quebram as queries)

⚠️ **Com limitações:**
- Campos novos não são persistidos (ex: `codigo_interno`, `valor`, etc)
- Dados importados que contenham campos novos têm esses dados descartados
- Usuário recebe aviso sobre campos ignorados na importação

---

## Segurança e Boas Práticas

1. **Nunca compartilhe credenciais MySQL** em documentação ou logs
2. **Execute migrações em ambiente de testes primeiro** para validar
3. **Sempre faça backup antes de aplicar migrações** que modificam schema
4. **O usuário `opus_app` não deve ter permissão ALTER TABLE permanentemente** (apenas aplicação de operações SELECT/INSERT/UPDATE)
5. **Monitore os logs de aplicação** após aplicar migration para confirmar que novos campos estão sendo usados

---

## Contato e Suporte

Caso a migration falhe ou gere erros:

1. Verifique se o arquivo `database/migrations/006_cadastro_base_e_especificacoes_ativos.sql` existe
2. Confirme que você está conectado ao servidor MySQL correto
3. Verifique permissões do usuário root no MySQL
4. Consulte os logs de erro do MySQL para detalhes

---

**Última atualização:** 2026-04-29  
**Versão:** 1.0  
**Status:** Documentação operacional - Migration 006 ainda não aplicada
