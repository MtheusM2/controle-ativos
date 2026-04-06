-- database/migrations/004_usuarios_nome_lembrar_me.sql

-- Adiciona dados de perfil e preferencia persistente de login.
-- Objetivo: habilitar tela de configuracoes com nome editavel e lembrar-me seguro.

USE controle_ativos;

-- Adiciona a coluna nome apenas quando ainda nao existir.
SET @coluna_nome_existe = (
	SELECT COUNT(*)
	FROM INFORMATION_SCHEMA.COLUMNS
	WHERE TABLE_SCHEMA = DATABASE()
	  AND TABLE_NAME = 'usuarios'
	  AND COLUMN_NAME = 'nome'
);
SET @sql_nome = IF(
	@coluna_nome_existe = 0,
	'ALTER TABLE usuarios ADD COLUMN nome VARCHAR(120) NULL AFTER id',
	'SELECT 1'
);
PREPARE stmt_nome FROM @sql_nome;
EXECUTE stmt_nome;
DEALLOCATE PREPARE stmt_nome;

-- Adiciona a coluna lembrar_me_ativo apenas quando ainda nao existir.
SET @coluna_lembrar_existe = (
	SELECT COUNT(*)
	FROM INFORMATION_SCHEMA.COLUMNS
	WHERE TABLE_SCHEMA = DATABASE()
	  AND TABLE_NAME = 'usuarios'
	  AND COLUMN_NAME = 'lembrar_me_ativo'
);
SET @sql_lembrar = IF(
	@coluna_lembrar_existe = 0,
	'ALTER TABLE usuarios ADD COLUMN lembrar_me_ativo TINYINT(1) NOT NULL DEFAULT 0 AFTER empresa_id',
	'SELECT 1'
);
PREPARE stmt_lembrar FROM @sql_lembrar;
EXECUTE stmt_lembrar;
DEALLOCATE PREPARE stmt_lembrar;

-- Preenche nome inicial com base no e-mail para manter UX consistente.
UPDATE usuarios
SET nome = TRIM(SUBSTRING_INDEX(email, '@', 1))
WHERE nome IS NULL OR TRIM(nome) = '';

-- Mantem a coluna nome obrigatoria apos backfill.
SET @coluna_nome_existe_pos = (
	SELECT COUNT(*)
	FROM INFORMATION_SCHEMA.COLUMNS
	WHERE TABLE_SCHEMA = DATABASE()
	  AND TABLE_NAME = 'usuarios'
	  AND COLUMN_NAME = 'nome'
);
SET @sql_nome_not_null = IF(
	@coluna_nome_existe_pos = 1,
	'ALTER TABLE usuarios MODIFY COLUMN nome VARCHAR(120) NOT NULL',
	'SELECT 1'
);
PREPARE stmt_nome_not_null FROM @sql_nome_not_null;
EXECUTE stmt_nome_not_null;
DEALLOCATE PREPARE stmt_nome_not_null;
