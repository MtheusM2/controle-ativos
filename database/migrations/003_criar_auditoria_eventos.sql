-- Migração 003: Criar tabela de auditoria para rastreabilidade de eventos críticos
-- Data: 2026-04-10
-- Escopo: Parte 2 — Auditoria e Rastreabilidade

USE controle_ativos;

-- =========================================================
-- TABELA: auditoria_eventos
-- Registra todos os eventos críticos do sistema para análise de segurança,
-- investigação de incidentes e conformidade LGPD.
-- =========================================================

CREATE TABLE IF NOT EXISTS auditoria_eventos (
    id INT NOT NULL AUTO_INCREMENT,

    -- Identificação do evento
    tipo_evento VARCHAR(50) NOT NULL,  -- ATIVO_CRIADO, LOGIN_SUCESSO, etc

    -- Contexto do usuário
    usuario_id INT NULL,               -- NULL para eventos antes de autenticação
    empresa_id INT NOT NULL,           -- Empresa onde ocorreu o evento

    -- Contexto técnico
    ip_origem VARCHAR(45) NULL,        -- IPv4 ou IPv6 do cliente
    user_agent VARCHAR(255) NULL,      -- Browser/client que iniciou ação

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

    -- Índices para queries comuns
    KEY idx_usuario_id (usuario_id),
    KEY idx_empresa_id (empresa_id),
    KEY idx_tipo_evento (tipo_evento),
    KEY idx_criado_em (criado_em),
    KEY idx_usuario_tipo (usuario_id, tipo_evento),
    KEY idx_empresa_tipo (empresa_id, tipo_evento),

    -- Foreign keys para integridade referencial
    CONSTRAINT fk_auditoria_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        ON DELETE SET NULL ON UPDATE CASCADE,

    CONSTRAINT fk_auditoria_empresa
        FOREIGN KEY (empresa_id) REFERENCES empresas (id)
        ON DELETE RESTRICT ON UPDATE CASCADE

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Descrição técnica:
-- - usuario_id é NULL para eventos que ocorrem antes de autenticação (login, recuperação)
-- - dados_antes/depois usam JSON para flexibilidade: suportam qualquer estrutura
-- - sucesso=1 para operações bem-sucedidas, sucesso=0 para falhas (ex: acesso negado)
-- - criado_em é imutável e rastreável
-- - Índices otimizam queries de: "quem fez o quê", "quando", "tipo de evento"
