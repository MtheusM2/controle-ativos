# Lista de Riscos Atuais — Controle de Ativos

**Data:** 2026-04-16  
**Atualização:** Consolidação Técnica v1.0

---

## Resumo Executivo

| Severidade | Quantidade | Status |
|-----------|-----------|--------|
| 🔴 CRÍTICO | 2 | Aberto (ação antes de prod ampla) |
| 🟠 ALTO | 3 | Aberto (ação antes de prod) |
| 🟡 MÉDIO | 2 | Aberto (ação em 30 dias) |
| 🟢 BAIXO | 2 | Aberto (nice-to-have) |

**Total:** 9 riscos identificados | **Bloqueadores:** 2

---

## RISCOS CRÍTICOS (Bloqueia Produção Ampla)

### 🔴 RC-001: Backup Não Configurado
**Severidade:** CRÍTICO  
**Categoria:** Disaster Recovery  
**Descrição:**  
Sistema não tem backup automático. Se servidor falhar ou dados forem corrompidos, não há recuperação possível.

**Cenário de Risco:**
- Servidor ou disco falha
- Dados corrompidos por malware/ataque
- Exclusão acidental de dados críticos
→ **Resultado:** Perda total de dados de 2+ meses

**Solução Recomendada:**
1. Configurar backup diário do banco MySQL
2. Retenção de 30 dias mínimo
3. Testar restore em ambiente de teste
4. Monitorar espaço em disco para backups
5. Documentar RTO/RPO (2h máximo)

**Custo:** 2-4 horas de implementação  
**Prazo:** Antes de liberar para produção ampla  
**Responsável:** Deploy Engineer  
**Status:** ❌ NÃO INICIADO

---

### 🔴 RC-002: Rate Limiting em Login Ausente
**Severidade:** CRÍTICO  
**Categoria:** Segurança - Força Bruta  
**Descrição:**  
Sistema implementa contagem de tentativas de login falhas com bloqueio temporário, mas não há rate limiting na API (/login). Um atacante pode fazer 1000+ requisições/segundo contra a rota.

**Cenário de Risco:**
- Ataque de força bruta (dicionário)
- Ataque DDoS contra /login
- Enumeração de usuários válidos
→ **Resultado:** Conta de usuário comprometida ou servidor indisponível

**Solução Recomendada:**
1. Implementar rate limiting por IP: máx 5 requisições/minuto para /login
2. Implementar rate limiting por usuário: máx 5 requisições/minuto
3. Usar biblioteca como Flask-Limiter
4. Log de tentativas suspeitas
5. Alert se > 10 falhas diferentes de 1 IP

**Custo:** 3-5 horas de implementação  
**Prazo:** Antes de liberar para produção ampla  
**Responsável:** Backend Engineer  
**Status:** ❌ NÃO INICIADO

---

## RISCOS ALTOS (Deve implementar antes de Produção)

### 🟠 RA-001: Logging Centralizado Ausente
**Severidade:** ALTO  
**Categoria:** Observabilidade - Auditoria  
**Descrição:**  
Logs são escritos apenas no servidor local (arquivo de texto ou stdout). Sem centralização, é impossível:
- Detectar ataques em tempo real
- Investigar incidentes post-mortem
- Alertar sobre erros críticos
- Auditar acesso a dados sensíveis

**Cenário de Risco:**
- Ataque acontece, logs estão no servidor comprometido
- Erro em produção, ninguém vê (sem agregação)
- Violação de LGPD (sem audit trail)
→ **Resultado:** Incidentes não detectados, conformidade violada

**Solução Recomendada:**
1. Implementar ELK (Elasticsearch-Logstash-Kibana) ou Graylog
2. Centralizar logs de Flask em JSON
3. Criar dashboards para alertas críticos
4. Retenção de 90 dias de logs
5. Alertar em Slack/email se erro > 5/min

**Custo:** 8-16 horas (setup inicial)  
**Prazo:** Antes de liberar para produção ampla  
**Responsável:** DevOps / Backend Engineer  
**Status:** ❌ NÃO INICIADO

---

### 🟠 RA-002: Headers HTTP de Segurança Ausentes
**Severidade:** ALTO  
**Categoria:** Segurança - Headers  
**Descrição:**  
Aplicação não envia headers HTTP que protegem contra ataques comuns:
- X-Frame-Options: falta → vulnerável a clickjacking
- X-Content-Type-Options: falta → vulnerável a MIME sniffing
- Content-Security-Policy: falta → XSS pode acontecer
- Strict-Transport-Security: falta → HTTPS pode ser downgrade

**Cenário de Risco:**
- Atacante embute iframe malicioso em página
- Navegador executa .exe como JavaScript
- XSS passa sem validação
- Usuário redireciona para HTTP (não HTTPS)
→ **Resultado:** Sessão comprometida, dados roubados

**Solução Recomendada:**
1. Adicionar em IIS web.config ou nginx.conf:
   - X-Frame-Options: DENY
   - X-Content-Type-Options: nosniff
   - X-XSS-Protection: 1; mode=block
   - Strict-Transport-Security: max-age=31536000
   - Content-Security-Policy: restritivo
2. Testar com curl -I

**Custo:** 2-3 horas  
**Prazo:** Antes de liberar para produção ampla  
**Responsável:** Deploy Engineer  
**Status:** ❌ NÃO INICIADO

---

### 🟠 RA-003: LGPD - Direito ao Esquecimento
**Severidade:** ALTO  
**Categoria:** Conformidade - LGPD  
**Descrição:**  
Lei geral de proteção de dados (LGPD) exige que usuário possa solicitar exclusão permanente de seus dados (direito ao esquecimento). Sistema não implementa isso.

**Cenário de Risco:**
- Usuário solicita delete de conta
- Empresa não consegue cumprir (dados ficam no banco)
- Usuário faz denúncia à ANPD
→ **Resultado:** Multa de até 2% do faturamento (muito alto)

**Solução Recomendada:**
1. Implementar rota DELETE /usuarios/<id>/delete-account
2. Deletar usuário da tabela `usuarios`
3. Anonimizar ativos criados por usuário (criar um pseudônimo como "DELETED_USER")
4. Documentar que backups levam 30 dias para expirar
5. Avisar usuário sobre delay de backup

**Custo:** 4-6 horas  
**Prazo:** Antes de liberar para produção ampla  
**Responsável:** Backend Engineer  
**Status:** ❌ NÃO INICIADO

---

## RISCOS MÉDIOS (Implementar em 30 dias)

### 🟡 RM-001: Status HTTP 422 Não Usado
**Severidade:** MÉDIO  
**Categoria:** UX - Código HTTP  
**Descrição:**  
Sistema retorna 400 Bad Request para erros de validação. Seria melhor usar 422 Unprocessable Entity (mais específico), facilitando debug no frontend.

**Impacto:**
- Frontend tem dificuldade diferenciando erro de sintaxe (400) vs validação (422)
- Menos semântico para consumidores da API

**Solução:**
1. Criar _json_error com status 422 para validação
2. Usar em rotas onde há validação de ativo
3. Manter 400 para erro de requisição (sintaxe)
4. Documentar em API spec

**Custo:** 1-2 horas  
**Prazo:** v1.1  
**Responsável:** Backend Engineer  
**Status:** ❌ NÃO INICIADO

---

### 🟡 RM-002: Token Refresh para Sessão Longa
**Severidade:** MÉDIO  
**Categoria:** Segurança - Sessão  
**Descrição:**  
Sessão tem timeout de 1 hora. Usuário que trabalha 2 horas é desconectado. Seria melhor implementar token refresh (extend sessão automaticamente se ativo).

**Solução:**
1. Implementar /session/refresh endpoint
2. Frontend chama refresh antes de expirar (55min)
3. Atualiza tempo de expiração na sessão
4. Mantém usuário conectado

**Custo:** 2-3 horas  
**Prazo:** v1.1 ou quando receber feedback de homologação  
**Responsável:** Backend Engineer  
**Status:** ❌ NÃO INICIADO

---

## RISCOS BAIXOS (Nice-to-Have)

### 🟢 RB-001: 2FA/MFA Não Implementado
**Severidade:** BAIXO  
**Categoria:** Segurança - Autenticação  
**Descrição:**  
Sistema não tem autenticação multi-fator. Recomendado se dados são muito sensíveis ou acesso de público.

**Solução:**
1. Integrar TOTP (Google Authenticator, Authy)
2. Ou SMS (mais caro, menos recomendado)
3. Fazer opcional no perfil de usuário

**Custo:** 4-6 horas  
**Prazo:** v1.1  
**Responsável:** Backend Engineer  
**Status:** ❌ NÃO INICIADO

---

### 🟢 RB-002: Auditoria Completa (Audit Trail)
**Severidade:** BAIXO  
**Categoria:** Conformidade - Auditoria  
**Descrição:**  
Sistema registra criação/edição de ativo, mas não mantém histórico completo (quem editou o quê, quando).

**Solução:**
1. Criar tabela `ativos_auditoria` com histórico
2. Registrar cada mudança (campo anterior → novo)
3. Quem fez (user_id)
4. Quando (timestamp)
5. Interface para visualizar histórico

**Custo:** 6-8 horas  
**Prazo:** v1.1  
**Responsável:** Backend Engineer  
**Status:** ❌ NÃO INICIADO

---

## RISCOS JÁ MITIGADOS ✅

| Risco | Antes | Ação | Depois |
|-------|-------|------|--------|
| Double-submit em novo ativo | 🔴 CRÍTICO | Botão desabilitado após clique | ✅ MITIGADO |
| CSRF em logout POST | 🟠 ALTO | Adicionar @require_csrf() | ✅ MITIGADO |
| CSRF em delete detalhe | 🔴 CRÍTICO | Enviar X-CSRF-Token | ✅ MITIGADO |
| Exception handling genérico | 🟡 MÉDIO | Usar StorageBackendError | ✅ MITIGADO |
| Filtro de localidade | 🟡 MÉDIO | Implementar em ativos.html | ✅ IMPLEMENTADO |

---

## MATRIZ DE RISCO

```
IMPACTO
   A  │  RC-001  │  RC-002  │  RA-001  │
   L  │ (Backup) │ (RateL)  │ (Logs)   │
   T  │          │          │  RA-002  │
   O  │          │          │  (Headers) │
      │          │          │  RA-003  │
   B  │          │          │ (LGPD)   │
   A  │          │          │          │
   I  │  RM-001  │  RM-002  │  RB-001  │  RB-002
   X  │  (422)   │  (Refr)  │  (2FA)   │  (Audit)
      └──────────┴──────────┴──────────┘
         BAIXA      MÉDIO       ALTA
                PROBABILIDADE
```

---

## MATRIZ DE AÇÃO

### Crítico (Fazer Agora)
```
[ ] RC-001: Configurar backup automático diário
[ ] RC-002: Implementar rate limiting em /login
```

### Alto (Fazer Antes de Produção)
```
[ ] RA-001: Implementar ELK/Graylog
[ ] RA-002: Adicionar headers HTTP em IIS/nginx
[ ] RA-003: Implementar direito ao esquecimento (delete account)
```

### Médio (Fazer em 30 Dias)
```
[ ] RM-001: Usar status 422 para validação
[ ] RM-002: Implementar token refresh
```

### Baixo (Considerar para v1.1)
```
[ ] RB-001: Implementar 2FA/MFA
[ ] RB-002: Implementar audit trail completo
```

---

## Assinatura

**Auditado por:** Sistema de Consolidação Técnica  
**Data:** 2026-04-16 14:25 UTC  
**Status:** ✅ Homologação Interna Aprovada / ⚠️ Produção Ampla com Pré-requisitos

**Próxima Revisão:** 2026-04-30 (feedback de Opus Medical e Vicente Martins)
