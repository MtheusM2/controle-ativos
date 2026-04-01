-- Migração de domínio: renomeia a coluna de documentação do ativo.
ALTER TABLE ativos CHANGE COLUMN seguro garantia VARCHAR(100) NULL;
