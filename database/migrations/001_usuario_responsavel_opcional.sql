-- database/migrations/001_usuario_responsavel_opcional.sql

-- Esta migração ajusta o banco já existente para a nova regra:
-- o campo usuario_responsavel deixa de ser obrigatório no nível estrutural.
-- A exigência passa a ser da regra de negócio, somente para ativos em uso.

USE controle_ativos;

-- Passo 1:
-- Permite que a coluna aceite NULL.
ALTER TABLE ativos
MODIFY COLUMN usuario_responsavel VARCHAR(100) NULL;

-- Passo 2:
-- Normaliza registros antigos que eventualmente estejam com string vazia.
UPDATE ativos
SET usuario_responsavel = NULL
WHERE usuario_responsavel IS NOT NULL
  AND TRIM(usuario_responsavel) = '';