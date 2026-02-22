-- ============================================
-- DOGEQUEST DATABASE SCHEMA v1.0
-- MySQL/MariaDB - Completely New Design
-- Daily Check-In System - DOGE Only Currency
-- ============================================

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS promo_redemptions;
DROP TABLE IF EXISTS promo_codes;
DROP TABLE IF EXISTS withdrawals;
DROP TABLE IF EXISTS referrals;
DROP TABLE IF EXISTS tasks;
DROP TABLE IF EXISTS task_completions;
DROP TABLE IF EXISTS daily_checkins;
DROP TABLE IF EXISTS balance_history;
DROP TABLE IF EXISTS user_ips;
DROP TABLE IF EXISTS ip_bans;
DROP TABLE IF EXISTS admin_sessions;
DROP TABLE IF EXISTS config;
DROP TABLE IF EXISTS stats;
DROP TABLE IF EXISTS users;
SET FOREIGN_KEY_CHECKS = 1;

-- ============================================
-- USERS TABLE (DOGE Only)
-- ============================================
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL UNIQUE,
    username VARCHAR(100) DEFAULT NULL,
    first_name VARCHAR(100) DEFAULT 'Player',
    
    -- DOGE Balance Only
    doge_balance DECIMAL(20, 8) DEFAULT 0.00000000,
    total_earned DECIMAL(20, 8) DEFAULT 0.00000000,
    
    -- Daily Check-In Data
    checkin_streak INT DEFAULT 0,
    last_checkin DATE DEFAULT NULL,
    longest_streak INT DEFAULT 0,
    total_checkins INT DEFAULT 0,
    
    -- Referral Data
    referral_count INT DEFAULT 0,
    validated_referrals INT DEFAULT 0,
    referred_by VARCHAR(50) DEFAULT NULL,
    referral_earnings DECIMAL(20, 8) DEFAULT 0.00000000,
    
    -- Wallet
    wallet_address VARCHAR(100) DEFAULT NULL,
    wallet_linked_at DATETIME DEFAULT NULL,
    
    -- Status
    banned TINYINT(1) DEFAULT 0,
    ban_reason VARCHAR(255) DEFAULT NULL,
    last_ip VARCHAR(50) DEFAULT NULL,
    
    -- Completed Tasks (JSON array)
    completed_tasks JSON DEFAULT NULL,
    
    -- Timestamps
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_active DATETIME DEFAULT NULL,
    
    INDEX idx_user_id (user_id),
    INDEX idx_username (username),
    INDEX idx_referred_by (referred_by),
    INDEX idx_banned (banned)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- DAILY CHECK-INS TABLE
-- ============================================
CREATE TABLE daily_checkins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    checkin_date DATE NOT NULL,
    day_number INT NOT NULL,
    reward DECIMAL(10, 8) NOT NULL,
    streak_bonus DECIMAL(10, 8) DEFAULT 0.00000000,
    total_reward DECIMAL(10, 8) NOT NULL,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY unique_daily_checkin (user_id, checkin_date),
    INDEX idx_user_id (user_id),
    INDEX idx_checkin_date (checkin_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- REFERRALS TABLE
-- ============================================
CREATE TABLE referrals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    referrer_id VARCHAR(50) NOT NULL,
    referred_id VARCHAR(50) NOT NULL,
    referred_username VARCHAR(100) DEFAULT NULL,
    referred_first_name VARCHAR(100) DEFAULT 'Player',
    
    validated TINYINT(1) DEFAULT 0,
    bonus_paid DECIMAL(10, 8) DEFAULT 0.00000000,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    validated_at DATETIME DEFAULT NULL,
    
    UNIQUE KEY unique_referral (referrer_id, referred_id),
    INDEX idx_referrer_id (referrer_id),
    INDEX idx_validated (validated)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- TASKS TABLE
-- ============================================
CREATE TABLE tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id VARCHAR(50) NOT NULL UNIQUE,
    title VARCHAR(200) NOT NULL,
    description TEXT DEFAULT NULL,
    reward DECIMAL(10, 8) DEFAULT 0.00000000,
    url VARCHAR(500) DEFAULT NULL,
    icon VARCHAR(50) DEFAULT 'star',
    task_type ENUM('telegram', 'social', 'external', 'daily', 'special') DEFAULT 'telegram',
    
    -- Channel Verification
    requires_channel TINYINT(1) DEFAULT 0,
    channel_username VARCHAR(100) DEFAULT NULL,
    
    -- Limits
    active TINYINT(1) DEFAULT 1,
    max_completions INT DEFAULT NULL,
    current_completions INT DEFAULT 0,
    
    -- Order
    sort_order INT DEFAULT 0,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_task_id (task_id),
    INDEX idx_active (active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- TASK COMPLETIONS TABLE
-- ============================================
CREATE TABLE task_completions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    task_id VARCHAR(50) NOT NULL,
    reward_amount DECIMAL(10, 8) NOT NULL,
    completed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY unique_completion (user_id, task_id),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- WITHDRAWALS TABLE (DOGE Only)
-- ============================================
CREATE TABLE withdrawals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    withdrawal_id VARCHAR(100) NOT NULL UNIQUE,
    user_id VARCHAR(50) NOT NULL,
    
    amount DECIMAL(20, 8) NOT NULL,
    fee DECIMAL(20, 8) DEFAULT 0.00000000,
    net_amount DECIMAL(20, 8) NOT NULL,
    wallet_address VARCHAR(100) NOT NULL,
    
    status ENUM('pending', 'processing', 'completed', 'failed', 'rejected') DEFAULT 'pending',
    tx_hash VARCHAR(100) DEFAULT NULL,
    admin_note TEXT DEFAULT NULL,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    processed_at DATETIME DEFAULT NULL,
    
    INDEX idx_user_id (user_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- PROMO CODES TABLE (DOGE Only)
-- ============================================
CREATE TABLE promo_codes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    reward DECIMAL(10, 8) NOT NULL DEFAULT 0.00000000,
    
    max_uses INT DEFAULT NULL,
    current_uses INT DEFAULT 0,
    
    active TINYINT(1) DEFAULT 1,
    expires_at DATETIME DEFAULT NULL,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_code (code),
    INDEX idx_active (active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- PROMO REDEMPTIONS TABLE
-- ============================================
CREATE TABLE promo_redemptions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    code VARCHAR(50) NOT NULL,
    reward DECIMAL(10, 8) NOT NULL,
    
    redeemed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY unique_redemption (user_id, code),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- BALANCE HISTORY TABLE
-- ============================================
CREATE TABLE balance_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    action VARCHAR(100) NOT NULL,
    amount DECIMAL(20, 8) NOT NULL,
    balance_before DECIMAL(20, 8) DEFAULT 0.00000000,
    balance_after DECIMAL(20, 8) DEFAULT 0.00000000,
    description TEXT DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- CONFIG TABLE
-- ============================================
CREATE TABLE config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value TEXT DEFAULT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- STATS TABLE
-- ============================================
CREATE TABLE stats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stat_key VARCHAR(100) NOT NULL UNIQUE,
    stat_value BIGINT DEFAULT 0,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- USER IPS TABLE
-- ============================================
CREATE TABLE user_ips (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    ip_address VARCHAR(50) NOT NULL,
    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    times_seen INT DEFAULT 1,
    
    UNIQUE KEY unique_user_ip (user_id, ip_address),
    INDEX idx_ip_address (ip_address)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- IP BANS TABLE
-- ============================================
CREATE TABLE ip_bans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ip_address VARCHAR(50) NOT NULL UNIQUE,
    reason VARCHAR(255) DEFAULT NULL,
    banned_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- ADMIN SESSIONS TABLE
-- ============================================
CREATE TABLE admin_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    admin_id VARCHAR(50) NOT NULL,
    session_token VARCHAR(255) NOT NULL,
    ip_address VARCHAR(50) DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    
    INDEX idx_session_token (session_token)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- DEFAULT CONFIG VALUES
-- ============================================
INSERT INTO config (config_key, config_value) VALUES
    ('daily_base_reward', '0.01'),
    ('daily_streak_bonus', '0.002'),
    ('daily_max_streak_bonus', '0.05'),
    ('referral_bonus', '0.05'),
    ('referral_commission', '0.10'),
    ('min_withdrawal', '1.0'),
    ('withdrawal_fee', '0.5'),
    ('withdrawal_mode', 'manual'),
    ('admin_password', 'admin123'),
    ('bot_token', ''),
    ('bot_username', 'DogeQuestBot'),
    ('official_channel', '@DogeQuest'),
    ('support_link', 'https://t.me/DogeQuestSupport')
ON DUPLICATE KEY UPDATE config_value = VALUES(config_value);

-- ============================================
-- DEFAULT STATS
-- ============================================
INSERT INTO stats (stat_key, stat_value) VALUES
    ('total_users', 0),
    ('total_checkins', 0),
    ('total_tasks_completed', 0),
    ('total_withdrawals', 0),
    ('total_doge_distributed', 0)
ON DUPLICATE KEY UPDATE stat_value = VALUES(stat_value);

-- ============================================
-- SAMPLE TASKS
-- ============================================
INSERT INTO tasks (task_id, title, description, reward, icon, task_type, requires_channel, channel_username, sort_order) VALUES
    ('join_channel', 'Join Our Channel', 'Join the official DogeQuest Telegram channel', 0.02, 'channel', 'telegram', 1, '@DogeQuest', 1),
    ('invite_friend', 'Invite a Friend', 'Share your referral link and invite new players', 0.05, 'users', 'social', 0, NULL, 2),
    ('daily_quest', 'Complete Daily Check-In', 'Claim your daily reward to maintain your streak', 0.01, 'calendar', 'daily', 0, NULL, 3)
ON DUPLICATE KEY UPDATE title = VALUES(title);
