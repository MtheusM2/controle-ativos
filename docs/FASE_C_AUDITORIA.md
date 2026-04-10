# FASE C — Auditoria e Rastreabilidade (Parte 2)

**Data:** 2026-04-10  
**Status:** Design + Implementação Inicial  
**Prioridade:** Alta

---

## 1. Objetivo

Implementar mecanismo de rastreabilidade para eventos críticos do sistema, permitindo:
- Rastreamento completo de quem fez o quê, quando
- Análise de incidentes de segurança
- Conformidade com LGPD (direito à auditoria)
- Homologação corporativa (rastreamento obrigatório)

---

## 2. Eventos Críticos Mapeados

### 2.1 Eventos de Ativo

| Evento | Gatilho | Dados Essenciais | Risco |
|--------|---------|------------------|-------|
| ATIVO_CRIADO | POST /ativos | ID, tipo, empresa, usuário_criador | Médio |
| ATIVO_EDITADO | PUT /ativos/<id> | ID, campos alterados, antes/depois, usuário | Alto |
| ATIVO_REMOVIDO | DELETE /ativos/<id> | ID, empresa, usuário | Alto |
| ATIVO_INATIVADO | PATCH status | ID, status anterior/novo, usuário | Médio |

### 2.2 Eventos de Arquivo

| Evento | Gatilho | Dados Essenciais | Risco |
|--------|---------|------------------|-------|
| ARQUIVO_ENVIADO | POST /ativos/<id>/anexos | arquivo_id, ativo_id, usuário, tipo, tamanho | Médio |
| ARQUIVO_REMOVIDO | DELETE /anexos/<id> | arquivo_id, ativo_id, usuário | Médio |
| ARQUIVO_BAIXADO | GET /anexos/<id>/download | arquivo_id, usuário, IP | Baixo |

### 2.3 Eventos de Acesso

| Evento | Gatilho | Dados Essenciais | Risco |
|--------|---------|------------------|-------|
| LOGIN_SUCESSO | POST /login | usuário, IP, hora | Médio |
| LOGIN_FALHA | POST /login (falha) | email tentado, razão, IP | Médio |
| LOGOUT | GET/POST /logout | usuário, hora | Baixo |
| SESSAO_EXPIRADA | Validação | usuário, hora | Baixo |

### 2.4 Eventos de Permissão

| Evento | Gatilho | Dados Essenciais | Risco |
|--------|---------|------------------|-------|
| ACESSO_NEGADO | Validação de permissão | usuário, ação tentada, razão | Baixo |
| USUARIO_PROMOVIDO | Admin action | usuário promovido, perfil novo, por quem | Alto |
| USUARIO_BLOQUEADO | Falhas de login | usuário, razão, até quando | Médio |

### 2.5 Eventos de Exportação

| Evento | Gatilho | Dados Essenciais | Risco |
|--------|---------|------------------|-------|
| EXPORTACAO_REALIZADA | GET /ativos/export/* | formato, usuário, quantidade de registros | Médio |
| IMPORTACAO_REALIZADA | POST /ativos/import/* | usuário, quantidade inserida, quantidade erros | Alto |

---

## 3. Estrutura de Dados

### 3.1 Schema Proposto

```sql
CREATE TABLE auditoria_eventos (
    id INT NOT NULL AUTO_INCREMENT,
    -- Identificação do evento
    tipo_evento VARCHAR(50) NOT NULL,  -- ATIVO_CRIADO, LOGIN_SUCESSO, etc
    -- Contexto do usuário
    usuario_id INT NULL,               -- NULL para eventos antes de autenticação
    empresa_id INT NOT NULL,           -- Empresa onde ocorreu
    -- Contexto técnico
    ip_origem VARCHAR(45) NULL,        -- IPv4 ou IPv6
    user_agent VARCHAR(255) NULL,      -- Browser/client
    -- Detalhes do evento
    dados_antes JSON NULL,             -- Estado anterior (para edições)
    dados_depois JSON NULL,            -- Estado novo (para edições)
    mensagem TEXT NULL,                -- Descrição legível do evento
    -- Metadados de sucesso/falha
    sucesso TINYINT(1) NOT NULL DEFAULT 1,
    motivo_falha VARCHAR(255) NULL,    -- Por que falhou (se aplicável)
    -- Rastreabilidade
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_usuario_id (usuario_id),
    KEY idx_empresa_id (empresa_id),
    KEY idx_tipo_evento (tipo_evento),
    KEY idx_criado_em (criado_em),
    KEY idx_usuario_tipo (usuario_id, tipo_evento),
    CONSTRAINT fk_auditoria_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_auditoria_empresa
        FOREIGN KEY (empresa_id) REFERENCES empresas (id)
        ON DELETE RESTRICT ON UPDATE CASCADE
);
```

### 3.2 Estrutura de Dados JSON

#### Evento de Criação de Ativo
```json
{
  "id_ativo": "OPU-001",
  "tipo": "Notebook",
  "marca": "Dell",
  "empresa_id": 1
}
```

#### Evento de Edição de Ativo
```json
{
  "ativo_id": "OPU-001",
  "campo_alterado": "status",
  "valor_anterior": "Em Uso",
  "valor_novo": "Inativo"
}
```

#### Evento de Login
```json
{
  "usuario_id": 5,
  "email": "usuario@empresa.com",
  "sucesso": true
}
```

---

## 4. Implementação Inicial (Sprint 2.1)

### 4.1 Criar Tabela de Auditoria

**Arquivo:** `database/migrations/003_criar_auditoria_eventos.sql`

```sql
USE controle_ativos;

CREATE TABLE IF NOT EXISTS auditoria_eventos (
    id INT NOT NULL AUTO_INCREMENT,
    tipo_evento VARCHAR(50) NOT NULL,
    usuario_id INT NULL,
    empresa_id INT NOT NULL,
    ip_origem VARCHAR(45) NULL,
    user_agent VARCHAR(255) NULL,
    dados_antes JSON NULL,
    dados_depois JSON NULL,
    mensagem TEXT NULL,
    sucesso TINYINT(1) NOT NULL DEFAULT 1,
    motivo_falha VARCHAR(255) NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_usuario_id (usuario_id),
    KEY idx_empresa_id (empresa_id),
    KEY idx_tipo_evento (tipo_evento),
    KEY idx_criado_em (criado_em),
    KEY idx_usuario_tipo (usuario_id, tipo_evento),
    CONSTRAINT fk_auditoria_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_auditoria_empresa
        FOREIGN KEY (empresa_id) REFERENCES empresas (id)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### 4.2 Service de Auditoria

**Arquivo:** `services/auditoria_service.py`

```python
from database.connection import cursor_mysql
from datetime import datetime
import json

class AuditoriaService:
    """Serviço responsável por registrar eventos de auditoria."""

    @staticmethod
    def registrar_evento(
        tipo_evento: str,
        usuario_id: int | None,
        empresa_id: int,
        mensagem: str = None,
        dados_antes: dict = None,
        dados_depois: dict = None,
        ip_origem: str = None,
        user_agent: str = None,
        sucesso: bool = True,
        motivo_falha: str = None
    ) -> int:
        """
        Registra um evento de auditoria.

        Args:
            tipo_evento: tipo de evento (ex: ATIVO_CRIADO)
            usuario_id: ID do usuário (None antes de autenticação)
            empresa_id: ID da empresa onde ocorreu
            mensagem: descrição legível
            dados_antes: estado anterior (JSON)
            dados_depois: estado novo (JSON)
            ip_origem: IP do cliente
            user_agent: navegador/cliente
            sucesso: se a operação foi bem-sucedida
            motivo_falha: razão da falha (se houver)

        Returns:
            ID do evento registrado
        """
        with cursor_mysql(dictionary=True) as (_conn, cur):
            cur.execute(
                """
                INSERT INTO auditoria_eventos (
                    tipo_evento,
                    usuario_id,
                    empresa_id,
                    ip_origem,
                    user_agent,
                    dados_antes,
                    dados_depois,
                    mensagem,
                    sucesso,
                    motivo_falha
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    tipo_evento,
                    usuario_id,
                    empresa_id,
                    ip_origem,
                    user_agent,
                    json.dumps(dados_antes) if dados_antes else None,
                    json.dumps(dados_depois) if dados_depois else None,
                    mensagem,
                    1 if sucesso else 0,
                    motivo_falha
                )
            )

        return cur.lastrowid

    @staticmethod
    def listar_eventos(
        empresa_id: int,
        tipo_evento: str = None,
        usuario_id: int = None,
        limite: int = 100,
        offset: int = 0
    ) -> list[dict]:
        """
        Lista eventos de auditoria (apenas admin pode acessar).
        """
        with cursor_mysql(dictionary=True) as (_conn, cur):
            where_clauses = ["empresa_id = %s"]
            params = [empresa_id]

            if tipo_evento:
                where_clauses.append("tipo_evento = %s")
                params.append(tipo_evento)

            if usuario_id:
                where_clauses.append("usuario_id = %s")
                params.append(usuario_id)

            where_sql = " AND ".join(where_clauses)

            cur.execute(
                f"""
                SELECT * FROM auditoria_eventos
                WHERE {where_sql}
                ORDER BY criado_em DESC
                LIMIT %s OFFSET %s
                """,
                params + [limite, offset]
            )

            return cur.fetchall() or []
```

### 4.3 Integração em Services Críticos

**Localização:** Adicionar chamadas em services

```python
# Em ativos_service.py - criar_ativo()
from services.auditoria_service import AuditoriaService

def criar_ativo(self, ativo: Ativo, user_id: int) -> str:
    # ... lógica existente ...
    
    # Registra na auditoria
    AuditoriaService.registrar_evento(
        tipo_evento="ATIVO_CRIADO",
        usuario_id=user_id,
        empresa_id=empresa_id,
        mensagem=f"Ativo {id_gerado} criado",
        dados_depois={"id": id_gerado, "tipo": ativo.tipo}
    )
    
    return id_gerado
```

### 4.4 Suporte em Flask

**Localização:** `utils/auditoria_helpers.py`

```python
from flask import request

def obter_ip_cliente() -> str:
    """Obtém IP do cliente (com suporte a proxy)."""
    if request.headers.get('X-Forwarded-For'):
        return request.headers['X-Forwarded-For'].split(',')[0].strip()
    return request.remote_addr or "unknown"

def obter_user_agent() -> str:
    """Obtém user agent do cliente."""
    return request.headers.get('User-Agent', 'unknown')[:255]
```

---

## 5. O Que Será Implementado Nesta Sprint

✅ Tabela `auditoria_eventos`  
✅ Service `AuditoriaService` com métodos básicos  
✅ Integração em eventos críticos (criar ativo, remover ativo)  
✅ Helpers para captura de IP e User-Agent  
✅ Query de listagem de eventos (protegida por admin)  

⏸️ Visualização web de auditoria (fica para Sprint 2.2)  
⏸️ Exportação de auditoria (fica para Sprint 2.2)  
⏸️ Alertas em tempo real (fica para Sprint 2.3+)  

---

## 6. Tipos de Eventos Suportados Inicialmente

```python
class TiposEvento:
    # Ativos
    ATIVO_CRIADO = "ATIVO_CRIADO"
    ATIVO_EDITADO = "ATIVO_EDITADO"
    ATIVO_REMOVIDO = "ATIVO_REMOVIDO"
    ATIVO_INATIVADO = "ATIVO_INATIVADO"
    
    # Arquivos
    ARQUIVO_ENVIADO = "ARQUIVO_ENVIADO"
    ARQUIVO_REMOVIDO = "ARQUIVO_REMOVIDO"
    ARQUIVO_BAIXADO = "ARQUIVO_BAIXADO"
    
    # Acesso
    LOGIN_SUCESSO = "LOGIN_SUCESSO"
    LOGIN_FALHA = "LOGIN_FALHA"
    LOGOUT = "LOGOUT"
    
    # Permissões
    ACESSO_NEGADO = "ACESSO_NEGADO"
    USUARIO_PROMOVIDO = "USUARIO_PROMOVIDO"
```

---

## 7. Exemplos de Uso

### Registrar criação de ativo

```python
AuditoriaService.registrar_evento(
    tipo_evento="ATIVO_CRIADO",
    usuario_id=user_id,
    empresa_id=empresa_id,
    mensagem="Notebook Dell criado",
    dados_depois={"id": "OPU-001", "tipo": "Notebook"},
    ip_origem="192.168.1.100"
)
```

### Registrar falha de acesso

```python
AuditoriaService.registrar_evento(
    tipo_evento="ACESSO_NEGADO",
    usuario_id=user_id,
    empresa_id=empresa_id,
    mensagem="Tentativa de remover ativo de outra empresa",
    sucesso=False,
    motivo_falha="Perfil 'consulta' não tem permissão"
)
```

### Listar eventos

```python
eventos = AuditoriaService.listar_eventos(
    empresa_id=1,
    tipo_evento="ATIVO_REMOVIDO"
)
```

---

## 8. Benefícios

| Aspecto | Benefício |
|---------|-----------|
| **Segurança** | Rastreamento completo de ações críticas |
| **Compliance** | Atende LGPD (direito à auditoria) |
| **Investigação** | Facilita identificação de incidentes |
| **Homologação** | Demonstra que sistema é auditável |
| **Confiança** | Transparência para usuários finais |

---

## 9. Impactos em Performance

| Aspecto | Estimativa |
|---------|-----------|
| Inserção de log | +1-2ms por requisição |
| Leitura de logs | O(1) com índices |
| Crescimento DB | ~500 bytes por evento |
| Retenção | 90 dias (manutenção mensal) |

**Conclusão:** Impacto negligenciável.

---

## 10. Próximos Passos

### Sprint 2.1
- [ ] Criar migração da tabela
- [ ] Implementar AuditoriaService
- [ ] Adicionar registros em ativos_service
- [ ] Testes básicos de auditoria
- [ ] Documentação

### Sprint 2.2
- [ ] Rota de listagem de auditoria (protegida por admin)
- [ ] Template web para visualização
- [ ] Filtros avançados
- [ ] Exportação de relatório de auditoria

### Sprint 2.3+
- [ ] Alertas em tempo real (anomalias)
- [ ] Dashboard de segurança
- [ ] Retenção automática de logs

---

## 11. Veredito Técnico

✅ **Design de auditoria é viável e escalável.**

Abordagem proposta:
- Tabela simples com índices estratégicos
- JSON para flexibilidade de dados
- Service centralizado para facilitar manutenção
- Sem impacto em performance

Pode ser expandida facilmente sem quebra retroativa.

---

**Responsável:** Claude Code  
**Data:** 2026-04-10  
**Versão:** 1.0
