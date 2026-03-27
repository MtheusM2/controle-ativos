-- database/schema.sql

-- Cria o banco de dados, caso ainda não exista.
CREATE DATABASE IF NOT EXISTS controle_ativos
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- Seleciona o banco de dados.
USE controle_ativos;

-- Tabela de usuários do sistema.
CREATE TABLE IF NOT EXISTS usuarios (
  id INT NOT NULL AUTO_INCREMENT,
  email VARCHAR(255) NOT NULL,
  senha_hash VARCHAR(255) NOT NULL,
  pergunta_recuperacao VARCHAR(255) NOT NULL,
  resposta_recuperacao_hash VARCHAR(255) NOT NULL,
  criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_usuarios_email (email)
) ENGINE=InnoDB;

-- Tabela de ativos.
CREATE TABLE IF NOT EXISTS ativos (
  id VARCHAR(20) NOT NULL,
  tipo VARCHAR(100) NOT NULL,
  marca VARCHAR(100) NOT NULL,
  modelo VARCHAR(100) NOT NULL,

  -- Responsável agora é opcional.
  -- A obrigatoriedade passa a ser tratada pela regra de negócio
  -- apenas quando o status for "Em Uso".
  usuario_responsavel VARCHAR(100) NULL,

  departamento VARCHAR(100) NOT NULL,
  status VARCHAR(50) NOT NULL,
  data_entrada DATE NOT NULL,
  data_saida DATE NULL,
  criado_por INT NOT NULL,
  criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_ativos_status (status),
  KEY idx_ativos_departamento (departamento),
  KEY idx_ativos_usuario_responsavel (usuario_responsavel),
  KEY idx_ativos_data_entrada (data_entrada),
  KEY idx_ativos_data_saida (data_saida),
  CONSTRAINT fk_ativos_criado_por
    FOREIGN KEY (criado_por) REFERENCES usuarios(id)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
) ENGINE=InnoDB;