---
description: Auditoria de segurança em um arquivo, módulo ou funcionalidade do controle-ativos. Retorna achados classificados por risco com orientação de correção.
---

# /security-review — Auditoria de Segurança

**Alvo da revisão:** $ARGUMENTS

---

Você vai realizar uma auditoria de segurança focada no alvo indicado.
Se nenhum alvo for especificado, auditar os arquivos de maior risco: `services/auth_service.py`, `web_app/routes/auth_routes.py`, `web_app/routes/ativos_routes.py`, `config.py`.

## Processo de auditoria

### Passo 1 — Leitura completa
Leia cada arquivo do escopo **na íntegra** antes de emitir qualquer achado.
Trace o fluxo de dados de ponta a ponta.

### Passo 2 — Aplicar checklist por categoria

#### A. Injeção (SQL, Path Traversal, Command Injection)
- Toda query usa parâmetros `%s`? Nunca f-string ou `.format()` com dados externos?
- Caminhos de arquivo construídos a partir de input do usuário usam `Path(...).resolve()` e verificam que estão dentro do diretório permitido?
- Não há `subprocess`, `os.system`, `eval()` com dados externos?

#### B. Autenticação
- Sessão limpa com `session.clear()` antes de definir novo `user_id`?
- Senha hasheada com bcrypt + pepper antes de salvar?
- Bloqueio por tentativas falhas funcional e testado?
- Reset token hasheado no banco, nunca em plaintext?

#### C. Autorização (Controle de Acesso)
- Toda rota que acessa dados verifica `session.get("user_id")` presente?
- Operações em ativos filtram por `empresa_id` correspondente ao usuário logado?
- Rotas administrativas verificam `perfil == 'adm'`?
- Arquivos de upload acessíveis apenas pelo proprietário?

#### D. Exposição de Dados Sensíveis
- Logs não imprimem `senha`, `token`, `pepper`, `secret_key`?
- Respostas de erro não expõem stack trace em produção (`FLASK_DEBUG=0`)?
- Dados de sessão mínimos (sem informação além do necessário)?

#### E. Configuração e Segredos
- Nenhuma variável sensível hardcodada?
- `config.py` usa `_get_required_str()` para variáveis obrigatórias?
- Cookies com `httponly`, `samesite`, `secure` corretos?

#### F. Upload de Arquivos
- Extensões verificadas por allowlist (não denylist)?
- Nome de arquivo sanitizado antes de salvar no disco?
- Limite de tamanho aplicado no servidor?

## Formato do relatório

Para cada achado:

```
### [RISCO: CRÍTICO/ALTO/MÉDIO/BAIXO] — Título do achado

**Arquivo:** `caminho/do/arquivo.py`, linha X
**Evidência:** (trecho de código problemático)
**Impacto:** o que pode acontecer se explorado
**Correção:** o que fazer — com exemplo de código quando aplicável
```

## Classificação de risco

| Nível   | Critério                                                      |
|---------|---------------------------------------------------------------|
| Crítico | Exploração direta sem autenticação ou com dados de qualquer usuário |
| Alto    | Exploração requer autenticação mas compromete dados de outros |
| Médio   | Aumenta superfície de ataque ou facilita exploração futura    |
| Baixo   | Má prática que não tem vetor de exploração imediato claro     |

## Conclusão

Ao final, emitir:
- **Resumo:** N achados (X críticos, Y altos, Z médios, W baixos)
- **Recomendação prioritária:** o item mais urgente a corrigir antes do próximo deploy
- **Estado geral:** APTO / CONDICIONAL / NÃO APTO para produção
