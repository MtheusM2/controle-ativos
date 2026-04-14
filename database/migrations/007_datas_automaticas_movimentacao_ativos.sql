-- =========================================================
-- MIGRATION 007 - Datas automáticas e movimentação de ativos
-- Adiciona timestamps oficiais da Fase 2 sem quebrar os campos legados.
-- =========================================================

ALTER TABLE ativos
    ADD COLUMN created_at TIMESTAMP NULL DEFAULT NULL AFTER atualizado_em,
    ADD COLUMN updated_at TIMESTAMP NULL DEFAULT NULL AFTER created_at,
    ADD COLUMN data_ultima_movimentacao TIMESTAMP NULL DEFAULT NULL AFTER updated_at;

UPDATE ativos
SET created_at = COALESCE(created_at, criado_em),
    updated_at = COALESCE(updated_at, atualizado_em)
WHERE created_at IS NULL
   OR updated_at IS NULL;

ALTER TABLE ativos
    MODIFY COLUMN created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    MODIFY COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;