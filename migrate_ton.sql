-- ================================================================
-- MIGRACIÓN TON COMPLETA
-- Ejecuta esto en la consola MySQL de PythonAnywhere
-- ================================================================

-- 1. Agregar columna ton_wallet a users (si no existe)
ALTER TABLE users ADD COLUMN IF NOT EXISTS ton_wallet VARCHAR(100) DEFAULT NULL;

-- 2. Crear tabla ton_deposits (si no existe)
CREATE TABLE IF NOT EXISTS ton_deposits (
    id INT AUTO_INCREMENT PRIMARY KEY,
    deposit_id VARCHAR(100) NOT NULL UNIQUE,
    user_id VARCHAR(50) NOT NULL,

    ton_amount DECIMAL(20, 9) NOT NULL,
    doge_credited DECIMAL(20, 8) NOT NULL,

    ton_wallet_from VARCHAR(100) NOT NULL,
    ton_tx_hash VARCHAR(200) DEFAULT NULL,
    boc TEXT DEFAULT NULL,

    status ENUM('pending','confirmed','credited','failed') DEFAULT 'pending',
    admin_note TEXT DEFAULT NULL,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    confirmed_at DATETIME DEFAULT NULL,

    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_deposit_id (deposit_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Agregar columnas faltantes en withdrawals
ALTER TABLE withdrawals
    ADD COLUMN IF NOT EXISTS withdrawal_type VARCHAR(20) DEFAULT 'doge',
    ADD COLUMN IF NOT EXISTS ton_wallet_address VARCHAR(100) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS ton_amount DECIMAL(20, 9) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS ton_tx_hash VARCHAR(200) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS processed_at DATETIME DEFAULT NULL;

-- 4. Config para TON (inserta solo si no existen)
INSERT IGNORE INTO config (config_key, config_value) VALUES
    ('ton_wallet_address',        ''),
    ('ton_to_doge_rate',          '100'),
    ('ton_min_deposit',           '0.1'),
    ('ton_deposits_enabled',      '1'),
    ('ton_auto_confirm',          '1'),
    ('ton_withdrawal_enabled',    '1'),
    ('ton_withdrawal_min_doge',   '10'),
    ('ton_withdrawal_fee_percent','2'),
    ('doge_to_ton_rate',          '100'),
    ('ton_bot_mnemonic',          ''),
    ('toncenter_api_key',         '');

-- ¡Listo! Verifica con:
-- SHOW TABLES;
-- DESCRIBE ton_deposits;
-- DESCRIBE withdrawals;
