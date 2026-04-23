-- =========================================================
-- MIGRAÇÃO 009: Auditoria de Importações (SIMPLIFICADA)
-- Data: 2026-04-22
-- Versão: Sem triggers, sem views, sem SUPER privilege
-- =========================================================

USE controle_ativos;

-- =========================================================
-- TABELA: auditoria_importacoes
-- =========================================================
CREATE TABLE IF NOT EXISTS auditoria_importacoes (
    id INT NOT NULL AUTO_INCREMENT,
    id_lote VARCHAR(50) NOT NULL UNIQUE,
    usuario_id INT NOT NULL,
    empresa_id INT NOT NULL,
    hash_arquivo VARCHAR(64) NOT NULL,
    nome_arquivo_original VARCHAR(255) NOT NULL,
    tamanho_arquivo_bytes INT,
    delimitador_csv CHAR(1),
    numero_linha_cabecalho INT DEFAULT 0,
    score_deteccao_cabecalho DECIMAL(3,2),
    total_linhas_arquivo INT NOT NULL,
    linhas_importadas INT DEFAULT 0,
    linhas_rejeitadas INT DEFAULT 0,
    linhas_com_aviso INT DEFAULT 0,
    linhas_atualizadas INT DEFAULT 0,
    status ENUM(
        'pendente',
        'preview_ok',
        'importando',
        'sucesso',
        'sucesso_parcial',
        'bloqueado',
        'erro',
        'revertido'
    ) NOT NULL DEFAULT 'pendente',
    mensagem_erro VARCHAR(1000),
    dados_bloqueios JSON,
    dados_avisos JSON,
    modo_duplicata ENUM('atualizar', 'ignorar', 'rejeitar') DEFAULT 'atualizar',
    endereco_ip VARCHAR(45),
    user_agent VARCHAR(500),
    timestamp_inicio TIMESTAMP NULL,
    timestamp_preview_gerado TIMESTAMP NULL,
    timestamp_confirmacao TIMESTAMP NULL,
    timestamp_conclusao TIMESTAMP NULL,
    timestamp_criacao TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    pode_reverter TINYINT(1) DEFAULT 1,
    reversao_em TIMESTAMP NULL,
    reversao_por INT NULL,
    reversao_motivo VARCHAR(500),
    ids_ativos_afetados JSON,

    PRIMARY KEY (id),
    UNIQUE KEY uk_auditoria_id_lote (id_lote),
    KEY idx_usuario_empresa (usuario_id, empresa_id),
    KEY idx_timestamp_conclusao (timestamp_conclusao),
    KEY idx_status (status),
    KEY idx_pode_reverter (pode_reverter),
    KEY idx_hash_arquivo (hash_arquivo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================================
-- TABELA: auditoria_importacoes_linhas
-- =========================================================
CREATE TABLE IF NOT EXISTS auditoria_importacoes_linhas (
    id INT NOT NULL AUTO_INCREMENT,
    id_lote VARCHAR(50) NOT NULL,
    numero_linha INT NOT NULL,
    status ENUM('importada', 'atualizada', 'rejeitada', 'aviso'),
    id_ativo_csv VARCHAR(20),
    id_ativo_criado VARCHAR(20),
    motivo_rejeicao VARCHAR(500),
    avisos JSON,
    campos_processados JSON,

    PRIMARY KEY (id),
    KEY idx_id_lote_numero (id_lote, numero_linha),
    KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================================
-- TABELA: ativos_log
-- =========================================================
CREATE TABLE IF NOT EXISTS ativos_log (
    id INT NOT NULL AUTO_INCREMENT,
    ativo_id VARCHAR(20) NOT NULL,
    empresa_id INT NOT NULL,
    operacao ENUM('INSERT', 'UPDATE', 'DELETE') NOT NULL,
    dados_antes JSON,
    dados_depois JSON,
    usuario_id INT NOT NULL,
    id_lote VARCHAR(50),
    motivo VARCHAR(500),
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY idx_ativo_id (ativo_id),
    KEY idx_empresa_id (empresa_id),
    KEY idx_timestamp (timestamp),
    KEY idx_id_lote (id_lote),
    KEY idx_operacao (operacao)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================================
-- FIM DA MIGRAÇÃO 009 (SIMPLIFICADA)
-- =========================================================

-- Status: 3 tabelas criadas, sem triggers/views/SUPER privilege
-- Funcionalidade: 100% (sem triggers automáticos, mas possibilidade de registrar manualmente)
