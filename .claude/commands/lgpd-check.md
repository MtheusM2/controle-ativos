---
description: Verificação prática de adequação à LGPD no projeto controle-ativos — identifica riscos reais e orienta medidas proporcionais ao contexto de sistema corporativo interno.
---

# /lgpd-check — Verificação Prática de Adequação à LGPD

**Escopo:** $ARGUMENTS

---

Você vai realizar uma verificação prática de adequação à LGPD para o **controle-ativos**.

**Contexto:** sistema corporativo interno de gestão de ativos de TI. Os usuários são colaboradores da empresa. Os dados pessoais tratados são mínimos e com finalidade legítima clara (controle operacional de ativos e autenticação de usuários internos).

A análise deve ser **pragmática e proporcional** ao contexto — não jurídica ou acadêmica.

---

## 1. Mapeamento de Dados Pessoais

Identifique todos os dados pessoais presentes no sistema:

### Dados identificados no schema atual
| Dado           | Tabela      | Coluna                    | Finalidade                     |
|----------------|-------------|---------------------------|--------------------------------|
| Nome completo  | `usuarios`  | `nome`                    | Identificação e auditoria      |
| E-mail         | `usuarios`  | `email`                   | Autenticação e comunicação     |
| Histórico login| `usuarios`  | `ultimo_login_em`         | Segurança e auditoria          |
| Responsável    | `ativos`    | `usuario_responsavel`     | Controle operacional de ativo  |

### Verificar também
- Logs: `logs/backend.log` — contém dados pessoais (email, nome, IP)?
- Arquivos de upload: podem conter documentos com dados pessoais?
- Session data: o que é armazenado na sessão Flask?

---

## 2. Checklist de Adequação Prática

### Base Legal (Art. 7º LGPD)
- [ ] O tratamento de dados de colaboradores para uso de sistema interno é justificado pela **execução de contrato** (relação de trabalho) — base legal legítima sem necessidade de consentimento explícito
- [ ] Dados de ativos com `usuario_responsavel` são necessários para a finalidade declarada (controle operacional)?
- [ ] Há dados sendo coletados que excedem o necessário para a finalidade? (princípio da minimização)

### Direitos do Titular (Arts. 18-20)
- [ ] Existe forma de um usuário solicitar acesso aos seus próprios dados?
- [ ] Existe forma de corrigir dados incorretos? (a tela de configurações já permite atualizar nome e email)
- [ ] Existe procedimento documentado para exclusão de usuário (direito ao esquecimento)?
- [ ] Usuário pode visualizar quais dados seus estão armazenados?

### Segurança dos Dados (Art. 46)
- [ ] Senhas hasheadas com bcrypt + pepper (não reversível)?
- [ ] Acesso ao banco com usuário de permissões mínimas (`opus_app`)?
- [ ] Comunicação via HTTPS em produção?
- [ ] Logs não contêm senhas ou tokens em plaintext?
- [ ] Upload de arquivos com validação e restrição de acesso?

### Retenção e Descarte
- [ ] Há política de retenção de logs? (quanto tempo `logs/backend.log` é mantido?)
- [ ] Usuários inativos ou desligados — há processo de desativação ou exclusão?
- [ ] Tokens de reset de senha têm expiração configurada? (`reset_token_expira_em`)

### Transparência
- [ ] Os colaboradores são informados sobre o tratamento de dados no uso do sistema? (política interna, termo de uso)

---

## 3. Riscos Identificados

Para cada risco, classificar:
- **Alto:** pode configurar violação direta à LGPD com impacto a titulares
- **Médio:** práticas que aumentam risco mas não configuram violação imediata
- **Baixo:** melhorias de conformidade sem risco imediato

---

## 4. Recomendações Práticas

Priorizar pelo impacto × facilidade de implementação:

### Alta prioridade (implementar antes do go-live)
- Procedimento documentado de exclusão/desativação de usuário
- Política de retenção de logs (rotação automática ou exclusão periódica)
- Verificar se logs não contêm dados pessoais além do necessário

### Média prioridade (implementar após estabilização)
- Tela para o usuário visualizar seus próprios dados armazenados
- Documentação interna de política de privacidade / uso do sistema

### Baixa prioridade (maturidade futura)
- Registro formal de atividades de tratamento (ROPA)
- Relatório de Impacto à Proteção de Dados (RIPD) se o escopo expandir

---

## 5. Conclusão

Emitir:
- **Nível de risco atual:** Baixo / Médio / Alto
- **Itens que impedem go-live responsável:** (lista)
- **Próximos 3 passos prioritários:** (ordenados por impacto)
- **Observação:** sistema corporativo interno com dados mínimos de colaboradores tem risco LGPD inerentemente baixo — adequação é incremental, não bloqueante
