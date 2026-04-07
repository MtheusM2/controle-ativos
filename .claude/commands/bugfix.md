---
description: Diagnosticar e corrigir um bug no controle-ativos — identifica a causa raiz antes de corrigir.
---

# /bugfix — Diagnosticar e corrigir bug

**Bug reportado:** $ARGUMENTS

---

Siga o processo abaixo. Não aplique correção antes de confirmar a causa raiz.

## 1. Reproduzir e entender o bug

- Qual é o comportamento atual? Qual é o esperado?
- Em qual rota, template ou operação ocorre?
- Ocorre sempre ou apenas em condições específicas (usuário admin, lista vazia, campo nulo)?

## 2. Rastrear o fluxo de dados

Siga o caminho do dado do ponto de entrada até o ponto de falha:

```
Request (form/JSON)
  → Rota (web_app/routes/)
    → Service (services/)
      → Banco (cursor_mysql)
        ← Resultado
      ← Model/dict
    ← Resposta JSON ou Template
  ← Browser
```

Leia os arquivos relevantes nessa ordem. Não adivinhe — leia o código.

## 3. Identificar a causa raiz

Antes de qualquer alteração, escreva em uma linha:

> **Causa raiz:** [o que exatamente está errado e por quê]

Causas comuns neste projeto:
- Filtro por `empresa_id` ausente → usuário vê dados de outra empresa
- `None` não tratado ao acessar campo opcional do banco
- Migração aplicada no dev mas não no schema.sql (ou vice-versa)
- Flash message não aparece porque redirect acontece antes do `flash()`
- Rota retorna JSON mas frontend espera redirecionamento (ou vice-versa)
- Coluna renomeada na migração mas query ainda usa nome antigo
- `session.get("user_id")` retorna string em vez de int → comparação falha

## 4. Aplicar a correção cirúrgica

- Corrigir **apenas** o que causou o bug — sem refatorações aproveitando a oportunidade
- Se a correção requer migração SQL, criar em `database/migrations/NNN_descricao.sql`
- Se a correção afeta comportamento de rota, verificar todos os templates que consomem essa rota

## 5. Verificar que o fix não quebra nada

```bash
pytest tests/ -v
```

Se não existe teste que teria capturado este bug:
- Escrever o teste que reproduz o bug (deve falhar antes do fix, passar depois)
- Adicionar ao arquivo de testes correspondente

## 6. Documentar

No commit, descrever:
- O que estava errado
- Por que estava errado
- Como foi corrigido

Formato de commit: `fix: <descrição curta do problema corrigido>`
