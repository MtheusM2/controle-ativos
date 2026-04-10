# FASE D — LGPD Mínima para Uso Interno (Parte 2)

**Data:** 2026-04-10  
**Status:** Análise Prática + Adequações Mínimas  
**Prioridade:** Média (não bloqueia produção, mas necessário para conformidade básica)

---

## 1. Contexto Corporativo

**Sistema:** controle-ativos é uma **aplicação corporativa interna** para gestão de ativos de TI.

**Usuários:** Apenas funcionários da empresa autorizado.

**Escopo LGPD aplicável:**
- Lei Geral de Proteção de Dados (Lei 13.709/2018)
- Adequação prática (não burocrática)
- Foco em proteção de dados pessoais tratados
- Sem necessidade de DPO formal (organizações de pequeno/médio porte)

---

## 2. Mapa de Dados Pessoais Tratados

### 2.1 Dados Pessoais Identificados

| Dado | Tabela | Campo | Finalidade | Necessário? |
|------|--------|-------|-----------|-----------|
| **Nome** | usuarios | nome | Identificação de usuário | ✅ SIM |
| **Email** | usuarios | email | Autenticação, comunicação | ✅ SIM |
| **Hash de Senha** | usuarios | senha_hash | Autenticação | ✅ SIM |
| **Pergunta Recuperação** | usuarios | pergunta_recuperacao | Recuperação de senha | ✅ SIM |
| **Hash Resposta Recuperação** | usuarios | resposta_recuperacao_hash | Recuperação de senha | ✅ SIM |
| **IP de Login** | auditoria_eventos | ip_origem | Segurança, rastreabilidade | ✅ SIM |
| **User-Agent** | auditoria_eventos | user_agent | Segurança, rastreabilidade | ⚠️ OPCIONAL |
| **Responsável de Ativo** | ativos | usuario_responsavel | Gestão de ativos | ✅ SIM |
| **Timestamps** | (vários) | criado_em, atualizado_em | Auditoria | ✅ SIM |
| **IP/User-Agent de Requisição** | logs | (se implementado) | Segurança | ⚠️ OPCIONAL |

### 2.2 Dados NÃO Pessoais (não regulados pela LGPD)

| Dado | Campo | Observação |
|------|-------|-----------|
| ID do Ativo | ativos.id | Código identificador de bem, não de pessoa |
| Tipo/Marca/Modelo | ativos.tipo, .marca, .modelo | Informação técnica do bem |
| Departamento | ativos.departamento | Unidade organizacional |
| Status | ativos.status | Estado do bem |
| Empresa ID | empresa_id (todo lugar) | Identificador técnico |

---

## 3. Análise de Risco LGPD

### 3.1 Categorização de Risco

| Dado | Risco | Mitigation |
|------|-------|-----------|
| Email | **Médio** | Enviado em comunicações, pode ser exposto | Restringir acesso, criptografia em trânsito (HTTPS) |
| Senha (hash) | **Baixo** | Hash irreversível (PBKDF2 + pepper) | Manter pepper seguro, nunca expor |
| IP de login | **Baixo** | Pode revelar localização aproximada | Registrar apenas quando necessário (segurança) |
| User-Agent | **Baixo** | Informação técnica, não identifica pessoa | Pode ser removido de logs antigos |

### 3.2 O que NÃO é Risco

- ❌ Dados de ativos (notebooks, computadores) — bens corporativos
- ❌ Nome do responsável do ativo — necessário para gestão do bem
- ❌ Departamento do usuário — unidade organizacional, não dado pessoal sensível

---

## 4. Adequações Mínimas Recomendadas

### 4.1 Nível 1 — Obrigatório para Produção

#### 1.1 Aviso de Privacidade Simples
**Localização:** Login page ou área de acesso

**Conteúdo mínimo:**
```
AVISO DE PRIVACIDADE

Este sistema de gestão de ativos trata dados pessoais limitados
(nome, email, IP de acesso) apenas para:
- Autenticação de acesso
- Gestão de ativos corporativos
- Rastreabilidade de ações por segurança

Responsável pelas informações: [seu_nome_ou_area_ti@empresa.com]

Seus direitos:
- Acessar seus dados pessoais
- Corrigir informações incorretas
- Solicitar exclusão (quando aplicável)

Para exercer direitos, contate: [email_responsavel]
```

#### 1.2 Política de Retenção Simples
**Documentação:** `docs/POLITICA_RETENCAO_DADOS.md`

```
POLÍTICA DE RETENÇÃO DE DADOS PESSOAIS

1. Emails e nomes de usuário:
   - Retido enquanto usuário ativo
   - Deletado 30 dias após desativação

2. Logs de auditoria (IP, timestamps):
   - Retido por 90 dias
   - Deletado automaticamente após esse período
   - Exceção: logs de falhas de segurança (180 dias)

3. Hashes de senha:
   - Não deletados (dado técnico de autenticação)
   - Hashado de forma irreversível

4. Dados de recuperação de senha:
   - Deletados após primeiro uso
   - Expiram em 24 horas
```

#### 1.3 Ponto Focal de Dados
**Ação:** Designar responsável e documentar

```
RESPONSÁVEL PELOS DADOS PESSOAIS
(Conforme LGPD, artigo 5º, VIII)

Nome: [Nome completo do TI/Ops]
Cargo: [Gestor de TI / Administrador de Sistemas]
Email: [email_responsavel@empresa.com]
Telefone: [ramal]

Responsabilidade:
- Atender requisições de acesso a dados pessoais
- Autorizar exclusões (quando aplicável)
- Investigar incidentes de segurança
- Manter conformidade com LGPD
```

### 4.2 Nível 2 — Importante, Não Crítico

#### 2.1 Fluxo de Incidente de Segurança
**Se dados pessoais forem expostos/vazados:**

1. **Identificar:** Que dados, quando, para quem
2. **Isolar:** Bloquear conta afetada, cancelar tokens
3. **Registrar:** Criar ticket de segurança
4. **Notificar:** Diretor de TI, responsável de dados
5. **Corrigir:** Patch, mudança de senha, reset de tokens
6. **Documentar:** Para possível comunicação posterior

**Responsável:** TI/Ops local

#### 2.2 Consentimento Implícito
Para **uso interno**, é aceitável:
- Consentimento implícito no "Termo de Uso de Sistemas Corporativos"
- Documento assinado na admissão
- Referência ao aviso de privacidade

**Ação:** Revisar contrato de trabalho/onboarding já existente.

#### 2.3 Direitos do Titular
Usuários podem solicitar:
- **Acesso:** Visualizar dados pessoais deles mesmos
- **Correção:** Atualizar nome/email
- **Exclusão:** Remover (quando aplicável — ex: após saída)
- **Portabilidade:** Receber cópia de dados

**Fluxo simples:**
1. Usuário envia email para [responsável]
2. TI valida identidade
3. TI executa ação (acesso, correção ou exclusão)
4. Confirma em até 10 dias

---

## 5. O Que JÁ ESTÁ Bom no Sistema

✅ **Senhas hasheadas** — Não armazenam plaintext (PBKDF2 + pepper)  
✅ **HTTPS preparado** — Proteção em trânsito quando ativo  
✅ **Auditoria** — Rastreamento de quem fez o quê (Fase C)  
✅ **Sessão segura** — Cookie HTTPONLY, SAMESITE, SECURE (quando HTTPS)  
✅ **Isolamento por empresa** — Usuários de uma empresa não veem dados de outra  
✅ **Perfis e permissões** — Controle de acesso implementado (Fase B)  

---

## 6. O Que AINDA Falta (Não Crítico para MVP)

⏸️ **Deletar conta de usuário** — Função administrativa (fica para Fase 3)  
⏸️ **Exportar dados do usuário** — Portabilidade de dados (fica para Fase 3)  
⏸️ **DPO formal** — Designação de Data Protection Officer (fica para quando escalar)  
⏸️ **Aviso na tela inicial** — Template com aviso (fácil de adicionar)  
⏸️ **Registro de consentimento** — Sistema de consentimento explícito (fica para Fase 3)  

---

## 7. Implementação em Sprint 2.1

### O Que Será Feito Agora

1. **Criar arquivo `docs/AVISO_PRIVACIDADE.txt`**
   - Simples, corporativo, prático
   - Exibir ao fazer login (optional, mas recomendado)

2. **Criar arquivo `docs/POLITICA_RETENCAO_DADOS.md`**
   - Documentar retenção de logs, dados de usuário
   - Implementar limpeza automática de logs antigos

3. **Documentar `docs/PONTO_FOCAL_DADOS.md`**
   - Nome e email do responsável
   - Procedimento de atendimento de direitos

4. **Documentar `docs/FLUXO_INCIDENTE_SEGURANCA.md`**
   - Procedimento se dados pessoais forem expostos
   - Quem notificar, quando

5. **Atualizar schema.sql**
   - Adicionar comentário sobre LGPD
   - Documentar qais colunas contêm dados pessoais

---

## 8. Script de Limpeza de Logs (Automático)

**Arquivo:** `scripts/limpar_logs_auditoria.ps1`

```powershell
# Executar via Windows Task Scheduler (mensal)
# Remove logs de auditoria com mais de 90 dias

$dias_retencao = 90
$data_limite = (Get-Date).AddDays(-$dias_retencao)

mysql -u opus_app -p"$senha" controle_ativos -e "
DELETE FROM auditoria_eventos
WHERE criado_em < '$data_limite'
  AND tipo_evento NOT IN ('LOGIN_FALHA', 'ACESSO_NEGADO');
"

# Registrar em log
$timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
Add-Content -Path "C:\controle_ativos\logs\limpeza_auditoria.log" -Value "$timestamp: Logs removidos com sucesso"
```

---

## 9. Integração em Deploy

**Checklist para produção:**

- [ ] Aviso de privacidade visível aos usuários
- [ ] Política de retenção documentada
- [ ] Responsável de dados identificado e comunicado
- [ ] HTTPS configurado (SESSION_COOKIE_SECURE=1)
- [ ] Backup automatizado de dados
- [ ] Plano de recuperação em caso de incidente

---

## 10. Veredito Técnico LGPD

✅ **Sistema é adequado para uso corporativo interno.**

**Base:**
- Dados pessoais tratados são mínimos e necessários
- Proteção técnica (PBKDF2, HTTPS, isolamento) está implementada
- Auditoria de ações permite rastreabilidade
- Consentimento implícito é aceitável para uso interno

**Para escalar para ambiente externo ou maior exposição:**
- Seria necessário DPO formal
- Documentação mais rigorosa
- Consentimento explícito
- Mas para uso interno corporativo: **OK**

---

## 11. Próximos Passos

### Sprint 2.1
- [ ] Criar documentação de privacidade (Nível 1)
- [ ] Implementar limpeza automática de logs
- [ ] Comunicar responsável de dados aos usuários
- [ ] Revisar contrato de trabalho/onboarding

### Sprint 2.2+
- [ ] Interface para usuário exercer direitos (portabilidade, correção)
- [ ] Dashboard de segurança com alertas
- [ ] Auditoria mais granular

### Futuro (quando escalar)
- [ ] Contratar DPO
- [ ] Certificação de conformidade
- [ ] Processo formalde consentimento
- [ ] Análise de impacto de privacidade (AIPD)

---

## 12. Referências Práticas

**Lei Geral de Proteção de Dados:**
- Lei 13.709/2018 (Brasil)
- Artigos-chave: 5, 6, 7, 8 (conceitos), 18-21 (direitos do titular)

**Autoridade:** ANPD (Autoridade Nacional de Proteção de Dados)
- Website: www.gov.br/cidadania/pt-br/acesso-a-informacao/lgpd
- Orientações práticas para empresas pequenas/médias

**Documentação Recomendada:**
- "LGPD Prática" (ANPD) — guia executivo simples
- "Privacy by Design" — princípio de proteção desde o início

---

**Responsável pela análise:** Claude Code  
**Data:** 2026-04-10  
**Versão:** 1.0  
**Categoria:** Análise prática, não consultoria jurídica
