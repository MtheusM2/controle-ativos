# DIAGNÓSTICO DA REGRESSÃO — Central de Importação

## Data: 2026-04-24
## Status: CAUSA RAIZ IDENTIFICADA

---

## Resumo da Regressão

A interface de importação **regrediu para um estado simplificado**, mostrando apenas a seção de upload sem a central de revisão (mapeamento, revisão por linha, edição, descarte).

## Causa Raiz Identificada

### 1. Contrato Quebrado entre Rota e JavaScript

**Arquivo:** `web_app/routes/ativos_routes.py` — linhas 1895-1902

```python
# A rota retorna HTTP 400 quando há bloqueios
bloqueios = preview.get('indicador_risco', {}).get('bloqueios', [])
if bloqueios:
    return _json_error(
        "Importação bloqueada por requisitos críticos.",
        status=400,
        preview=preview,
        id_lote=id_lote
    )
```

**Arquivo:** `web_app/templates/importar_ativos.html` — linhas 1280-1282

```javascript
// O JS rejeita HTTP 400 e NÃO renderiza
const payload = await response.json();
if (!response.ok || !payload.ok) {
    throw new Error(payload.erro || "Falha ao gerar pré-visualização.");
}
// Nunca chega aqui quando status 400
```

### 2. Impacto

Quando o CSV gera **QUALQUER bloqueio crítico** (campo obrigatório faltando, taxa erro > 50%, etc.):
- Rota retorna **HTTP 400** ✗
- JS intercepta e lança exceção ✗
- Preview NÃO é renderizada ✗
- Usuário vê apenas mensagem de erro ✗
- A central de revisão completa nunca aparece ✗

### 3. Dados que Existem mas Não Aparecem

No objeto `preview_enriquecido` da rota (importacao_service_seguranca.py, linha 254):

```
✓ linhas_revisao (todas as linhas para edição/descarte)
✓ erros_por_linha (erros reais estruturados)
✓ avisos_por_linha (avisos reais estruturados)
✓ campos_destino_disponiveis (lista de campos)
✓ indicador_risco (status, cor, bloqueios, alertas)
✓ validacao_detalhes (contadores de validação)
```

Todos esses dados **EXISTEM** no JSON de resposta (status 400), mas o JS **NÃO OS PROCESSA** porque rejeita a requisição por status != 200.

---

## Fluxo Quebrado (Agora)

```
1. Usuário seleciona CSV
2. JS POST → /ativos/importar/preview
3. Rota processa, gera preview COMPLETO
4. Rota detecta bloqueios
5. Rota retorna HTTP 400 + preview_enriquecido
6. JS vê status 400 → throw Error
7. Catch mostra mensagem de erro
8. FIM — preview nunca renderiza
```

---

## Fluxo Esperado (Design Original)

```
1. Usuário seleciona CSV
2. JS POST → /ativos/importar/preview
3. Rota processa, gera preview COMPLETO
4. Rota detecta bloqueios
5. Rota retorna HTTP 200 + preview_enriquecido + indicador_risco.bloqueios
6. JS renderiza preview SEMPRE (bloqueios visíveis na UI)
7. Se bloqueios críticos: renderiza aviso visual, desabilita botão de confirmação
8. Usuário vê a central de revisão mesmo com bloqueios
9. Usuário pode editar/descartar linhas mesmo para corrigir bloqueios
10. Confirmação respeita modo_importacao
```

---

## Arquivos Afetados

| Arquivo | Linha(s) | Problema |
|---------|----------|----------|
| `web_app/routes/ativos_routes.py` | 1895-1902 | Retorna 400 quando há bloqueios |
| `web_app/templates/importar_ativos.html` | 1280-1282 | Rejeita requisições com status != 200 |
| **Nenhum teste de regressão** | — | JS nunca testado com bloqueios visíveis |

---

## Correccões Necessárias

### 1. Rota: Retornar 200 + Bloqueios no Payload (NÃO 400)

Mudança em `ativos_routes.py`:
- Remover retorno 400 quando há bloqueios
- Retornar 200 **sempre** quando preview é gerado
- Passar bloqueios como parte do `indicador_risco` no JSON

### 2. JavaScript: Renderizar Preview Mesmo Com Bloqueios

Mudança em template JS:
- Aceitar responses com status 200
- Renderizar preview **independente** de bloqueios
- Mostrar indicador visual de bloqueios
- Desabilitar botão de confirmação se `indicador_risco.bloqueios` não vazio

### 3. Testes: Validar Regressão

Criar testes para:
- Preview renderiza mesmo com bloqueios
- Indicador de risco aparece quando há bloqueios
- Botão de confirmação desabilita quando há bloqueios críticos

---

## Componentes do Working Tree

**Templates com funcionalidade nova (existem, mas não renderizam):**
- Bloco A — Mapeamento de Colunas
- Bloco B — Revisão por Linha (com edição, descarte, inferência)
- Bloco C — Opções de Importação (modo, checkboxes)
- Bloco D — Confirmação Final

**Dados completos no serviço (existem, mas não lidos pelo JS):**
- `linhas_revisao` — grade de revisão com status/erros/avisos
- `erros_por_linha` — estrutura real de erros
- `avisos_por_linha` — estrutura real de avisos
- `campos_destino_disponiveis` — dropdown fields para modal de edição

---

## Próximos Passos

1. ✓ Auditoria completa (FEITA)
2. → Backup do estado atual (FEITO)
3. → Corrigir rota para retornar 200 sempre
4. → Corrigir JS para aceitar/renderizar preview mesmo com bloqueios
5. → Atualizar indicador visual (bloqueios em destaque)
6. → Criar testes de regressão
7. → Validar fluxo completo
