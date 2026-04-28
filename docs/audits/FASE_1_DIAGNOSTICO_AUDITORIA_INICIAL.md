# FASE 1 — Diagnóstico Consolidado da Auditoria Inicial

**Data:** 2026-04-27  
**Status:** Auditoria completa concluída  
**Objetivo:** Preservação e análise do estado atual antes de qualquer alteração  

---

## 1. ESTADO DO WORKING TREE

### Arquivos Modificados (13 arquivos)
```
M services/ativos_service.py
M services/importacao_service_seguranca.py
M tests/conftest.py
M tests/test_app.py
M tests/test_auditoria_importacao.py
M tests/test_import_validators.py
M tests/test_importacao_fluxo_confirmacao.py
M tests/test_importacao_massa.py
M tests/test_integracao_rotas_importacao.py
M utils/import_validators.py
M web_app/routes/ativos_routes.py
M web_app/static/css/style.css
M web_app/templates/importar_ativos.html
```

### Arquivos Novos (7 arquivos)
```
?? DIAGNOSE_REGRESSAO.md
?? RELATORIO_FIX_REGRESSAO_IMPORTACAO.md
?? RESUMO_PARTE_2_TESTES.md
?? backup-importacao-auditoria.patch
?? tests/test_email_inference.py
?? tests/test_importacao_revisao_central.py
?? utils/email_inference.py
?? utils/import_types.py
```

### Branch e Commit Recente
- **Branch:** auditoria-importacao-fix
- **Último commit:** b6965ac - "fix: resolver bloqueio de importação — campo 'id' opcional e alinhamento mapper/validator"
- **Base para PR:** main

---

## 2. ARQUITETURA DA IMPORTAÇÃO EM MASSA

### Fluxo Atual (Camadas)

#### Camada 1: Entrada (Web)
- **Rota:** `/ativos/importar/preview` (POST)
- **Arquivo:** `web_app/routes/ativos_routes.py:1846`
- **Responsabilidade:** Ler CSV, chamar serviço, retornar preview
- **Status:** OK, com comentários de código

#### Camada 2: Serviço de Importação com Segurança
- **Classe:** `ServicoImportacaoComSeguranca` 
- **Arquivo:** `services/importacao_service_seguranca.py`
- **Responsabilidade:**
  - Processar arquivo CSV (delimitador, detecção cabeçalho)
  - Fazer mapeamento de colunas
  - Validar linhas contra regras
  - Gerar preview com bloqueios/avisos
  - Registrar auditoria
- **Status:** OK, contém mapeamento de campos e validação

#### Camada 3: Validadores
- **Arquivo:** `utils/import_validators.py`
- **Principais classes:**
  - `ValidadorCampos` — validação de tipo, formato, enum
  - `ValidadorLinha` — validação de linha completa
  - `ValidadorLote` — validação de lote, bloqueios, alertas
- **Status:** OK, mas com **PROBLEMAS IDENTIFICADOS** (ver seção 3)

#### Camada 4: Mapeamento de Campos
- **Arquivo:** `utils/import_mapper.py` (não listado, mas referenciado)
- **Responsabilidade:** Mapear colunas CSV para campos de banco
- **Status:** Contrato esperado: `ResultadoMatch` com `coluna_origem`, `campo_destino`, `score`

#### Camada 5: Inferência por Email
- **Arquivo:** `utils/email_inference.py`
- **Responsabilidade:** Inferir setor e localização baseado em email
- **Status:** OK, com priorização correta

### Fluxo de Confirmação
- **Rota:** `/ativos/importar/confirmar` (POST)
- **Arquivo:** `web_app/routes/ativos_routes.py:1913`
- **Entrada:** id_lote, modo_importacao, mapeamento_confirmado, linhas_descartadas, edições
- **Status:** Implementado, mas **DEPENDE DEMAIS DO FRONTEND** (ver seção 3)

---

## 3. PROBLEMAS IDENTIFICADOS (Causa Raiz)

### Problema 1: Divergência de Nomes Canônicos
**Localização:** Múltiplos arquivos  
**Impacto:** CRÍTICO

#### 1a. `setor` vs `departamento`
- **import_validators.py:40-44:** Define ALIASES_CAMPOS_IMPORTACAO com `'departamento': 'setor'`
- **email_inference.py:248-310:** Mantém sincronismo manual entre `setor` e `departamento`
- **validators.py:40-55:** Define SETORES_VALIDOS como fonte única
- **Problema:** Campos competem, gerando silêncios e sobrescrita

#### 1b. `localizacao` vs `unidade` vs `base`
- **import_validators.py:42:** Define aliases `'unidade': 'localizacao'` e `'base': 'localizacao'`
- **validators.py:66-69:** Define UNIDADES_VALIDAS como `["Opus Medical", "Vicente Martins"]`
- **email_inference.py:133-178:** Infere `localizacao` baseado em email
- **Problema:** Sem normalização no mapeamento CSV

#### 1c. `tipo` vs `tipo_ativo`
- **import_validators.py:43:** Define alias `'tipo': 'tipo_ativo'`
- **validators.py:22-34:** Define TIPOS_ATIVO_VALIDOS como fonte
- **Problema:** Frontend pode enviar `tipo` ou `tipo_ativo` sem controle centralizado

### Problema 2: Validação Dividida entre Prévia e Confirmação
**Localização:** importacao_service_seguranca.py, rotas, validadores  
**Impacto:** CRÍTICO

#### 2a. Prévia Valida com Regras X
- **ImportacaoServiceComSeguranca.gerar_preview_seguro():**
  - Chama `ValidadorLote.validar_lote()`
  - Usa CAMPOS_BLOQUEANTES e CAMPOS_RECOMENDAVEIS
  - Detecta duplicatas por ID e serial
  - Valida tipos, datas, emails

#### 2b. Confirmação Valida com Regras Y (FREQUENTEMENTE DIFERENTES)
- **importar_ativos_confirmar():**
  - Recebe modo_importacao, linhas_descartadas, edições
  - **NÃO revalida contra as mesmas regras da prévia**
  - Depende do frontend para decidir o que aceitar

#### 2c. Resultado
- **Cenário:** Prévia aprova linha com setor="TI" (válido)
- **Cenário:** Confirmação rejeita porque frontend mandou setor="" (inválido)
- **Raiz:** Validação não é compartilhada; cada camada usa lógica parcial

### Problema 3: Modo de Importação Decidido no Frontend
**Localização:** web_app/routes/ativos_routes.py:1932-1942  
**Impacto:** ALTO

```python
modo_importacao = request.form.get('modo_importacao', 'validas_e_avisos').strip()
if modo_importacao not in {"validas_apenas", "validas_e_avisos", "tudo_ou_nada"}:
    modo_importacao = "validas_e_avisos"
modo_tudo_ou_nada = modo_importacao == 'tudo_ou_nada'
```

**Problema:**
- Frontend controla qual linhas são importadas
- Backend aceita qualquer modo sem recalcular
- Se confirmação falha, modo_importacao fica inconsistente com lote revisado
- Modo `tudo_ou_nada` não considera linhas descartadas

### Problema 4: Lote Revisado Não é Fonte Única de Verdade
**Localização:** importacao_service_seguranca.py, confirmação  
**Impacto:** ALTO

#### 4a. Que dados são usados na confirmação?
1. **id_lote** — referência ao lote original
2. **modo_importacao** — escolha do usuário
3. **linhas_descartadas** — quais linhas pular
4. **edicoes_por_linha** — edições manuais (JSON)
5. **mapeamento_confirmado** — mapeamento de colunas revisado
6. **sugestoes_confirmadas** — inferências aceitas

#### 4b. Que dados NÃO são usados?
- **Dados validados da prévia** — não enviados novamente
- **Snapshot de linhas mapeadas** — não resgatáveis
- **Resultado de validação anterior** — não reutilizado

#### 4c. Problema
- Se confirmação recalcular validação, usará dados brutos diferentes
- Se não recalcular, pode importar dados inválidos
- Não há mecanismo de "lote confirmado" que persista o estado

### Problema 5: Inferência por Email Pode Sobrescrever Valores Válidos
**Localização:** email_inference.py:230-312  
**Impacto:** MÉDIO

**Contrato Atual:**
```python
Ordem de prioridade:
1. valor explicito valido vindo da planilha
2. valor corrigido manualmente no modal
3. valor inferido automaticamente por e-mail
4. sugestao pendente de confirmacao
5. permanece ausente quando nao ha confianca suficiente
```

**Problema Encontrado:**
- `aplicar_inferencia_email_em_dados()` não valida se o valor existente é realmente válido
- Usa `_valor_setor_valido()` e `_valor_localizacao_valido()`, que dependem de SETORES_VALIDOS e UNIDADES_VALIDAS
- Se SETORES_VALIDOS muda, comportamento muda silenciosamente

---

## 4. CAMPOS CANÔNICOS ATUAIS

### Definidos em import_validators.py
```python
CAMPOS_CANONICOS_IMPORTACAO = {
    'tipo_ativo',
    'marca',
    'modelo',
    'setor',
    'localizacao',
    'status',
    'data_entrada',
    'email_responsavel',
}
```

### Aliases Aceitos
```python
ALIASES_CAMPOS_IMPORTACAO = {
    'departamento': 'setor',
    'unidade': 'localizacao',
    'base': 'localizacao',
    'tipo': 'tipo_ativo',
}
```

### Classificação de Criticidade
```python
CAMPOS_BLOQUEANTES = {'tipo_ativo', 'marca', 'modelo'}        # Erro se vazios
CAMPOS_RECOMENDAVEIS = {'setor', 'status', 'data_entrada'}   # Aviso se vazios
```

---

## 5. TESTES ATUAIS

### Arquivos de Teste Existentes
1. **tests/test_import_validators.py** — Testa ValidadorCampos, ValidadorLinha, ValidadorLote
2. **tests/test_importacao_fluxo_confirmacao.py** — Testa preview e confirmação
3. **tests/test_importacao_massa.py** — Testa importação em lote
4. **tests/test_integracao_rotas_importacao.py** — Testa rotas Web
5. **tests/test_auditoria_importacao.py** — Testa auditoria
6. **tests/test_email_inference.py** (novo) — Testa inferência por email
7. **tests/test_importacao_revisao_central.py** (novo) — Testa central de revisão

### Status dos Testes
- **Cobertura:** Boa (validação, rotas, auditoria)
- **Lacuna:** Falta teste de **convergência entre prévia e confirmação**
- **Lacuna:** Falta teste de **regressão do bug principal**

---

## 6. ARQUIVOS PRIORITÁRIOS DESTA FASE

Conforme solicitado:

| Arquivo | Responsabilidade | Status |
|---------|------------------|--------|
| `services/ativos_service.py` | CRUD de ativos | Será afetado |
| `services/importacao_service_seguranca.py` | Validação + preview | **CRÍTICO** |
| `utils/import_validators.py` | Validadores | **CRÍTICO** |
| `utils/validators.py` | Domínio (STATUS, SETORES, TIPOS) | **CRÍTICO** |
| `utils/email_inference.py` | Inferência | Será ajustado |
| `web_app/routes/ativos_routes.py` | Rotas web | Será ajustado |

**NÃO TOCAR NESTA FASE:**
- Templates HTML/Jinja2 (exceto se necessário para contrato de payload)
- CSS/JS (exceto se necessário para contrato)
- Banco de dados (schema não muda)
- Migrações (não necessárias)

---

## 7. ORDEM DE CONSOLIDAÇÃO RECOMENDADA

Para reduzir risco de regressão:

1. **Definir nomes canônicos únicos** (PARTE 3)
   - Escolher definitivamente: setor, localizacao, tipo_ativo
   - Documentar aliases de entrada

2. **Unificar validação** (PARTE 2)
   - Criar `ValidadorImportacaoCanônico` que todos usam
   - Prévia chama mesma validação da confirmação

3. **Backend como autoridade de modo** (PARTE 4)
   - Backend recalcula modo baseado em lote revisado
   - Frontend envia intenção, não decisão

4. **Lote revisado como fonte de verdade** (PARTE 5)
   - Persistir snapshot de linhas validadas
   - Confirmação usa snapshot, não recomputa

5. **Consolidar inferência** (PARTE 6)
   - Inferência não sobrescreve valor válido
   - Respeita prioridade clara

6. **Testes abrangentes** (PARTE 7)
   - Cobertura de regressão
   - Convergência prévia/confirmação

---

## 8. CHECKLIST DE PRESERVAÇÃO

✅ Working tree mapeado  
✅ Arquivos críticos identificados  
✅ Problemas documentados com localização exata  
✅ Contrato de dados entendido  
✅ Fluxo ponta-a-ponta mapeado  
✅ Testes atuais identificados  
✅ Causa raiz documentada  
❌ **NENHUMA ALTERAÇÃO FEITA** (preservação completa)

---

## 9. PRÓXIMOS PASSOS (Esperado)

1. Usar este diagnóstico para planejar PARTE 2 (Contrato Único)
2. Criar consolidação progressiva sem quebrar
3. Adicionar testes de regressão antes de cada mudança
4. Validar convergência prévia/confirmação

---

## 10. SUMÁRIO EXECUTIVO

**Situação:** Sistema de importação está 80% pronto, mas com divergências críticas entre camadas.

**Causa Raiz:**
- Validação espalhada em múltiplos lugares
- Nomes de campos competem (setor/departamento, localizacao/unidade/base, tipo/tipo_ativo)
- Frontend controla decisões que devem ser do backend
- Lote revisado não persiste como fonte de verdade

**Risco:** Prévia aprova e confirmação rejeita (ou vice-versa).

**Solução:** Consolidação arquitetural em 6 fases estruturadas, sem quebrar funcionalidade.

**Escopo:** 6 arquivos críticos, 0 arquivos de infra/BD, ~500 linhas de código alterado.

