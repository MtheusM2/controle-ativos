-- Script de segurança para criar usuário dedicado da aplicação.
-- Execute com usuário administrador (ex.: root) no MySQL.

-- 1) Cria usuário da aplicação apenas para localhost, se ainda não existir.
CREATE USER IF NOT EXISTS 'opus_app'@'localhost'
IDENTIFIED BY 'CHANGE_ME_STRONG_PASSWORD';

-- 2) Concede privilégios necessários para operação do sistema no schema alvo.
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX
ON `controle_ativos`.*
TO 'opus_app'@'localhost';

-- 3) Recarrega a tabela de privilégios para garantir aplicação imediata.
FLUSH PRIVILEGES;
