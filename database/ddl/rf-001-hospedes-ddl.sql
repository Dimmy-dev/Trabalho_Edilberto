-- =====================================================================
-- Script DDL: Sistema Grand Plaza Hotel Management
-- Requisito Funcional: RF-001 - Cadastro de Hóspede & Arquitetura Segura
-- Banco de Dados: MySQL 8.0+
-- Autor: Equipe de Desenvolvimento — Lab Inovação III (2026)
-- =====================================================================

CREATE DATABASE IF NOT EXISTS db_hotel_grand_plaza
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE db_hotel_grand_plaza;

-- ---------------------------------------------------------------------
-- 1. TABELA DE HÓSPEDES (tb_hospedes) - Domínio Central do RF-001
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tb_hospedes (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    uuid_publico CHAR(36) NOT NULL UNIQUE DEFAULT (UUID()),
    nome VARCHAR(150) NOT NULL,
    email VARCHAR(180) NOT NULL,
    cpf CHAR(11) NOT NULL,
    telefone VARCHAR(20) NOT NULL,
    data_nascimento DATE NOT NULL,
    observacoes TEXT NULL,
    created_at TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),

    -- Restrições de Unicidade e Regras de Negócio (RN-01 e RN-02)
    CONSTRAINT uk_hospedes_email UNIQUE (email),
    CONSTRAINT uk_hospedes_cpf UNIQUE (cpf),
    CONSTRAINT chk_hospedes_nome_minlen CHECK (CHAR_LENGTH(nome) >= 3),
    CONSTRAINT chk_hospedes_cpf_digits CHECK (cpf REGEXP '^[0-9]{11}$')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Índices B-Tree para alta performance em buscas frequentes
CREATE INDEX idx_hospedes_nome ON tb_hospedes (nome);
CREATE INDEX idx_hospedes_created ON tb_hospedes (created_at DESC);

-- ---------------------------------------------------------------------
-- 2. TABELA DE SESSÕES DE OPERADORES / CLIENTES (tb_sessoes)
-- Gerenciamento de tokens, expiração temporal e revogação ativa
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tb_sessoes (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_hospede BIGINT UNSIGNED NOT NULL,
    token_hash VARCHAR(64) NOT NULL,
    ip_address VARCHAR(45) NULL,
    user_agent VARCHAR(500) NULL,
    expires_at DATETIME(3) NOT NULL,
    revoked_at DATETIME(3) NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    CONSTRAINT uk_sessoes_token_hash UNIQUE (token_hash),
    CONSTRAINT fk_sessoes_hospede FOREIGN KEY (id_hospede) 
        REFERENCES tb_hospedes(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_sessoes_lookup ON tb_sessoes (token_hash, is_active, expires_at);
CREATE INDEX idx_sessoes_hospede ON tb_sessoes (id_hospede);

-- ---------------------------------------------------------------------
-- 3. TABELA DE QUARTOS (tb_quartos)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tb_quartos (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    numero VARCHAR(10) NOT NULL UNIQUE,
    categoria VARCHAR(50) NOT NULL,
    valor_diaria DECIMAL(10, 2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'DISPONIVEL',
    created_at TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    CONSTRAINT chk_quartos_valor CHECK (valor_diaria > 0),
    CONSTRAINT chk_quartos_status CHECK (status IN ('DISPONIVEL', 'OCUPADO', 'MANUTENCAO', 'RESERVADO'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 4. TABELA DE RESERVAS (tb_reservas)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tb_reservas (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    uuid_publico CHAR(36) NOT NULL UNIQUE DEFAULT (UUID()),
    id_hospede BIGINT UNSIGNED NOT NULL,
    id_quarto BIGINT UNSIGNED NOT NULL,
    data_checkin DATE NOT NULL,
    data_checkout DATE NOT NULL,
    valor_total DECIMAL(10, 2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
    created_at TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),

    CONSTRAINT fk_reservas_hospede FOREIGN KEY (id_hospede) 
        REFERENCES tb_hospedes(id) ON DELETE RESTRICT,
    CONSTRAINT fk_reservas_quarto FOREIGN KEY (id_quarto) 
        REFERENCES tb_quartos(id) ON DELETE RESTRICT,
    CONSTRAINT chk_reservas_datas CHECK (data_checkout > data_checkin),
    CONSTRAINT chk_reservas_status CHECK (status IN ('PENDENTE', 'CONFIRMADA', 'CHECKIN_ATIVO', 'CONCLUIDA', 'CANCELADA'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_reservas_hospede ON tb_reservas (id_hospede);
CREATE INDEX idx_reservas_datas ON tb_reservas (data_checkin, data_checkout);

-- ---------------------------------------------------------------------
-- 5. TABELA DE PAGAMENTOS PIX (tb_pagamentos_pix)
-- Controle de transações instantâneas, webhook idempotente e QR code
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tb_pagamentos_pix (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    uuid_publico CHAR(36) NOT NULL UNIQUE DEFAULT (UUID()),
    id_reserva BIGINT UNSIGNED NULL,
    pix_webhook_id VARCHAR(100) NULL,
    end_to_end_id VARCHAR(50) NULL,
    valor DECIMAL(10, 2) NOT NULL,
    qr_code_copia_cola TEXT NOT NULL,
    qr_code_url VARCHAR(500) NULL,
    qr_expires_at DATETIME(3) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    pago_em DATETIME(3) NULL,
    payload_bruto JSON NULL,
    created_at TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),

    CONSTRAINT uk_pagamentos_pix_webhook UNIQUE (pix_webhook_id),
    CONSTRAINT fk_pagamentos_reserva FOREIGN KEY (id_reserva) 
        REFERENCES tb_reservas(id) ON DELETE RESTRICT,
    CONSTRAINT chk_pagamentos_valor CHECK (valor > 0),
    CONSTRAINT chk_pagamentos_status CHECK (status IN ('PENDING', 'PAID', 'EXPIRED', 'CANCELLED', 'REFUNDED'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_pagamentos_status_expiracao ON tb_pagamentos_pix (status, qr_expires_at);

-- ---------------------------------------------------------------------
-- 6. TABELA DE AUDITORIA E SEGURANÇA (tb_audit_logs)
-- Atendimento à RN-08 e rastreabilidade para conformidade LGPD
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tb_audit_logs (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_hospede BIGINT UNSIGNED NULL,
    acao VARCHAR(60) NOT NULL,
    tabela_afetada VARCHAR(50) NOT NULL,
    registro_id BIGINT UNSIGNED NULL,
    dados_anteriores JSON NULL,
    dados_novos JSON NULL,
    ip_origem VARCHAR(45) NOT NULL,
    user_agent VARCHAR(300) NULL,
    created_at TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    CONSTRAINT fk_audit_hospede FOREIGN KEY (id_hospede) 
        REFERENCES tb_hospedes(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_audit_created ON tb_audit_logs (created_at DESC);
CREATE INDEX idx_audit_tabela_registro ON tb_audit_logs (tabela_afetada, registro_id);
