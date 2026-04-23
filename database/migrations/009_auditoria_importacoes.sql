-- =========================================================
-- MIGRAÇÃO 009: Auditoria de Importações
-- Data: 2026-04-22
-- Objetivo: Criar infraestrutura de rastreabilidade para
--           importações em lote com suporte a reversão
-- =========================================================

USE controle_ativos;

-- =========================================================
-- TABELA: auditoria_importacoes
-- Rastreia cada importação: quem, quando, o quê, resultado
-- =========================================================
CREATE TABLE IF NOT EXISTS auditoria_importacoes (
    id INT NOT NULL AUTO_INCREMENT,

    -- Identificação da importação (chave única para rastreabilidade)
    id_lote VARCHAR(50) NOT NULL UNIQUE,

    -- Quem importou
    usuario_id INT NOT NULL,
    empresa_id INT NOT NULL,

    -- Metadados do arquivo
    hash_arquivo VARCHAR(64) NOT NULL,                    -- SHA256 do CSV
    nome_arquivo_original VARCHAR(255) NOT NULL,
    tamanho_arquivo_bytes INT,

    -- Detecção de cabeçalho
    delimitador_csv CHAR(1),                             -- ',' ou ';'
    numero_linha_cabecalho INT DEFAULT 0,
    score_deteccao_cabecalho DECIMAL(3,2),               -- 0.00 a 1.00

    -- Contagem de linhas
    total_linhas_arquivo INT NOT NULL,
    linhas_importadas INT DEFAULT 0,
    linhas_rejeitadas INT DEFAULT 0,
    linhas_com_aviso INT DEFAULT 0,
    linhas_atualizadas INT DEFAULT 0,

    -- Status da importação
    status ENUM(
        'pendente',           -- Upload recebido, preview pendente
        'preview_ok',         -- Preview gerado, aguardando confirmação
        'importando',         -- Processamento em andamento
        'sucesso',            -- Importação completa, sem erros
        'sucesso_parcial',    -- Algumas linhas rejeitadas
        'bloqueado',          -- Bloqueado (campo crítico faltando, etc)
        'erro',               -- Erro durante processamento
        'revertido'           -- Admin reverteu a importação
    ) NOT NULL DEFAULT 'pendente',

    -- Detalhes de erro (se bloqueado ou erro)
    mensagem_erro VARCHAR(1000),

    -- Bloqueios identificados (JSON array)
    dados_bloqueios JSON,

    -- Avisos identificados (JSON array com contagem por tipo)
    dados_avisos JSON,

    -- Configuração de importação
    modo_duplicata ENUM('atualizar', 'ignorar', 'rejeitar')
        DEFAULT 'atualizar',

    -- Rastreabilidade de acesso
    endereco_ip VARCHAR(45),                             -- IPv4 ou IPv6
    user_agent VARCHAR(500),                             -- Browser info

    -- Timeline de eventos
    timestamp_inicio TIMESTAMP NULL,                     -- Quando iniciou upload
    timestamp_preview_gerado TIMESTAMP NULL,
    timestamp_confirmacao TIMESTAMP NULL,                -- Quando usuário confirmou
    timestamp_conclusao TIMESTAMP NULL,                  -- Quando importação terminou
    timestamp_criacao TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Reversão (admin pode reverter até 7 dias)
    pode_reverter TINYINT(1) DEFAULT 1,
    dias_reverter_restantes INT GENERATED ALWAYS AS (
        DATEDIFF(DATE_ADD(timestamp_conclusao, INTERVAL 7 DAY), CURDATE())
    ) STORED,
    reversao_em TIMESTAMP NULL,
    reversao_por INT NULL,                              -- Quem reverteu
    reversao_motivo VARCHAR(500),

    -- Lista de IDs afetados (para rollback seguro)
    ids_ativos_afetados JSON,                           -- ["NTB-001", "NTB-002", ...]

    PRIMARY KEY (id),
    UNIQUE KEY uk_auditoria_id_lote (id_lote),
    KEY idx_usuario_empresa (usuario_id, empresa_id),
    KEY idx_timestamp_conclusao (timestamp_conclusao),
    KEY idx_status (status),
    KEY idx_pode_reverter (pode_reverter),
    KEY idx_hash_arquivo (hash_arquivo),

    CONSTRAINT fk_auditoria_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT fk_auditoria_empresa
        FOREIGN KEY (empresa_id) REFERENCES empresas(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT fk_auditoria_revertido_por
        FOREIGN KEY (reversao_por) REFERENCES usuarios(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================================
-- TABELA: auditoria_importacoes_linhas
-- Detalha erros/avisos por linha para troubleshooting
-- =========================================================
CREATE TABLE IF NOT EXISTS auditoria_importacoes_linhas (
    id INT NOT NULL AUTO_INCREMENT,

    -- Referência à importação
    id_lote VARCHAR(50) NOT NULL,
    numero_linha INT NOT NULL,                          -- Linha no arquivo original

    -- Resultado desta linha
    status ENUM('importada', 'atualizada', 'rejeitada', 'aviso'),

    -- Dados da linha
    id_ativo_csv VARCHAR(20),                           -- ID extraído do CSV
    id_ativo_criado VARCHAR(20),                        -- ID criado (pode diferir)

    -- Se rejeitada, por que?
    motivo_rejeicao VARCHAR(500),

    -- Avisos (JSON array)
    avisos JSON,

    -- Valores detectados (para debug)
    campos_processados JSON,                            -- {"id": "NTB-001", "tipo": "Notebook", ...}

    PRIMARY KEY (id),
    KEY idx_id_lote_numero (id_lote, numero_linha),
    KEY idx_status (status),

    CONSTRAINT fk_linhas_lote
        FOREIGN KEY (id_lote) REFERENCES auditoria_importacoes(id_lote)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================================
-- TABELA: ativos_log
-- Auditoria de todas as mudanças em ativos (INSERT/UPDATE/DELETE)
-- Usada para rastreabilidade e análise de divergências
-- =========================================================
CREATE TABLE IF NOT EXISTS ativos_log (
    id INT NOT NULL AUTO_INCREMENT,

    -- Qual ativo foi afetado
    ativo_id VARCHAR(20) NOT NULL,
    empresa_id INT NOT NULL,

    -- Que operação foi feita
    operacao ENUM('INSERT', 'UPDATE', 'DELETE') NOT NULL,

    -- Estado antes e depois
    dados_antes JSON,                                   -- NULL para INSERT
    dados_depois JSON,                                  -- NULL para DELETE

    -- Quem fez (e porque)
    usuario_id INT NOT NULL,
    id_lote VARCHAR(50),                                -- Se foi via importação
    motivo VARCHAR(500),

    -- Timeline
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY idx_ativo_id (ativo_id),
    KEY idx_empresa_id (empresa_id),
    KEY idx_timestamp (timestamp),
    KEY idx_id_lote (id_lote),
    KEY idx_operacao (operacao),

    CONSTRAINT fk_log_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT fk_log_empresa
        FOREIGN KEY (empresa_id) REFERENCES empresas(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT fk_log_lote
        FOREIGN KEY (id_lote) REFERENCES auditoria_importacoes(id_lote)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================================
-- TRIGGERS: Logging automático de mudanças em ativos
-- =========================================================

DELIMITER $$

-- Trigger: Log de INSERT
CREATE TRIGGER trg_ativos_log_insert
AFTER INSERT ON ativos
FOR EACH ROW
BEGIN
    INSERT INTO ativos_log (
        ativo_id, empresa_id, operacao, dados_antes, dados_depois,
        usuario_id, id_lote, timestamp
    ) VALUES (
        NEW.id,
        NEW.empresa_id,
        'INSERT',
        NULL,
        JSON_OBJECT(
            'id', NEW.id,
            'tipo', NEW.tipo,
            'marca', NEW.marca,
            'modelo', NEW.modelo,
            'serial', NEW.serial,
            'status', NEW.status,
            'usuario_responsavel', NEW.usuario_responsavel,
            'departamento', NEW.departamento,
            'data_entrada', NEW.data_entrada,
            'valor', NEW.valor
        ),
        COALESCE(@usuario_id, NEW.criado_por),
        @id_lote,
        NOW()
    );
END$$

-- Trigger: Log de UPDATE
CREATE TRIGGER trg_ativos_log_update
AFTER UPDATE ON ativos
FOR EACH ROW
BEGIN
    INSERT INTO ativos_log (
        ativo_id, empresa_id, operacao, dados_antes, dados_depois,
        usuario_id, id_lote, timestamp
    ) VALUES (
        NEW.id,
        NEW.empresa_id,
        'UPDATE',
        JSON_OBJECT(
            'tipo', OLD.tipo,
            'marca', OLD.marca,
            'modelo', OLD.modelo,
            'serial', OLD.serial,
            'status', OLD.status,
            'usuario_responsavel', OLD.usuario_responsavel,
            'departamento', OLD.departamento,
            'valor', OLD.valor
        ),
        JSON_OBJECT(
            'tipo', NEW.tipo,
            'marca', NEW.marca,
            'modelo', NEW.modelo,
            'serial', NEW.serial,
            'status', NEW.status,
            'usuario_responsavel', NEW.usuario_responsavel,
            'departamento', NEW.departamento,
            'valor', NEW.valor
        ),
        COALESCE(@usuario_id, NEW.criado_por),
        @id_lote,
        NOW()
    );
END$$

-- Trigger: Log de DELETE
CREATE TRIGGER trg_ativos_log_delete
AFTER DELETE ON ativos
FOR EACH ROW
BEGIN
    INSERT INTO ativos_log (
        ativo_id, empresa_id, operacao, dados_antes, dados_depois,
        usuario_id, id_lote, timestamp
    ) VALUES (
        OLD.id,
        OLD.empresa_id,
        'DELETE',
        JSON_OBJECT(
            'id', OLD.id,
            'tipo', OLD.tipo,
            'marca', OLD.marca,
            'modelo', OLD.modelo,
            'serial', OLD.serial,
            'status', OLD.status,
            'usuario_responsavel', OLD.usuario_responsavel,
            'departamento', OLD.departamento
        ),
        NULL,
        COALESCE(@usuario_id, OLD.criado_por),
        @id_lote,
        NOW()
    );
END$$

DELIMITER ;

-- =========================================================
-- VIEW: Resumo de Importações por Usuário
-- =========================================================
CREATE OR REPLACE VIEW vw_resumo_importacoes_usuario AS
SELECT
    u.id,
    u.nome,
    u.email,
    COUNT(*) as total_importacoes,
    SUM(CASE WHEN status IN ('sucesso', 'sucesso_parcial') THEN 1 ELSE 0 END) as importacoes_ok,
    SUM(CASE WHEN status = 'bloqueado' THEN 1 ELSE 0 END) as bloqueadas,
    SUM(CASE WHEN status = 'erro' THEN 1 ELSE 0 END) as com_erro,
    SUM(linhas_importadas) as total_linhas_importadas,
    MAX(timestamp_conclusao) as ultima_importacao
FROM auditoria_importacoes ai
JOIN usuarios u ON ai.usuario_id = u.id
WHERE ai.status != 'pendente'
GROUP BY u.id, u.nome, u.email;

-- =========================================================
-- VIEW: Importações Reversíveis (< 7 dias)
-- =========================================================
CREATE OR REPLACE VIEW vw_importacoes_reversaveis AS
SELECT
    id_lote,
    usuario_id,
    empresa_id,
    timestamp_conclusao,
    status,
    total_linhas_arquivo,
    linhas_importadas,
    dias_reverter_restantes,
    pode_reverter,
    CASE
        WHEN dias_reverter_restantes <= 0 THEN 'Expirada'
        WHEN dias_reverter_restantes <= 1 THEN 'Expira em <24h'
        ELSE CONCAT('Expira em ', dias_reverter_restantes, ' dias')
    END as prazo_reversao
FROM auditoria_importacoes
WHERE status IN ('sucesso', 'sucesso_parcial')
    AND pode_reverter = 1
    AND timestamp_conclusao IS NOT NULL;

-- =========================================================
-- Fim da Migração 009
-- =========================================================
