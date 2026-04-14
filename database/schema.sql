-- =========================================================
-- SCHEMA OFICIAL DO PROJETO controle_ativos
-- Este arquivo recria a estrutura principal do banco.
-- =========================================================

-- Cria o banco, caso ainda não exista.
CREATE DATABASE IF NOT EXISTS controle_ativos
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

-- Define o banco em uso.
USE controle_ativos;

-- =========================================================
-- TABELA: empresas
-- Armazena as empresas cadastradas no sistema.
-- =========================================================
CREATE TABLE IF NOT EXISTS empresas (
    id INT NOT NULL AUTO_INCREMENT,
    nome VARCHAR(150) NOT NULL,
    codigo VARCHAR(50) NOT NULL,
    prefixo_ativo VARCHAR(10) NULL,
    ativa TINYINT(1) NOT NULL DEFAULT 1,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_empresas_nome (nome),
    UNIQUE KEY uk_empresas_codigo (codigo)
);

-- =========================================================
-- TABELA: usuarios
-- Armazena usuários com vínculo organizacional.
-- =========================================================
CREATE TABLE IF NOT EXISTS usuarios (
    id INT NOT NULL AUTO_INCREMENT,
    nome VARCHAR(120) NOT NULL,
    email VARCHAR(255) NOT NULL,
    senha_hash VARCHAR(512) NOT NULL,
    pergunta_recuperacao VARCHAR(255) NOT NULL,
    resposta_recuperacao_hash VARCHAR(512) NOT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    ultimo_login_em TIMESTAMP NULL DEFAULT NULL,
    senha_alterada_em TIMESTAMP NULL DEFAULT NULL,
    tentativas_login_falhas INT NOT NULL DEFAULT 0,
    bloqueado_ate TIMESTAMP NULL DEFAULT NULL,
    reset_token_hash VARCHAR(512) NULL,
    reset_token_expira_em TIMESTAMP NULL DEFAULT NULL,
    reset_token_usado_em TIMESTAMP NULL DEFAULT NULL,
    perfil VARCHAR(20) NOT NULL DEFAULT 'usuario',
    empresa_id INT NOT NULL,
    lembrar_me_ativo TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE KEY uk_usuarios_email (email),
    KEY idx_usuarios_perfil (perfil),
    KEY idx_usuarios_empresa_id (empresa_id),
    KEY idx_usuarios_reset_expira_em (reset_token_expira_em),
    CONSTRAINT fk_usuarios_empresa
        FOREIGN KEY (empresa_id)
        REFERENCES empresas (id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
);

-- =========================================================
-- TABELA: ativos
-- Armazena ativos vinculados a empresa e usuário criador.
-- O responsável é opcional, exceto pela regra de negócio
-- quando o status for 'Em Uso', validada na aplicação.
-- =========================================================
CREATE TABLE IF NOT EXISTS ativos (
    id VARCHAR(20) NOT NULL,
    codigo_interno VARCHAR(50) NULL,
    tipo VARCHAR(100) NOT NULL,
    marca VARCHAR(100) NOT NULL,
    modelo VARCHAR(100) NOT NULL,
    serial VARCHAR(120) NULL,
    descricao VARCHAR(255) NULL,
    categoria VARCHAR(100) NULL,
    tipo_ativo VARCHAR(50) NULL,
    condicao VARCHAR(50) NULL,
    localizacao VARCHAR(120) NULL,
    setor VARCHAR(100) NULL,
    usuario_responsavel VARCHAR(100) NULL,
    email_responsavel VARCHAR(255) NULL,
    departamento VARCHAR(100) NOT NULL,
    nota_fiscal VARCHAR(100) NULL,
    garantia VARCHAR(100) NULL,
    status VARCHAR(50) NOT NULL,
    data_entrada DATE NOT NULL,
    data_saida DATE NULL,
    data_compra DATE NULL,
    valor DECIMAL(12,2) NULL,
    observacoes TEXT NULL,
    detalhes_tecnicos VARCHAR(255) NULL,
    processador VARCHAR(120) NULL,
    ram VARCHAR(60) NULL,
    armazenamento VARCHAR(120) NULL,
    sistema_operacional VARCHAR(120) NULL,
    carregador VARCHAR(120) NULL,
    teamviewer_id VARCHAR(100) NULL,
    anydesk_id VARCHAR(100) NULL,
    nome_equipamento VARCHAR(120) NULL,
    hostname VARCHAR(120) NULL,
    imei_1 VARCHAR(40) NULL,
    imei_2 VARCHAR(40) NULL,
    numero_linha VARCHAR(40) NULL,
    operadora VARCHAR(80) NULL,
    conta_vinculada VARCHAR(120) NULL,
    polegadas VARCHAR(30) NULL,
    resolucao VARCHAR(60) NULL,
    tipo_painel VARCHAR(60) NULL,
    entrada_video VARCHAR(120) NULL,
    fonte_ou_cabo VARCHAR(120) NULL,
    criado_por INT NOT NULL,
    empresa_id INT NOT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    data_ultima_movimentacao TIMESTAMP NULL DEFAULT NULL,
    PRIMARY KEY (id),
    KEY idx_ativos_status (status),
    KEY idx_ativos_empresa_id (empresa_id),
    KEY idx_ativos_criado_por (criado_por),
    KEY idx_ativos_departamento (departamento),
    KEY idx_ativos_setor (setor),
    KEY idx_ativos_tipo_ativo (tipo_ativo),
    KEY idx_ativos_codigo_interno (codigo_interno),
    KEY idx_ativos_usuario_responsavel (usuario_responsavel),
    CONSTRAINT fk_ativos_criado_por
        FOREIGN KEY (criado_por)
        REFERENCES usuarios (id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT fk_ativos_empresa
        FOREIGN KEY (empresa_id)
        REFERENCES empresas (id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
);

-- =========================================================
-- TABELA: ativos_arquivos
-- Armazena anexos físicos vinculados a um ativo.
-- Suporta múltiplos documentos por ativo com tipo categorizado.
-- =========================================================
CREATE TABLE IF NOT EXISTS ativos_arquivos (
    id INT NOT NULL AUTO_INCREMENT,
    ativo_id VARCHAR(20) NOT NULL,
    tipo_documento VARCHAR(30) NOT NULL DEFAULT 'outro',
    nome_original VARCHAR(255) NOT NULL,
    nome_armazenado VARCHAR(255) NOT NULL,
    caminho_arquivo VARCHAR(512) NOT NULL,
    mime_type VARCHAR(127) NULL,
    tamanho_bytes INT NOT NULL DEFAULT 0,
    enviado_por INT NOT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_ativos_arquivos_ativo_id (ativo_id),
    KEY idx_ativos_arquivos_tipo (tipo_documento),
    KEY idx_ativos_arquivos_enviado_por (enviado_por),
    CONSTRAINT fk_ativos_arquivos_ativo
        FOREIGN KEY (ativo_id)
        REFERENCES ativos (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_ativos_arquivos_usuario
        FOREIGN KEY (enviado_por)
        REFERENCES usuarios (id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
);

-- =========================================================
-- TABELA: sequencias_ativo
-- Controla a geração automática de ID para ativos por empresa.
-- Usa SELECT FOR UPDATE para garantir atomicidade em ambiente concorrente.
-- =========================================================
CREATE TABLE IF NOT EXISTS sequencias_ativo (
    empresa_id     INT          NOT NULL,
    proximo_numero INT UNSIGNED NOT NULL DEFAULT 1,
    updated_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                                ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (empresa_id),
    CONSTRAINT fk_seq_empresa
        FOREIGN KEY (empresa_id) REFERENCES empresas (id)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;