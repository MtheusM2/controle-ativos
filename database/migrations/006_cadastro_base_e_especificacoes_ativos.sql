-- =========================================================
-- MIGRATION 006
-- Evolui a tabela ativos para cadastro base + especificacoes por tipo.
-- Mantem colunas legadas para compatibilidade com rotas e listagens existentes.
-- =========================================================

ALTER TABLE ativos
    ADD COLUMN codigo_interno VARCHAR(50) NULL AFTER id,
    ADD COLUMN serial VARCHAR(120) NULL AFTER modelo,
    ADD COLUMN descricao VARCHAR(255) NULL AFTER modelo,
    ADD COLUMN categoria VARCHAR(100) NULL AFTER descricao,
    ADD COLUMN tipo_ativo VARCHAR(50) NULL AFTER categoria,
    ADD COLUMN condicao VARCHAR(50) NULL AFTER tipo_ativo,
    ADD COLUMN localizacao VARCHAR(120) NULL AFTER condicao,
    ADD COLUMN setor VARCHAR(100) NULL AFTER localizacao,
    ADD COLUMN email_responsavel VARCHAR(255) NULL AFTER usuario_responsavel,
    ADD COLUMN data_compra DATE NULL AFTER data_saida,
    ADD COLUMN valor DECIMAL(12,2) NULL AFTER data_compra,
    ADD COLUMN observacoes TEXT NULL AFTER valor,
    ADD COLUMN detalhes_tecnicos VARCHAR(255) NULL AFTER observacoes,
    ADD COLUMN processador VARCHAR(120) NULL AFTER detalhes_tecnicos,
    ADD COLUMN ram VARCHAR(60) NULL AFTER processador,
    ADD COLUMN armazenamento VARCHAR(120) NULL AFTER ram,
    ADD COLUMN sistema_operacional VARCHAR(120) NULL AFTER armazenamento,
    ADD COLUMN carregador VARCHAR(120) NULL AFTER sistema_operacional,
    ADD COLUMN teamviewer_id VARCHAR(100) NULL AFTER carregador,
    ADD COLUMN anydesk_id VARCHAR(100) NULL AFTER teamviewer_id,
    ADD COLUMN nome_equipamento VARCHAR(120) NULL AFTER anydesk_id,
    ADD COLUMN hostname VARCHAR(120) NULL AFTER nome_equipamento,
    ADD COLUMN imei_1 VARCHAR(40) NULL AFTER hostname,
    ADD COLUMN imei_2 VARCHAR(40) NULL AFTER imei_1,
    ADD COLUMN numero_linha VARCHAR(40) NULL AFTER imei_2,
    ADD COLUMN operadora VARCHAR(80) NULL AFTER numero_linha,
    ADD COLUMN conta_vinculada VARCHAR(120) NULL AFTER operadora,
    ADD COLUMN polegadas VARCHAR(30) NULL AFTER conta_vinculada,
    ADD COLUMN resolucao VARCHAR(60) NULL AFTER polegadas,
    ADD COLUMN tipo_painel VARCHAR(60) NULL AFTER resolucao,
    ADD COLUMN entrada_video VARCHAR(120) NULL AFTER tipo_painel,
    ADD COLUMN fonte_ou_cabo VARCHAR(120) NULL AFTER entrada_video;

-- Indices leves para filtros operacionais frequentes da nova tela.
ALTER TABLE ativos
    ADD KEY idx_ativos_tipo_ativo (tipo_ativo),
    ADD KEY idx_ativos_codigo_interno (codigo_interno),
    ADD KEY idx_ativos_setor (setor);
