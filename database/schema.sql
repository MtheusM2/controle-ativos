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
    email VARCHAR(255) NOT NULL,
    senha_hash VARCHAR(255) NOT NULL,
    pergunta_recuperacao VARCHAR(255) NOT NULL,
    resposta_recuperacao_hash VARCHAR(255) NOT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    perfil VARCHAR(20) NOT NULL DEFAULT 'usuario',
    empresa_id INT NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uk_usuarios_email (email),
    KEY idx_usuarios_perfil (perfil),
    KEY idx_usuarios_empresa_id (empresa_id),
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
    tipo VARCHAR(100) NOT NULL,
    marca VARCHAR(100) NOT NULL,
    modelo VARCHAR(100) NOT NULL,
    usuario_responsavel VARCHAR(100) NULL,
    departamento VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    data_entrada DATE NOT NULL,
    data_saida DATE NULL,
    criado_por INT NOT NULL,
    empresa_id INT NOT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_ativos_status (status),
    KEY idx_ativos_empresa_id (empresa_id),
    KEY idx_ativos_criado_por (criado_por),
    KEY idx_ativos_departamento (departamento),
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