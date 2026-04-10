-- database/migrations/005_sequencias_ativo.sql
-- Suporte a geração automática de ID de ativo por empresa.
-- Evita digitação manual do ID e garante unicidade via sequência transacional.
--
-- Aplicar com: mysql -u <user> -p controle_ativos < 005_sequencias_ativo.sql

USE controle_ativos;

-- Passo 1: coluna prefixo_ativo em empresas (3 chars por convenção, até 10)
-- Exemplo: OPU para Opus, VIC para Vicente Martins
ALTER TABLE empresas
    ADD COLUMN IF NOT EXISTS prefixo_ativo VARCHAR(10) NULL
    AFTER codigo;

-- Passo 2: tabela de sequências por empresa (transação segura via FOR UPDATE)
-- Impede race condition: dois processos nunca gerarão o mesmo número para a mesma empresa.
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

-- Passo 3: configurar prefixos das unidades conhecidas
-- IMPORTANTE: antes de aplicar em produção, verificar que os nomes batem exatamente
-- com os nomes na tabela empresas do seu banco.
UPDATE empresas SET prefixo_ativo = 'OPU' WHERE nome = 'Opus';
UPDATE empresas SET prefixo_ativo = 'VIC' WHERE nome = 'Vicente Martins';

-- Passo 4: inicializar sequências para empresas com prefixo configurado
-- Cada empresa começa do número 1 — ativos históricos com IDs antigos mantêm seus IDs.
INSERT INTO sequencias_ativo (empresa_id, proximo_numero)
    SELECT id, 1 FROM empresas WHERE prefixo_ativo IS NOT NULL
ON DUPLICATE KEY UPDATE empresa_id = empresa_id;  -- no-op se já existir
