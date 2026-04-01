# 🔄 Guia de Migração: Coluna "seguro" → "garantia"

## 📋 Situação Atual

| Item | Status |
|------|--------|
| **Código Python/Flask** | ✅ Refatorado para usar `garantia` |
| **Banco MySQL** | ⚠️ Ainda usa coluna `seguro` |
| **Sincronização** | ❌ DESSINCRONIZADA |
| **Registros existentes** | 8 ativos no banco |

---

## 🚀 Processo de Migração

4 scripts Python foram criados para automatizar o processo de forma **segura e validada**.

### **PASSO 1: Fazer Backup**

```bash
python STEP_1_BACKUP.py
```

**O que faz:**
- Conecta ao banco MySQL
- Lê todos os registros da tabela `ativos`
- Salva em arquivo CSV com timestamp (ex: `BACKUP_ativos_20260401_143022.csv`)
- Resultado: Um arquivo CSV no diretório raiz

**Saída esperada:**
```
✓ Backup criado: BACKUP_ativos_20260401_143022.csv
✓ Total de registros salvos: 8
```

---

### **PASSO 2: Executar Migração SQL**

```bash
python STEP_2_MIGRATION.py
```

**O que faz:**
- Conecta ao banco MySQL
- **PEDE CONFIRMAÇÃO** antes de executar (responda `S` ou `Enter`)
- Executa: `ALTER TABLE ativos CHANGE COLUMN seguro garantia VARCHAR(100) NULL;`
- Faz commit da transação

**Saída esperada:**
```
⚠️  AVISO: Você está prestes a executar a MIGRAÇÃO no banco de dados
...
Backup foi feito? [S/n]: S

✓ Migração executada com sucesso!
✓ Coluna 'seguro' foi renomeada para 'garantia'
```

---

### **PASSO 3: Validar Migração**

```bash
python STEP_3_VALIDATE.py
```

**O que faz:**
- Verifica se a coluna `garantia` existe e `seguro` foi removida
- Confirma que todos os 8 registros foram preservados
- Testa SELECT com coluna `garantia`
- Testa queries UPDATE (simulado)
- Verifica índices

**Saída esperada:**
```
✓ VALIDACAO CONCLUIDA COM SUCESSO!

Resumo:
  • Schema: Sincronizado ✓
  • Dados: 8 registros preservados ✓
  • Compatibilidade Python: Testada ✓
  • Próximo passo: Testar aplicação Flask
```

---

### **PASSO 4: Teste Funcional Completo**

```bash
python STEP_4_FUNCTIONAL_TEST.py
```

**O que faz:**
- Testa conectividade ao banco
- Verifica se o modelo `Ativo` funciona com campo `garantia`
- Testa validadores (regra "nota_fiscal OU garantia")
- Verifica schema é compatível
- Confirma que o `AtivosService` está pronto

**Saída esperada:**
```
✓ TESTE FUNCIONAL PASSOU!

Resumo:
  • Banco MySQL: Acessível ✓
  • Modelo Ativo: Campo 'garantia' funciona ✓
  • Validators: Aceitam 'garantia' ✓
  • Schema: Sincronizado ✓
  • Service: Pronto para uso ✓
```

---

## 🔧 Como Executar TUDO Junto

Se quiser executar os 4 passos em sequência sem quebra:

```bash
# Entrar no ambiente virtual (se não estiver)
. .venv\Scripts\activate.ps1

# Executar os 4 testes
python STEP_1_BACKUP.py && python STEP_2_MIGRATION.py && python STEP_3_VALIDATE.py && python STEP_4_FUNCTIONAL_TEST.py
```

---

## ⚠️ O Que Cada Script Faz em Detalhes

### **STEP_1_BACKUP.py**

| Operação | Tipo | Risco |
|----------|------|-------|
| Ler dados da tabela | SELECT | ✅ Sem risco |
| Salvar em CSV | Arquivo local | ✅ Sem risco |
| Modificar banco | ❌ Não | ✅ Seguro |

**Arquivo de saída:** `BACKUP_ativos_YYYYMMDD_HHMMSS.csv`

**Quando usar:** ANTES de qualquer migração

---

### **STEP_2_MIGRATION.py**

| Operação | Tipo | Risco |
|----------|------|-------|
| Renomear coluna | ALTER TABLE | ⚠️ **Destrutivo** |
| Pedir confirmação | Input | ✅ Proteção |
| Fazer commit | Transação | ❌ Sem rollback automático |

**SQL executado:**
```sql
ALTER TABLE ativos CHANGE COLUMN seguro garantia VARCHAR(100) NULL;
```

**Proteções:**
- ✅ Pede confirmação de usuário
- ✅ Aviso em maiúsculas
- ✅ Resgata se houver erro

**Quando usar:** APÓS BACKUP ter sucesso

---

### **STEP_3_VALIDATE.py**

| Verificação | Tipo | O que Testa |
|---|---|---|
| Schema | DESCRIBE | Se `garantia` existe, `seguro` removida |
| Dados | SELECT COUNT | Se 8 registros foram preservados |
| Compatibilidade | SELECT com garantia | Se Python consegue ler a coluna |
| Índices | SHOW INDEX | Se há índices na coluna |

**Quando usar:** APÓS migração completar

---

### **STEP_4_FUNCTIONAL_TEST.py**

| Teste | O que Valida |
|---|---|
| Conectividade | Banco trabalha com código |
| Modelo Ativo | Campo `garantia` em to_dict() |
| Validators | Regra "nota_fiscal OR garantia" |
| Schema | `garantia` existente |
| Service | AtivosService instancia |

**Quando usar:** DEPOIS de STEP 3 passar

---

## 🔄 Rollback (Desfazer Migração)

Se algo der errado, use o backup:

```sql
-- Conectar ao MySQL
mysql -u root -p controle_ativos

-- Renomear de volta
ALTER TABLE ativos CHANGE COLUMN garantia seguro VARCHAR(100) NULL;

-- Pronto! Voltou ao estado anterior
```

Ou, restaurar código Python para versão anterior:
```bash
git checkout HEAD -- models/ services/ web_app/ utils/
```

---

## 📊 Checklist de Execução

```
ANTES DE INICIAR:
  [ ] Ambiente virtual ativado:  . .venv\Scripts\activate.ps1
  [ ] Banco MySQL rodando:       sudo systemctl status mysql
  [ ] .env com credenciais OK

EXECUTAR NESTA ORDEM:
  [ ] python STEP_1_BACKUP.py          (ARQUIVO de backup criado)
  [ ] python STEP_2_MIGRATION.py       (responda S na confirmação)
  [ ] python STEP_3_VALIDATE.py        (tudo passa)
  [ ] python STEP_4_FUNCTIONAL_TEST.py (tudo passa)

APÓS SUCESSO:
  [ ] Deletar scripts temporários: rm STEP_*.py DIAGNOSE_SCHEMA.py
  [ ] Testar Flask: python main.py (ou seu script de run)
  [ ] Testar web: Abrir http://localhost:5000
  [ ] Testar cadastro: Criar novo ativo
  [ ] Testar listagem: Ver ativos cadastrados
  [ ] Testar filtro: Filtrar por garantia
```

---

## 🐛 Troubleshooting

### **Erro: "Unknown column 'garantia'"**
- Significa STEP_2 não foi executado
- Execute: `python STEP_2_MIGRATION.py`

### **Erro: "1054 (42S22): Unknown column 'seguro'"**
- Significa coluna foi excluída mas código não foi atualizado
- Seu código Python pode estar na versão antiga
- Faça: `git pull` ou atualize os arquivos

### **Erro de permissão MySQL**
- Verifique .env:
  - DB_USER: root (ou seu usuário)
  - DB_PASSWORD: correto
  - DB_PORT: 3306 (padrão)

### **Erro: "Connection refused"**
- MySQL não está rodando
- Windows: Abra Services e inicie "MySQL"
- Linux: `sudo systemctl start mysql`

---

## 📝 Logs e Evidências

Todos os scripts geram saída clara:

- **STEP_1**: Cria arquivo `BACKUP_ativos_YYYYMMDD_HHMMSS.csv`
- **STEP_2**: Printa SQL executado e resultado
- **STEP_3**: Printa todas as validações com ✓ ou ❌
- **STEP_4**: Printa testes funcionais com ✓ ou ❌

**Para guardar log completo:**
```bash
python STEP_3_VALIDATE.py > VALIDATION_LOG.txt 2>&1
```

---

## ✅ Conclusão

Após os 4 passos completarem com sucesso:

1. ✅ Banco MySQL = coluna `garantia` (renomeada de `seguro`)
2. ✅ Código Python = usa `ativo.garantia`
3. ✅ Dados = 8 registros preservados  
4. ✅ Flask/Web = funciona normalmente
5. ✅ CLI = lista com "Garantia" em vez de "Seguro"

**Você pode deletar estes scripts após o sucesso:**
```bash
rm STEP_1_BACKUP.py STEP_2_MIGRATION.py STEP_3_VALIDATE.py STEP_4_FUNCTIONAL_TEST.py DIAGNOSE_SCHEMA.py
```

---

**Documento preparado:** 01/04/2026  
**Status:** Pronto para execução  
**Confirmação necessária:** Antes de STEP_2 (migração)
