# Checklist de Homologação — Importador Flexível

**Data:** 2026-04-22  
**Versão:** Fase 3 — Testes em Desenvolvimento  
**Responsável:** [Nome do Testador]  
**Status:** [ ] Em Progresso

---

## Pré-Condições

Antes de iniciar os testes, verifique:

- [ ] App rodando em `http://localhost:5000` (ou configurado)
- [ ] Banco MySQL conectado e com dados de teste
- [ ] Usuário logado com perfil `usuario` (empresa_id=1)
- [ ] Navegador com console aberto (F12) para capturar erros
- [ ] Todos os 3 bugs críticos foram corrigidos:
  - [ ] Bug #1: `obter_usuario_sessao` importado ou removido
  - [ ] Bug #2: Rota `/confirmar` lê FormData corretamente
  - [ ] Bug #3: 4 checkboxes visíveis no template

---

## Grupo A — Upload e Preview (7 casos)

### M-A01: CSV com cabeçalho perfeito

**Ação:**
1. Acesse a tela de importação (`/ativos/importar`)
2. Selecione e envie arquivo com headers: `id,tipo,marca,modelo,departamento,status,data_entrada`
3. Clique "Analisar e pré-visualizar"

**Resultado Esperado:**
- [ ] Painel de preview abre
- [ ] Seção "Reconhecidos automaticamente" mostra ≥6 campos em verde
- [ ] Seção "Sugestões" está vazia ou mínima
- [ ] Amostra de gravação mostra dados mapeados corretamente
- [ ] Nenhuma mensagem de erro ou bloqueio

**Status:** ☐ Passou | ☐ Falhou | ☐ Não testado  
**Notas:** ___________

---

### M-A02: CSV com cabeçalho alternativo

**Ação:**
1. Selecione arquivo com headers alternativos: `patrimonio,tipo_equipamento,fabricante,modelo_equipamento,setor,situacao,data`
2. Clique "Analisar"

**Resultado Esperado:**
- [ ] Painel "Sugestões" aparece com campos para confirmar
- [ ] Ex: "patrimonio" → "id" (com score e motivo)
- [ ] Botão "Confirmar importação" desabilitado (aguardando decisões)
- [ ] Após selecionar "Aplicar sugestão" para cada campo, botão habilita

**Status:** ☐ Passou | ☐ Falhou | ☐ Não testado  
**Notas:** ___________

---

### M-A03: CSV com colunas extras

**Ação:**
1. Selecione arquivo com headers: `id,tipo,marca,modelo,departamento,status,data_entrada,coluna_extra_1,coluna_extra_2`
2. Clique "Analisar"

**Resultado Esperado:**
- [ ] Seção "Ignoradas" lista `coluna_extra_1` e `coluna_extra_2`
- [ ] Nenhum bloqueio de importação
- [ ] Mensagem indica que colunas extras serão descartadas

**Status:** ☐ Passou | ☐ Falhou | ☐ Não testado  
**Notas:** ___________

---

### M-A04: CSV com cabeçalho deslocado (linha 3)

**Ação:**
1. Selecione arquivo com:
   ```
   Sistema de Controle de Ativos
   Exportado em 2026-04-22
   
   id,tipo,marca,modelo,departamento,status,data_entrada
   NTB-001,Notebook,...
   ```
2. Clique "Analisar"

**Resultado Esperado:**
- [ ] Painel abre sem erro
- [ ] Detector reconhece cabeçalho na linha correta
- [ ] Preview mostra 1 linha de dados (NTB-001)
- [ ] Nenhuma mensagem de erro

**Status:** ☐ Passou | ☐ Falhou | ☐ Não testado  
**Notas:** ___________

---

### M-A05: CSV com campo crítico ausente

**Ação:**
1. Selecione arquivo SEM coluna `tipo`: `marca,modelo,departamento,status,data_entrada`
2. Clique "Analisar"

**Resultado Esperado:**
- [ ] Banner vermelho aparece: "Importação bloqueada por requisitos críticos"
- [ ] Seção "Bloqueios de importação" lista "Campo crítico não encontrado: tipo"
- [ ] Botão "Confirmar" está desabilitado
- [ ] Status code HTTP 400 (verificar em Network do navegador)

**Status:** ☐ Passou | ☐ Falhou | ☐ Não testado  
**Notas:** ___________

---

### M-A06: Arquivo .xlsx (formato inválido)

**Ação:**
1. Tente enviar arquivo `.xlsx` ou `.xls`

**Resultado Esperado:**
- [ ] Mensagem de erro clara: "Formato inválido" ou "Apenas CSV"
- [ ] Painel de preview não abre
- [ ] Nenhum erro 500 no console

**Status:** ☐ Passou | ☐ Falhou | ☐ Não testado  
**Notas:** ___________

---

### M-A07: Arquivo vazio

**Ação:**
1. Crie arquivo CSV vazio (`b''`) e tente enviar

**Resultado Esperado:**
- [ ] Mensagem de erro: "Arquivo CSV vazio"
- [ ] Painel de preview não abre
- [ ] Status code HTTP 400

**Status:** ☐ Passou | ☐ Falhou | ☐ Não testado  
**Notas:** ___________

---

## Grupo B — Confirmação com Checkboxes (4 casos)

### M-B01: Botão desabilitado até checkboxes marcados

**Ação:**
1. Gere preview com CSV válido
2. Observe o botão "Confirmar importação"
3. Tente clicar nele (deve estar desabilitado)
4. Marque os 4 checkboxes: revisor_dados, confirma_duplicatas, aceita_avisos, autoriza_importacao

**Resultado Esperado:**
- [ ] Botão desabilitado inicialmente (cinzento)
- [ ] Mensagem abaixo do botão: "Marque todas as confirmações..."
- [ ] Após marcar todos os 4, botão fica azul e habilitado
- [ ] Mensagem muda: "Pré-requisitos atendidos"
- [ ] Desmarcar qualquer checkbox desabilita novamente

**Status:** ☐ Passou | ☐ Falhou | ☐ Não testado  
**Notas:** ___________

---

### M-B02: Importação bem-sucedida

**Ação:**
1. Preview OK, com CSV válido
2. Marque todos os 4 checkboxes
3. Clique "Confirmar importação"
4. Aguarde sucesso

**Resultado Esperado:**
- [ ] Mensagem de sucesso em verde: "Importação concluída"
- [ ] Status code HTTP 201
- [ ] Lista de ativos atualizada (pode redirecionar ou recarregar)
- [ ] Nenhum erro 500 no console

**Status:** ☐ Passou | ☐ Falhou | ☐ Não testado  
**Notas:** ___________

---

### M-B03: Sugestões pendentes desabilitam botão

**Ação:**
1. Gere preview com CSV que tenha colunas com sugestões
2. NÃO confirme as sugestões (deixe em "Selecione uma decisão")
3. Marque todos os 4 checkboxes

**Resultado Esperado:**
- [ ] Botão permanece desabilitado
- [ ] Mensagem: "...sugestão(ões) sem decisão..."
- [ ] Após confirmar todas as sugestões, botão habilita

**Status:** ☐ Passou | ☐ Falhou | ☐ Não testado  
**Notas:** ___________

---

### M-B04: Modo duplicata funciona

**Ação:**
1. Gere preview com CSV que tem IDs que já existem no banco
2. Seção de duplicatas mostra "IDs existentes: ..."
3. Marque todos os checkboxes
4. Clique "Confirmar" com modo "ignorar" (não criar duplicatas)

**Resultado Esperado:**
- [ ] Importação completa com sucesso
- [ ] Mensagem indica "Modo: ignorar duplicatas"
- [ ] Apenas ativos NOVOS são criados (não atualiza os existentes)

**Status:** ☐ Passou | ☐ Falhou | ☐ Não testado  
**Notas:** ___________

---

## Grupo C — Indicadores Visuais de Risco (4 casos)

### M-C01: CSV com ~5% erro → alerta amarelo

**Ação:**
1. Gere preview com CSV que tem 1 erro em ~20 linhas (5% taxa de erro)

**Resultado Esperado:**
- [ ] Badge de status mostra "alerta" em amarelo
- [ ] Seção "Avisos por linha" lista erros específicos
- [ ] Import pode continuar (não está bloqueado)
- [ ] Botão "Confirmar" não está desabilitado por bloqueios

**Status:** ☐ Passou | ☐ Falhou | ☐ Não testado  
**Notas:** ___________

---

### M-C02: CSV com 60% erro → bloqueado vermelho

**Ação:**
1. Gere preview com CSV que tem muitos erros (ex: datas inválidas em 3 de 5 linhas)

**Resultado Esperado:**
- [ ] Banner vermelho: "Importação bloqueada..."
- [ ] Badge de status: "bloqueado" em vermelho
- [ ] Seção "Bloqueios": "Taxa de erro (60%) excedeolimite (50%)"
- [ ] Botão "Confirmar" desabilitado

**Status:** ☐ Passou | ☐ Falhou | ☐ Não testado  
**Notas:** ___________

---

### M-C03: Email ausente → aviso mas permite import

**Ação:**
1. Gere preview com CSV que não tem coluna `email_responsavel`

**Resultado Esperado:**
- [ ] Seção "Avisos por linha" mostra "Email não fornecido" em amarelo
- [ ] Status geral pode ser "alerta" (não bloqueado)
- [ ] Botão "Confirmar" habilita após marcar checkboxes

**Status:** ☐ Passou | ☐ Falhou | ☐ Não testado  
**Notas:** ___________

---

### M-C04: CSV com 10K linhas carrega em < 15s

**Ação:**
1. Crie CSV com 10.000 linhas de dados válidos
2. Clique "Analisar"
3. Observe o tempo no console (Network → GET /preview)

**Resultado Esperado:**
- [ ] Tempo total < 15 segundos
- [ ] Preview carrega e mostra resultado sem timeout
- [ ] Painel renderiza sem conglar o navegador
- [ ] Nenhum erro 500 ou 504

**Status:** ☐ Passou | ☐ Falhou | ☐ Não testado  
**Performance:** _____ segundos

---

## Checklist de Segurança

Teste os cenários defensivos manualmente:

### R01: CSV injection
- [ ] Coluna com `=CMD("calc")` é tratada como texto, não executada

### R03: Arquivo grande (50MB)
- [ ] Arquivo > 10MB é rejeitado com mensagem clara

### R05: SQL injection
- [ ] Coluna com `'; DROP TABLE;--` não executa
- [ ] Valores são escapados corretamente no banco

### R07: CSRF expirado
- [ ] Token CSRF inválido retorna 403 (não 500)
- [ ] Nenhum dado parcialmente importado

### R09: ID com caracteres XSS
- [ ] ID com `<script>alert(1)</script>` é rejeitado como ID_INVALIDO
- [ ] Mensagem clara de erro

---

## Resumo Final

| Grupo | Testes | Passaram | Falharam | Notas |
|-------|--------|----------|----------|-------|
| A     | 7      | ___/7    | ___/7    | |
| B     | 4      | ___/4    | ___/4    | |
| C     | 4      | ___/4    | ___/4    | |
| Seg   | 5      | ___/5    | ___/5    | |
| **Total** | **20** | **___/20** | **___/20** | |

---

## Gates de Aprovação

- [ ] **Gate A (Manual UI):** Todos M-A01 a M-A07 passaram
- [ ] **Gate B (Confirmação):** Todos M-B01 a M-B04 passaram
- [ ] **Gate C (Risco):** Todos M-C01 a M-C04 passaram e R01–R09 defensivos
- [ ] **Gate D (Performance):** M-C04 concluído em < 15s
- [ ] **Gate E (Sem Erros 500):** Nenhum erro 500 em nenhum cenário

---

## Assinatura

**Testador:** _________________________ **Data:** ___/___/______

**Supervisor:** _______________________ **Data:** ___/___/______

---

## Observações Finais

```
[Espaço para anotações de bugs encontrados, comportamentos inesperados, etc.]
```
