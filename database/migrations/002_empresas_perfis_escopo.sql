-- database/migrations/002_empresas_perfis_escopo.sql

-- Esta migração cria a base corporativa do sistema:
-- - empresas
-- - perfis de acesso
-- - vínculo organizacional dos usuários
-- - escopo de ativos por empresa
--
-- Estratégia de transição:
-- - cria uma empresa base para não quebrar a base atual
-- - coloca os usuários atuais como 'adm' temporariamente
-- - vincula os ativos já existentes à empresa base herdada dos usuários
--
-- Depois dessa migração, o ideal é:
-- 1. cadastrar as 5 empresas reais
-- 2. ajustar o empresa_id dos usuários
-- 3. ajustar perfis de quem não deve continuar como admin

USE controle_ativos;

-- =========================
-- 1. TABELA EMPRESAS
-- =========================
CREATE TABLE IF NOT EXISTS empresas (
  id INT NOT NULL AUTO_INCREMENT,
  nome VARCHAR(150) NOT NULL,
  codigo VARCHAR(50) NOT NULL,
  ativa TINYINT(1) NOT NULL DEFAULT 1,
  criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_empresas_codigo (codigo),
  UNIQUE KEY uq_empresas_nome (nome)
) ENGINE=InnoDB;

-- Cria empresa base para transição, se ainda não existir.
INSERT INTO empresas (nome, codigo, ativa)
SELECT 'Opus Base - Ajustar Depois', 'OPUS-BASE', 1
WHERE NOT EXISTS (
    SELECT 1
    FROM empresas
    WHERE codigo = 'OPUS-BASE'
);

-- Guarda o ID da empresa base.
SET @empresa_base_id = (
    SELECT id
    FROM empresas
    WHERE codigo = 'OPUS-BASE'
    LIMIT 1
);

-- =========================
-- 2. USUÁRIOS
-- =========================
ALTER TABLE usuarios
ADD COLUMN perfil VARCHAR(20) NOT NULL DEFAULT 'usuario',
ADD COLUMN empresa_id INT NULL;

-- Durante a transição, todos os usuários atuais viram admin
-- para evitar perda de acesso imediata.
UPDATE usuarios
SET perfil = 'adm',
    empresa_id = @empresa_base_id
WHERE empresa_id IS NULL;

ALTER TABLE usuarios
MODIFY COLUMN empresa_id INT NOT NULL;

ALTER TABLE usuarios
ADD KEY idx_usuarios_perfil (perfil),
ADD KEY idx_usuarios_empresa_id (empresa_id),
ADD CONSTRAINT fk_usuarios_empresa
  FOREIGN KEY (empresa_id) REFERENCES empresas(id)
  ON UPDATE CASCADE
  ON DELETE RESTRICT;

-- =========================
-- 3. ATIVOS
-- =========================
ALTER TABLE ativos
ADD COLUMN empresa_id INT NULL;

-- Herda a empresa do usuário criador.
UPDATE ativos a
INNER JOIN usuarios u
    ON u.id = a.criado_por
SET a.empresa_id = u.empresa_id
WHERE a.empresa_id IS NULL;

ALTER TABLE ativos
MODIFY COLUMN empresa_id INT NOT NULL;

ALTER TABLE ativos
ADD KEY idx_ativos_empresa_id (empresa_id),
ADD CONSTRAINT fk_ativos_empresa
  FOREIGN KEY (empresa_id) REFERENCES empresas(id)
  ON UPDATE CASCADE
  ON DELETE RESTRICT;