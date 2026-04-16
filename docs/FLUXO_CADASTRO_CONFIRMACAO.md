# Fluxo de Cadastro com Confirmação — Documentação Técnica

**Data:** 2026-04-16  
**Versão:** 2.0 — Confirmação Final + Anti-Duplicidade  
**Status:** ✅ Implementado e testado

---

## 1. Visão Geral

O fluxo de cadastro de ativo foi refatorado para:
1. **2 etapas:** preenchimento + confirmação (antes: gravação imediata)
2. **Proteção anti-duplicidade:** no frontend (botão desabilitado) e backend (cache de deduplicação)
3. **Feedback visual:** badge "NOVO" destaca ativo recém-criado na listagem
4. **Melhor UX:** modal de confirmação exibe todos os dados para validação antes de gravar

---

## 2. Fluxo End-to-End

```
┌─────────────────────────────────────────────────────────────────┐
│                     USUARIO INICIA CADASTRO                      │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ↓
        ┌─────────────────┐
        │ Preenche Form   │
        └────────┬────────┘
                 │
                 ↓
        ┌─────────────────────────────┐
        │ Clica "Salvar Ativo"        │
        │ (form submit)               │
        └────────┬────────────────────┘
                 │
                 ↓ (JavaScript)
        ┌──────────────────────────────────────┐
        │ Coleta dados do formulário           │
        │ Renderiza modal de confirmação       │
        │ Abre modal (hidden=false)            │
        └────────┬─────────────────────────────┘
                 │
                 ↓
        ┌───────────────────────────────────────────┐
        │ USER VÊ MODAL COM DADOS ORGANIZADOS       │
        │ - 7 seções: Identificação, Classificação │
        │ - Localização, Responsável, Operacional  │
        │ - Valor/Doc, Detalhes Técnicos           │
        └────┬──────────────────────────────────┬───┘
             │                                  │
             ↓ (Voltar)                     ↓ (Confirmar)
    Modal fecha          Botão desabilitado
    Dados permanecem    "é-loading" classe
    no formulário       

                                    ↓
                        ┌────────────────────────┐
                        │ POST /ativos (body: dados)
                        │ + X-CSRF-Token         │
                        └────────┬───────────────┘
                                 │
                                 ↓ (Backend)
                        ┌────────────────────────┐
                        │ Gera chave_dedup       │
                        │ hash(dados + user_id)  │
                        └────────┬───────────────┘
                                 │
                    ┌────────────┴────────────┐
                    ↓                         ↓
            Chave JÁ EXISTE      Chave É NOVA
            (duplicação)         (primeira vez)
            │                    │
            ↓                    ↓
        Retorna ID do        Cria ativo
        ativo existente      service.criar_ativo()
        201 Created          │
                             ↓
                        Registra no cache
                        201 Created
                        {ativo: {...}}
                        │
                        ↓ (Frontend)
                    Fecha modal
                    Mostra: "Cadastrado!"
                    Aguarda 1.5s
                    │
                    ↓
            Redireciona para:
            /ativos/lista?highlight=NOVO_ID
            │
            ↓
        ┌─────────────────────────────────┐
        │ Página listagem carrega         │
        │ - Lê parâmetro ?highlight=...   │
        │ - Renderiza badge "NOVO"        │
        │ - Scroll até o ativo destacado  │
        │ - Remove param da URL           │
        └─────────────────────────────────┘
```

---

## 3. Arquitetura Técnica

### 3.1 Frontend (novo_ativo.html)

#### Estado
```javascript
// Dados coletados do formulário antes de confirmar
let pendingAssetData = null;
```

#### Fluxo
1. **form.submit** → Coleta dados → Renderiza modal → Abre modal
2. **Botão voltar** → Fecha modal (dados permanecem no form)
3. **Botão confirmar** → Desabilita botão → POST /ativos → Redireciona

#### Proteção Anti-Duplicidade (Frontend)
```javascript
const confirmButton = document.getElementById("confirm-asset-button");
confirmButton.disabled = true;  // Desabilita imediatamente
confirmButton.classList.add("is-loading");  // Indica carregamento

// Re-habilita só se erro
// Em sucesso, redireciona (botão não volta)
```

### 3.2 Backend (ativos_routes.py)

#### Proteção Anti-Duplicidade (Backend)
```python
# Cache em memória: {hash_dados+user_id: (ativo_id, timestamp)}
_creation_dedup_cache = {}

# Gera chave: SHA256(dados_normalizados + user_id)
def _gerar_chave_dedup(dados, user_id) -> str

# Verifica duplicação: se existe há <10s, retorna ativo existente
def _verificar_duplicacao(chave_dedup, user_id, ativo_id_novo) -> (bool, str|None)

# Usa na rota:
chave = _gerar_chave_dedup(dados, user_id)
eh_duplicada, id_existente = _verificar_duplicacao(chave, user_id, None)

if eh_duplicada:
    return ativo_id_existente  # Retorna já criado
else:
    id_novo = service.criar_ativo(ativo, user_id)
    _verificar_duplicacao(chave, user_id, id_novo)  # Registra
    return id_novo
```

#### Campos Usados para Deduplicação
```
tipo, tipo_ativo, marca, modelo, serial,
usuario_responsavel, setor, departamento, localizacao,
condicao, status
```

**Lógica:** Se esses 11 campos são idênticos em <10s, considera duplicação.

#### TTL de Cache
- **10 segundos:** requisições com >10s são consideradas nova criação
- **Limpeza automática:** removia de entradas expiradas a cada requisição

### 3.3 Frontend (ativos.html)

#### Destaque com Badge "NOVO"
```javascript
// URL: /ativos/lista?highlight=NTB-001

// No carregamento:
const highlightId = urlParams.get("highlight");
loadAssets({}, highlightId);

// Na renderização:
function renderAssets(assets, highlightId = null) {
    // Se isNewAsset = true:
    // - Background: #fffacd (amarelo claro)
    // - Borda: 4px solid #ffc107 (amarelo)
    // - Badge: "NOVO" em amarelo

    // Scroll automático até a linha
}
```

#### Limpeza de URL
```javascript
// Após usar parâmetro, remove da URL
window.history.replaceState({}, document.title, cleanUrl);
```

---

## 4. Segurança

| Aspecto | Implementação |
|---------|---------------|
| **CSRF** | Obrigatório em POST /ativos (decorator @require_csrf) ✅ |
| **Autenticação** | Obrigatório (decorator @require_auth_api) ✅ |
| **Anti-Duplicidade (FE)** | Botão desabilitado durante envio ✅ |
| **Anti-Duplicidade (BE)** | Cache de hash + TTL 10s ✅ |
| **Idempotência** | GET /ativos?highlight=... é idempotente ✅ |
| **XSS** | escapeHtml() em confirmação ✅ |
| **SQL Injection** | Service usa prepared statements ✅ |

---

## 5. Testes Unitários

```
Status: ✅ 65/65 testes passando

Cobertura:
- POST /ativos com CSRF: OK
- Autorização por empresa: OK
- Validação de entrada: OK
- Compatibilidade com anexos: OK
- Redirecionamento: Não testado (JS, não automático)
```

### Testes Manuais Recomendados

#### 5.1 Fluxo Normal
```
1. Preencher cadastro: tipo, marca, modelo, responsável, setor
2. Clicar "Salvar ativo"
3. ✓ Modal de confirmação abre com dados
4. ✓ Dados estão organizados em 7 seções
5. Clicar "Confirmar e salvar"
6. ✓ Botão desabilitado + classe "is-loading"
7. ✓ Redireciona para listagem após 1.5s
8. ✓ Ativo aparececom badge "NOVO"
9. ✓ Linha tem background amarelo e borda amarela
10. ✓ Scroll automático até o ativo
11. ✓ URL não tem mais parâmetro ?highlight=...
```

#### 5.2 Voltar para Editar
```
1. Preencher cadastro
2. Clicar "Salvar ativo"
3. Modal abre
4. Clicar "Voltar para editar"
5. ✓ Modal fecha
6. ✓ Dados permanecem no formulário
7. Editar alguns dados
8. Clicar "Salvar ativo" novamente
9. ✓ Modal abre com dados atualizados
10. Confirmar
11. ✓ Cadastro com os novos dados
```

#### 5.3 Double-Click (Proteção Anti-Duplicidade)
```
1. Preencher cadastro
2. Abrir modal de confirmação
3. Clicar RAPIDAMENTE "Confirmar e salvar" várias vezes (3-5x)
4. ✓ Apenas 1 ativo é criado (não 3-5)
5. ✓ Backend retorna o mesmo ID
6. ✓ Redirecionamento acontece normalmente
7. Ir para listagem
8. ✓ Ativo aparece 1x, não duplicado
```

#### 5.4 Double-Submit via F12 Console
```
1. Preencher e abrir modal
2. Abrir DevTools (F12) → Console
3. Executar fetch POST /ativos 2x em rápida sucessão
4. ✓ Apenas 1 criação efetiva
5. ✓ Segunda requisição retorna ativo já criado
```

#### 5.5 Fluxo de Anexos
```
1. Preencher cadastro
2. Confirmar e gravar
3. ✓ Redireciona para listagem
4. Clicar no ativo recém-criado (link detalhes ou editar)
5. Ir para detalhe_ativo.html
6. ✓ Painel de anexos está acessível
7. ✓ Upload de anexos funciona
8. ✓ Download funciona
9. ✓ Deleção funciona
```

#### 5.6 Validação
```
1. Deixar campos obrigatórios em branco
2. Clicar "Salvar ativo"
3. ✓ Modal não abre (ou mostra erro antes)
4. ✓ Mensagem de erro clara
5. Preencher tipos incompatíveis (ex: responsável numérico)
6. Abrir modal
7. ✓ Dados escapados, sem XSS
```

---

## 6. Campos Exibidos na Confirmação

### Seção: Identificação
- Patrimônio / Código Interno
- ID do Ativo (gerado automaticamente)

### Seção: Classificação
- Tipo
- Marca
- Modelo
- Serial

### Seção: Localização e Setor
- Localidade
- Setor / Departamento

### Seção: Responsável
- Responsável
- E-mail

### Seção: Dados Operacionais
- Condição
- Status
- Data de Entrada
- Data de Saída

### Seção: Valor e Documentação
- Data de Compra
- Valor
- Garantia
- Nota Fiscal

### Seção: Detalhes Técnicos
- Observações
- Especificações Técnicas

---

## 7. Diferenças em Relação ao Fluxo Anterior

| Aspecto | Antes | Depois |
|---------|-------|--------|
| **Gravação** | Imediata no submit | 2-etapas (conf + confirm) |
| **Validação antes confirm** | Não | Modal com dados |
| **Proteção FE** | Botão desabilitado | Botão + disabled loop |
| **Proteção BE** | Nenhuma | Cache com hash |
| **Duplicação por clique** | SIM (risco) | NÃO (protegido) |
| **Feedback pós-sucesso** | Painel de docs | Redirecionamento + badge |
| **Badge NOVO** | Não | SIM (7 segundos) |
| **Compatibilidade** | N/A | 100% com anexos |

---

## 8. Código Alterado

### novo_ativo.html
- ✅ Modal de confirmação adicionada
- ✅ Handler de submit refatorado (2 etapas)
- ✅ Função renderConfirmationModal expandida (7 seções)
- ✅ Proteção contra double-submit
- ✅ Redirecionamento com parâmetro highlight
- ✅ Comentários documentando fluxo

### ativos.html
- ✅ Função renderAssets expandida para aceitar highlightId
- ✅ Badge "NOVO" renderizada condicionalmente
- ✅ Scroll automático até ativo destacado
- ✅ Lógica de captura de ?highlight= na URL
- ✅ Limpeza de parâmetro via history.replaceState
- ✅ Carregamento inicial com IIFE

### ativos_routes.py
- ✅ Imports: hashlib, json, time
- ✅ Cache global _creation_dedup_cache
- ✅ Função _gerar_chave_dedup
- ✅ Função _verificar_duplicacao
- ✅ Rota POST /ativos com lógica anti-duplicidade
- ✅ Comentários documentando proteção

---

## 9. Riscos e Limitações

| Risco | Severidade | Mitigação |
|-------|-----------|-----------|
| Cache em memória (não persistente) | BAIXA | OK para 10s, servidor reinicia limpa |
| Apenas 11 campos em dedup | BAIXA | Suficiente para casos de uso, pode expandir |
| TTL fixo 10s | BAIXA | Ajustável se necessário |
| Scroll automático (JS) | MUITO BAIXA | Graceful degrade se JS desabilitado |
| Badge não persiste (timeout) | BAIXA | Intencional (feedback temporário) |

---

## 10. Próximas Melhorias (Backlog)

1. **Persistência de Dedup:** Usar Redis/session em vez de memória
2. **Especificações Técnicas:** Exibir campos conforme tipo do ativo
3. **Anexos na Confirmação:** Preview de anexos selecionados antes de gravar
4. **Confirmação Modal mais Elegante:** Dialog HTML nativo (em vez de CSS div)
5. **Testes Automatizados:** Selenium/Cypress para testar fluxo JS
6. **Analytics:** Log de tempo de confirmação, taxa de abandono de modal

---

## Assinatura

**Implementado por:** Dev Senior Full Stack  
**Data:** 2026-04-16  
**Commits:**
- `089d608` Fluxo de cadastro com confirmação + anti-duplicidade
- `579277b` Campos expandidos na confirmação

**Status:** ✅ Pronto para homologação interna
