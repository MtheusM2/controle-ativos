# Diagnóstico UX/Visual — Fase 4.1 Acabamento

**Data:** 2026-04-28  
**Branch:** feature/evolucao-produto-v1  
**Fase:** 4.1 — Acabamento visual e experiência de uso

---

## RESUMO EXECUTIVO

O sistema controle-ativos/Opus Assets tem **arquitetura de templates bem estruturada** (Jinja2, modular, com partials). CSS é **premium e coerente** (theme dark wine). 

**Oportunidades identificadas:**
1. **Logo não está integrada** — sidebar usa apenas quadrado genérico
2. **Inconsistências visuais menores** em modais, botões, spacing
3. **Topo sem branding** — topbar é genérica
4. **Formulários podem ser mais elegantes** — especialmente em novo_ativo.html
5. **Feedback visual de ações** pode ser melhorado

**Risco:** Baixo. Mudanças são **puramente visuais**, não afetam rotas, validação ou importação.

---

## 1. ESTRUTURA ATUAL

### Templates Mapeados

```
Templates (14 arquivos):
├── Autenticação (3)
│   ├── index.html (login)
│   ├── register.html (cadastro)
│   └── recovery.html (recuperação)
│
├── Aplicação Autenticada (9)
│   ├── dashboard.html (KPIs, atalhos)
│   ├── ativos.html (listagem com filtros/export)
│   ├── novo_ativo.html (cadastro)
│   ├── editar_ativo.html (edição)
│   ├── detalhe_ativo.html (visualização)
│   ├── importar_ativos.html (import preview/confirm)
│   ├── configuracoes.html (settings)
│   └── base.html (layout master)
│
└── Partials (3)
    ├── sidebar.html (navegação fixa)
    ├── topbar.html (contexto do usuário)
    └── flash_messages.html (feedback global)
```

### CSS

- **Tamanho:** 2.687 linhas
- **Tema:** Dark mode premium com acentos wine (#a81936)
- **Estrutura:** CSS custom properties, bem organizado
- **Componentes:** Cards, tabelas, modais, botões, formulários

### Logos (Adicionadas)

```
web_app/static/images/
├── logo-opus-full.png (39 KB) — logo completa
├── logo-opus-square.png (43 KB) — quadrada (250×250px ideal)
└── logo-opus-horizontal.png (11 KB) — horizontal (90px height)
```

---

## 2. PROBLEMAS ENCONTRADOS

### 2.1 Branding & Logo

| Problema | Localização | Impacto | Severidade |
|----------|-------------|--------|-----------|
| Logo Opus não está em nenhum lugar | Aplicação inteira | Falta identidade visual | 🟡 ALTA |
| Sidebar usa "brand-mark" genérico | sidebar.html:5 | Não reconhecível | 🟡 ALTA |
| Topbar não tem identidade visual | topbar.html | Genérico | 🟡 ALTA |
| Login sem logo | index.html | Não profissional | 🟡 ALTA |
| Favicon não está definido | base.html | Detalhe perdido | 🟢 BAIXA |

### 2.2 Interfere & Consistência

| Problema | Localização | Detalhes | Severidade |
|----------|-------------|----------|-----------|
| Titles em maiúsculas inconsistentes | Vários | "OPUS ASSETS" vs "Opus Assets" | 🟢 BAIXA |
| Spacing em cards | novo_ativo.html | Margem inferior inconsistente | 🟢 BAIXA |
| Modais podem ser muito largos | ativos.html:60-200 | Filter modal em desktop ocupa 80% | 🟢 BAIXA |
| Botões secundários sem destaque | Vários | Ao lado de primários, pouco contraste | 🟢 BAIXA |

### 2.3 Formulários

| Problema | Localização | Detalhes | Severidade |
|----------|-------------|----------|-----------|
| novo_ativo.html muito longo | novo_ativo.html | Scroll infinito de campos | 🟡 ALTA |
| Campos agrupados sem separação visual clara | novo_ativo.html | "Cadastro base", "Especificações técnicas"... sem cards | 🟡 ALTA |
| Campos desabilitados e read-only sem indicação clara | editar_ativo.html | Cor igual, sem ícone | 🟡 MÉDIA |

### 2.4 Tabelas

| Problema | Localização | Detalhes | Severidade |
|----------|-------------|----------|-----------|
| Tabelas podem ficar muito estreitas em responsivo | ativos.html | Colunas ficam ilegíveis em tablet | 🟡 MÉDIA |
| Ações em tabelas (editar, deletar) sem ícones claros | ativos.html | Apenas texto "Editar" | 🟢 BAIXA |

### 2.5 Feedback Visual

| Problema | Localização | Detalhes | Severidade |
|----------|-------------|----------|-----------|
| Loading state não está claro | ativos.html:50 | "Carregando ativos..." é texto puro | 🟢 BAIXA |
| Mensagens de sucesso não têm ícone | flash_messages.html | Apenas cor verde | 🟢 BAIXA |
| Modal de confirmação pouco visual | Vários | Modal branco sem destaque | 🟢 BAIXA |

---

## 3. PRIORIZAÇÃO DE MELHORIAS

### Fase 4.1a — Branding & Logo (CRÍTICA)
```
Prioridade: 🔴 CRÍTICA
Risco: Mínimo (visual)
Tempo: 30min
Testes: Visuais apenas

Tarefas:
1. Integrar logo Opus na sidebar
2. Adicionar logo/branding no login
3. Adicionar favicon
4. Refinar topbar com identidade
```

### Fase 4.1b — Layout & Spacing (ALTA)
```
Prioridade: 🟡 ALTA
Risco: Baixo
Tempo: 1h30min
Testes: Visuais + manual

Tarefas:
1. Organizar novo_ativo.html em seções visuais
2. Melhorar spacing geral
3. Padronizar card layout
```

### Fase 4.1c — Componentes Visuais (MÉDIA)
```
Prioridade: 🟡 MÉDIA
Risco: Baixo
Tempo: 2h
Testes: Visuais + manual

Tarefas:
1. Melhorar feedback visual (loading, sucesso, erro)
2. Ícones em ações de tabela
3. Indicadores de campo disabled/readonly
```

### Fase 4.1d — Responsividade (BAIXA)
```
Prioridade: 🟢 BAIXA
Risco: Médio (pode quebrar em mobile)
Tempo: 2h
Testes: Testes em múltiplos breakpoints

Tarefas:
1. Verificar tabelas em responsivo
2. Modais em mobile
3. Formulários em mobile
```

---

## 4. RECOMENDAÇÕES ESPECÍFICAS

### 4.1 Logo na Sidebar

**Atual (sidebar.html:5):**
```html
<div class="brand-mark" aria-hidden="true"></div>
```

**Proposta:**
```html
<img 
    src="{{ url_for('static', filename='images/logo-opus-square.png') }}" 
    alt="Opus Assets Logo" 
    class="brand-logo"
    style="width: 40px; height: 40px; border-radius: 8px;"
>
```

**CSS a adicionar:**
```css
.brand-logo {
    object-fit: contain;
    transition: transform 0.2s ease;
}

.brand-logo:hover {
    transform: scale(1.05);
}
```

### 4.2 Logo no Login

**Adicionar em index.html antes do formulário:**
```html
<div style="text-align: center; margin-bottom: 24px;">
    <img 
        src="{{ url_for('static', filename='images/logo-opus-horizontal.png') }}" 
        alt="Opus Assets" 
        style="max-width: 200px; height: auto;"
    >
</div>
```

### 4.3 Favicon

**Adicionar em base.html na seção `<head>`:**
```html
<link rel="icon" type="image/png" href="{{ url_for('static', filename='images/logo-opus-square.png') }}">
```

### 4.4 Topbar com Branding

**Proposta:** Adicionar logo compacta + "Opus Assets" na topbar:
```html
<div class="topbar-brand">
    <img src="{{ url_for('static', filename='images/logo-opus-horizontal.png') }}" alt="Opus">
    <span>Opus Assets</span>
</div>
```

### 4.5 Novo Ativo — Organização em Seções

**Adicionar CSS classes:**
```css
.form-section {
    padding: 20px;
    border-bottom: 1px solid var(--line-soft);
}

.form-section:last-child {
    border-bottom: none;
}

.form-section-title {
    font-size: 0.9rem;
    font-weight: 700;
    text-transform: uppercase;
    color: var(--text-2);
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 2px solid var(--wine-2);
}
```

**Então agrupar campos:**
```html
<div class="form-section">
    <h3 class="form-section-title">Dados Básicos</h3>
    <!-- campos de identidade -->
</div>

<div class="form-section">
    <h3 class="form-section-title">Especificações</h3>
    <!-- campos técnicos -->
</div>

<div class="form-section">
    <h3 class="form-section-title">Responsabilidade</h3>
    <!-- campos de responsável -->
</div>
```

---

## 5. CHECKLIST DE VALIDAÇÃO

Após fazer as alterações, validar:

- [ ] Logo Opus aparece na sidebar
- [ ] Logo Opus aparece no login
- [ ] Favicon carrega corretamente
- [ ] Topbar tem identidade visual
- [ ] Novo ativo está organizado em seções
- [ ] Spacing está consistente
- [ ] Botões têm contraste adequado
- [ ] Modais estão bem dimensionados
- [ ] Tabelas legíveis em desktop
- [ ] Testes passando: `pytest -v`
- [ ] Sem regressão de funcionalidade

---

## 6. PRÓXIMOS PASSOS

1. **Hoje (4.1a):** Integrar logo nos 4 lugares estratégicos
2. **Hoje (4.1b):** Organizar novo_ativo.html em seções
3. **Hoje (4.1c):** Melhorar feedback visual
4. **Esta semana:** Responsividade em mobile
5. **Próxima semana:** Testes de usabilidade com usuários reais

---

**Autor:** Claude Code  
**Status:** Pronto para implementação  
**Branch:** feature/evolucao-produto-v1
