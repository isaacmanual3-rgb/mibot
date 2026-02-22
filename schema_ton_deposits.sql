-- ============================================
-- TON DEPOSITS TABLE
-- Run this ALTER if users table already exists
-- ============================================

-- Add TON wallet address field to users (if not exists)
ALTER TABLE users ADD COLUMN IF NOT EXISTS ton_wallet VARCHAR(100) DEFAULT NULL;

-- Deposits table
CREATE TABLE IF NOT EXISTS ton_deposits (
    id INT AUTO_INCREMENT PRIMARY KEY,
    deposit_id VARCHAR(100) NOT NULL UNIQUE,
    user_id VARCHAR(50) NOT NULL,
    
    ton_amount DECIMAL(20, 9) NOT NULL,       -- Amount in TON
    doge_credited DECIMAL(20, 8) NOT NULL,    -- DOGE credited (1:1 example, configurable)
    
    ton_wallet_from VARCHAR(100) NOT NULL,    -- User's TON wallet
    ton_tx_hash VARCHAR(200) DEFAULT NULL,   -- TON transaction hash
    boc VARCHAR(2000) DEFAULT NULL,           -- Raw BOC for verification
    
    status ENUM('pending','confirmed','credited','failed') DEFAULT 'pending',
    admin_note TEXT DEFAULT NULL,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    confirmed_at DATETIME DEFAULT NULL,
    
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_deposit_id (deposit_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Config entries for TON
INSERT INTO config (config_key, config_value) VALUES
    ('ton_wallet_address', 'UQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAXl'),
    ('ton_to_doge_rate', '100'),
    ('ton_min_deposit', '0.1'),
    ('ton_deposits_enabled', '1')
ON DUPLICATE KEY UPDATE config_key = config_key;
