ALTER TABLE ativos
    ADD COLUMN IF NOT EXISTS mac_address VARCHAR(17) NULL AFTER nome_equipamento;

ALTER TABLE ativos_arquivos
    ADD COLUMN IF NOT EXISTS data_inicio_garantia DATE NULL AFTER enviado_por,
    ADD COLUMN IF NOT EXISTS data_fim_garantia DATE NULL AFTER data_inicio_garantia,
    ADD COLUMN IF NOT EXISTS prazo_garantia_meses INT NULL AFTER data_fim_garantia,
    ADD COLUMN IF NOT EXISTS observacao_garantia VARCHAR(255) NULL AFTER prazo_garantia_meses;
