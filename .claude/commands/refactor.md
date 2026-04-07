---
description: Refatoração cirúrgica de código no controle-ativos — melhora qualidade sem alterar comportamento externo.
---

# /refactor — Refatoração Cirúrgica

**Alvo:** $ARGUMENTS

---

Você vai refatorar o código indicado. Siga este processo para garantir que o comportamento externo permaneça idêntico.

## Princípios desta refatoração

1. **Comportamento externo inalterado** — rotas, assinaturas de função pública, respostas HTTP e exceções levantadas permanecem os mesmos
2. **Cirúrgica** — escopo limitado ao que foi pedido; sem "melhorar enquanto passa por ali"
3. **Testável** — se não há teste antes, escrever antes de refatorar; se há, garantir que continuam passando
4. **Motivada** — cada mudança tem um motivo claro (legibilidade, eliminar duplicação, separar responsabilidade)

## Processo

### Passo 1 — Ler o código original na íntegra

Leia todos os arquivos do escopo. Entenda o comportamento atual antes de qualquer mudança.

### Passo 2 — Identificar os problemas reais

Categorize o que está sendo resolvido:

| Problema                        | Exemplo                                              |
|---------------------------------|------------------------------------------------------|
| Duplicação de código            | Mesmo bloco `try/except` em 3 rotas                  |
| Função com muitas responsabilidades | Service que valida, acessa banco e formata resposta |
| Nome não descritivo             | `def proc(d)` → `def processar_dados_ativo(dados)`   |
| Magic number sem nome           | `if tentativas > 5` → usar constante `MAX_TENTATIVAS`|
| Lógica de negócio na rota       | Query SQL diretamente na view function               |
| Acesso direto ao banco no model | Model que chama `cursor_mysql()` diretamente         |

### Passo 3 — Planejar antes de executar

Para cada mudança planejada, confirmar:
- Esta mudança altera o comportamento externo? → Se sim, não é refatoração, é feature
- Esta mudança quebra algum teste existente? → Ajustar expectativa dos testes se necessário (mas não o contrato)
- Esta mudança afeta outros arquivos que importam este? → Listar e atualizar todos

### Passo 4 — Executar uma mudança por vez

Não fazer tudo de uma vez. A ordem segura:
1. Extrair função auxiliar privada (sem mudar chamadores)
2. Atualizar chamadores para usar a nova função
3. Remover código morto
4. Renomear (com substituição global)
5. Reorganizar estrutura de módulo

### Passo 5 — Verificar

Após cada etapa significativa:
```bash
pytest tests/ -v
```

Se algum teste falhar → reverter a última mudança, entender o porquê antes de prosseguir.

## O que NÃO fazer nesta refatoração

- Não adicionar novas funcionalidades
- Não mudar assinaturas de funções públicas (usadas por outros módulos)
- Não alterar a estrutura de resposta JSON das rotas
- Não adicionar dependências externas
- Não reescrever do zero — refatorar em passos pequenos e verificáveis
- Não adicionar comentários ou docstrings onde o código é autoexplicativo

## Entregáveis

Ao concluir:
1. Lista das mudanças feitas com justificativa de cada uma
2. Confirmação de que `pytest tests/ -v` passa
3. Identificação de qualquer dívida técnica relacionada que ficou de fora do escopo (para futura tarefa)
