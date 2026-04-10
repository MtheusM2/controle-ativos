# Política de Retenção de Dados Pessoais

**Versão:** 1.0  
**Data:** 2026-04-10  
**Escopo:** Sistema Controle-Ativos  
**Responsável:** [TI/Ops]

---

## 1. Objetivo

Estabelecer política clara e simples de retenção de dados pessoais, alinhada com:
- Lei Geral de Proteção de Dados (LGPD)
- Segurança de TI
- Necessidades operacionais

---

## 2. Dados Pessoais e Períodos de Retenção

### 2.1 Dados de Usuário

| Dado | Tabela | Retenção | Condição |
|------|--------|----------|----------|
| **Nome** | usuarios | Enquanto ativo | Deletar 30 dias após desativação |
| **Email** | usuarios | Enquanto ativo | Deletar 30 dias após desativação |
| **Senha Hash** | usuarios | Permanente | Não aplicável (dado técnico) |
| **Pergunta Recuperação** | usuarios | Enquanto ativo | Deletar com usuário |
| **Resposta Recuperação Hash** | usuarios | Enquanto ativo | Deletar com usuário |

### 2.2 Logs de Auditoria

| Evento | Retenção | Exceções |
|--------|----------|----------|
| Criação/edição de ativo | 90 dias | Nenhuma |
| Login bem-sucedido | 90 dias | Nenhuma |
| **Login falha / Acesso negado** | **180 dias** | **Por segurança** |
| Upload/remoção de arquivo | 90 dias | Nenhuma |
| Operações administrativas | 180 dias | Por rastreabilidade |

**Justificativa:** 90 dias é suficiente para investigação de incidentes normais. Falhas de login/acesso negado requerem retenção maior por questões de segurança.

### 2.3 Tokens e Sessão

| Tipo | Retenção | Condição |
|------|----------|----------|
| **Token de reset de senha** | 24 horas | Expira automaticamente |
| **Token remember-me** | 180 dias | Deletado ao logout |
| **Sessão de login** | 2 horas | Conforme configuração (renovável) |
| **IP de acesso** (em logs) | Conforme log | Deletado com log de auditoria |

---

## 3. Procedimento de Limpeza Automática

### 3.1 Limpeza de Logs Antigos

**Frequência:** Mensalmente (último dia do mês)

**Script:** `scripts/limpar_auditoria_automatico.ps1`

```powershell
# Executar via Task Scheduler no último dia de cada mês

$data_limite_90dias = (Get-Date).AddDays(-90)
$data_limite_180dias = (Get-Date).AddDays(-180)

# Deleta logs normais com > 90 dias
mysql -u opus_app -p$env:DB_PASSWORD controle_ativos -e "
DELETE FROM auditoria_eventos
WHERE criado_em < '$data_limite_90dias'
  AND tipo_evento NOT IN ('LOGIN_FALHA', 'ACESSO_NEGADO', 'USUARIO_PROMOVIDO');
"

# Deleta logs de segurança com > 180 dias
mysql -u opus_app -p$env:DB_PASSWORD controle_ativos -e "
DELETE FROM auditoria_eventos
WHERE criado_em < '$data_limite_180dias'
  AND tipo_evento IN ('LOGIN_FALHA', 'ACESSO_NEGADO');
"

# Registra execução
$timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
Add-Content "C:\controle_ativos\logs\limpeza_auditoria.log" `
    "$timestamp : Limpeza executada com sucesso"
```

### 3.2 Limpeza de Usuários Desativados

**Frequência:** Trimestralmente (ou sob demanda)

**Procedimento Manual:**
1. Identificar usuários inativos há mais de 30 dias
2. Confirmar com gestor de RH
3. Executar `DELETE FROM usuarios WHERE id = ? AND empresa_id = ?`
4. Logs de auditoria do usuário não são deletados (rastreabilidade)

---

## 4. Exclusões Especiais

### 4.1 Retenção Estendida

Manter logs por período **maior** se:
- Investigação de incidente de segurança ativa
- Litígio ou processo trabalhista pendente
- Solicitação de autoridade governamental

**Responsável:** Gestor de TI + Jurídico (se aplicável)

### 4.2 Exclusão Sob Demanda

Usuário pode solicitar exclusão de dados via direito de portabilidade LGPD.

**Procedimento:**
1. Usuário envia email ao responsável de dados
2. TI valida identidade
3. Se aprovado: executar limpeza sob demanda
4. Exceção: Manter logs de auditoria (não identificam pessoa)

---

## 5. Backup e Recuperação

### 5.1 Dados em Backup

Backups **contêm** dados pessoais (necessário para recuperação).

**Política:**
- Backups retirados de produção após 30 dias
- Deletados após 6 meses
- Criptografados em armazenamento

### 5.2 Recuperação de Backup

Se necessário recuperar de backup antigo:
1. Restaura dados até o ponto de backup
2. Executar limpeza novamente para conformidade

**Exemplo:** Backup de janeiro contém logs até janeiro. Se restaurar em abril, deletar logs > 90 dias novamente.

---

## 6. Relatório de Retenção

### 6.1 Auditoria Trimestral

**Responsável:** Gestor de TI

**Verificar:**
- [ ] Limpeza automática executou corretamente
- [ ] Total de registros em auditoria_eventos
- [ ] Data do registro mais antigo
- [ ] Nenhum usuário ativo foi deletado por engano

**Relatório:** Enviar para [Responsável de Dados] até fim do trimestre.

### 6.2 Metricas

```sql
-- Executar trimestral
SELECT 
    COUNT(*) as total_eventos,
    MIN(criado_em) as registro_mais_antigo,
    MAX(criado_em) as registro_mais_recente,
    COUNT(DISTINCT usuario_id) as usuarios_distintos
FROM auditoria_eventos;
```

---

## 7. Conformidade LGPD

### 7.1 Verificações

- ✅ Dados são retidos apenas pelo tempo necessário
- ✅ Usuários podem solicitar acesso/exclusão
- ✅ Exclusão é executada em até 10 dias úteis
- ✅ Logs de auditoria permitem rastreabilidade
- ✅ Backup é retido de forma segura

### 7.2 Documento Obrigatório

Esta política **deve ser:**
- Compartilhada com usuários (parte do onboarding)
- Revida anualmente (ou conforme mudanças)
- Armazenada junto com aviso de privacidade

---

## 8. Responsabilidades

| Função | Responsabilidade |
|--------|-----------------|
| **Gestor de TI** | Executar limpeza automática e sob demanda |
| **Responsável Dados** | Revisar conformidade, atender requisições |
| **Compliance/Jurídico** | Revisar anualmente, validar adequação |

---

## 9. Revisão e Atualização

- **Primeira revisão:** 2026-10-10 (6 meses)
- **Revisão anual:** 2027-04-10
- **Próxima revisão:** Conforme mudanças legais ou operacionais

---

**Versão:** 1.0  
**Data da última revisão:** 2026-04-10  
**Próxima revisão:** 2026-10-10
