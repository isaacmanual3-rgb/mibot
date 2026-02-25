"""
database.py - Doge Pixel Database Operations
Clean, optimized DOGE-only database layer
"""

import os
import json
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
import mysql.connector
from mysql.connector import pooling

logger = logging.getLogger(__name__)

# Database Configuration
# Supports Railway (MYSQL_URL or MYSQLDATABASE_URL) and manual env vars
def _build_db_config():
    import urllib.parse
    # Railway MySQL plugin exposes MYSQL_URL or MYSQLDATABASE_URL
    url = os.environ.get('MYSQL_URL') or os.environ.get('MYSQLDATABASE_URL') or os.environ.get('DATABASE_URL', '')
    if url and url.startswith('mysql'):
        parsed = urllib.parse.urlparse(url)
        return {
            'host':      parsed.hostname,
            'port':      parsed.port or 3306,
            'user':      parsed.username,
            'password':  parsed.password,
            'database':  parsed.path.lstrip('/'),
            'charset':   'utf8mb4',
            'collation': 'utf8mb4_unicode_ci',
            'autocommit': True,
            'pool_name': 'dogepixel_pool',
            'pool_size': 5,
        }
    # Fallback: individual env vars (PythonAnywhere / manual)
    return {
        'host':      os.environ.get('DB_HOST', 'localhost'),
        'port':      int(os.environ.get('DB_PORT', 3306)),
        'user':      os.environ.get('DB_USER', 'root'),
        'password':  os.environ.get('DB_PASSWORD', ''),
        'database':  os.environ.get('DB_NAME', 'dogepixel'),
        'charset':   'utf8mb4',
        'collation': 'utf8mb4_unicode_ci',
        'autocommit': True,
        'pool_name': 'dogepixel_pool',
        'pool_size': 5,
    }

DB_CONFIG = _build_db_config()

# Connection Pool
_pool = None

def get_pool():
    """Get or create connection pool"""
    global _pool
    if _pool is None:
        try:
            _pool = pooling.MySQLConnectionPool(**DB_CONFIG)
            logger.info("Database pool created successfully")
        except Exception as e:
            logger.error(f"Failed to create pool: {e}")
            raise
    return _pool

def get_connection():
    """Get connection from pool"""
    return get_pool().get_connection()

def execute_query(query, params=None, fetch_one=False, fetch_all=False):
    """Execute a database query"""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())

        if fetch_one:
            return cursor.fetchone()
        elif fetch_all:
            return cursor.fetchall()
        else:
            conn.commit()
            return cursor.lastrowid
    except Exception as e:
        logger.error(f"Query error: {e}\nQuery: {query}\nParams: {params}")
        if conn:
            conn.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# ============================================
# USER OPERATIONS
# ============================================

def get_user(user_id):
    """Get user by Telegram ID"""
    query = "SELECT * FROM users WHERE user_id = %s"
    user = execute_query(query, (str(user_id),), fetch_one=True)
    if user and user.get('completed_tasks'):
        if isinstance(user['completed_tasks'], str):
            try:
                user['completed_tasks'] = json.loads(user['completed_tasks'])
            except:
                user['completed_tasks'] = []
    return user

def create_user(user_id, username=None, first_name='Player', referred_by=None):
    """Create a new user"""
    query = """
        INSERT INTO users (user_id, username, first_name, referred_by, completed_tasks)
        VALUES (%s, %s, %s, %s, '[]')
        ON DUPLICATE KEY UPDATE
            username = COALESCE(VALUES(username), username),
            first_name = COALESCE(VALUES(first_name), first_name)
    """
    execute_query(query, (str(user_id), username, first_name, referred_by))

    # Update stats
    increment_stat('total_users')

    return get_user(user_id)

def update_user(user_id, **kwargs):
    """Update user fields"""
    if not kwargs:
        return

    set_clauses = []
    values = []

    for key, value in kwargs.items():
        if key == 'completed_tasks' and isinstance(value, list):
            value = json.dumps(value)
        set_clauses.append(f"{key} = %s")
        values.append(value)

    values.append(str(user_id))
    query = f"UPDATE users SET {', '.join(set_clauses)} WHERE user_id = %s"
    execute_query(query, tuple(values))

def get_all_users(limit=100, offset=0):
    """Get paginated users"""
    query = "SELECT * FROM users ORDER BY created_at DESC LIMIT %s OFFSET %s"
    return execute_query(query, (limit, offset), fetch_all=True) or []

def get_users_count():
    """Get total user count"""
    result = execute_query("SELECT COUNT(*) as count FROM users", fetch_one=True)
    return result['count'] if result else 0

def ban_user(user_id, reason=None):
    """Ban a user"""
    update_user(user_id, banned=1, ban_reason=reason)

def unban_user(user_id):
    """Unban a user"""
    update_user(user_id, banned=0, ban_reason=None)

# ============================================
# BALANCE OPERATIONS
# ============================================

def update_balance(user_id, amount, action, description=None):
    """Update user DOGE balance with history"""
    user = get_user(user_id)
    if not user:
        return False

    balance_before = Decimal(str(user.get('doge_balance', 0)))
    balance_after = balance_before + Decimal(str(amount))

    if balance_after < 0:
        return False

    # Update balance
    execute_query(
        "UPDATE users SET doge_balance = %s, total_earned = total_earned + %s WHERE user_id = %s",
        (float(balance_after), max(0, float(amount)), str(user_id))
    )

    # Record history
    execute_query("""
        INSERT INTO balance_history (user_id, action, amount, balance_before, balance_after, description)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (str(user_id), action, float(amount), float(balance_before), float(balance_after), description))

    return True

def get_balance_history(user_id, limit=20):
    """Get user balance history"""
    query = """
        SELECT * FROM balance_history
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT %s
    """
    return execute_query(query, (str(user_id), limit), fetch_all=True) or []

# ============================================
# DAILY CHECK-IN OPERATIONS
# ============================================

def get_checkin_status(user_id):
    """Get user's daily check-in status"""
    user = get_user(user_id)
    if not user:
        return None

    today = date.today()
    last_checkin = user.get('last_checkin')
    streak = user.get('checkin_streak', 0)

    # Check if already claimed today
    can_claim = True
    if last_checkin:
        if isinstance(last_checkin, str):
            last_checkin = datetime.strptime(last_checkin, '%Y-%m-%d').date()
        elif isinstance(last_checkin, datetime):
            last_checkin = last_checkin.date()

        if last_checkin == today:
            can_claim = False
        elif last_checkin < today - timedelta(days=1):
            streak = 0  # Streak broken

    # Calculate rewards
    base_reward = float(get_config('daily_base_reward', '0.01'))
    streak_bonus = float(get_config('daily_streak_bonus', '0.002'))
    max_bonus = float(get_config('daily_max_streak_bonus', '0.05'))

    bonus = min(streak * streak_bonus, max_bonus)
    total_reward = base_reward + bonus

    return {
        'can_claim': can_claim,
        'streak': streak,
        'last_checkin': last_checkin,
        'base_reward': base_reward,
        'streak_bonus': bonus,
        'total_reward': total_reward,
        'total_checkins': user.get('total_checkins', 0),
        'longest_streak': user.get('longest_streak', 0)
    }

def claim_daily_checkin(user_id):
    """Process daily check-in claim"""
    status = get_checkin_status(user_id)
    if not status or not status['can_claim']:
        return None

    user = get_user(user_id)
    today = date.today()

    # Calculate new streak
    new_streak = status['streak'] + 1
    longest_streak = max(new_streak, user.get('longest_streak', 0))

    # Record check-in
    execute_query("""
        INSERT INTO daily_checkins (user_id, checkin_date, day_number, reward, streak_bonus, total_reward)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (str(user_id), today, new_streak, status['base_reward'],
          status['streak_bonus'], status['total_reward']))

    # Update user
    execute_query("""
        UPDATE users SET
            checkin_streak = %s,
            last_checkin = %s,
            longest_streak = %s,
            total_checkins = total_checkins + 1
        WHERE user_id = %s
    """, (new_streak, today, longest_streak, str(user_id)))

    # Add balance
    update_balance(user_id, status['total_reward'], 'daily_checkin',
                   f"Day {new_streak} check-in reward")

    # Update stats
    increment_stat('total_checkins')

    return {
        'reward': status['total_reward'],
        'streak': new_streak,
        'streak_bonus': status['streak_bonus']
    }

def get_checkin_history(user_id, days=7):
    """Get recent check-in history"""
    query = """
        SELECT * FROM daily_checkins
        WHERE user_id = %s
        ORDER BY checkin_date DESC
        LIMIT %s
    """
    return execute_query(query, (str(user_id), days), fetch_all=True) or []

# ============================================
# REFERRAL OPERATIONS
# ============================================

def add_referral(referrer_id, referred_id, referred_username=None, referred_first_name='Player'):
    """Add a new referral"""
    try:
        execute_query("""
            INSERT INTO referrals (referrer_id, referred_id, referred_username, referred_first_name)
            VALUES (%s, %s, %s, %s)
        """, (str(referrer_id), str(referred_id), referred_username, referred_first_name))

        # Update referral count
        execute_query(
            "UPDATE users SET referral_count = referral_count + 1 WHERE user_id = %s",
            (str(referrer_id),)
        )
        return True
    except Exception as e:
        logger.error(f"Failed to add referral: {e}")
        return False

def validate_referral(referrer_id, referred_id):
    """Validate a referral and pay bonus"""
    bonus = float(get_config('referral_bonus', '0.05'))

    # Update referral
    execute_query("""
        UPDATE referrals
        SET validated = 1, bonus_paid = %s, validated_at = NOW()
        WHERE referrer_id = %s AND referred_id = %s AND validated = 0
    """, (bonus, str(referrer_id), str(referred_id)))

    # Update referrer
    execute_query("""
        UPDATE users
        SET validated_referrals = validated_referrals + 1,
            referral_earnings = referral_earnings + %s
        WHERE user_id = %s
    """, (bonus, str(referrer_id)))

    # Pay bonus
    update_balance(referrer_id, bonus, 'referral_bonus',
                   f"Referral bonus for inviting user")

    return True


def pay_referral_commission(user_id, amount, source):
    """Pay 5% lifetime commission to the referrer whenever user earns from mining or deposits.
    Only pays if a validated referral exists (i.e. referred user already purchased a plan)."""
    if not amount or float(amount) <= 0:
        return

    user = get_user(user_id)
    if not user or not user.get('referred_by'):
        return

    referrer_id = user['referred_by']

    # Only pay if the referral is validated (plan was purchased)
    ref_row = execute_query(
        "SELECT validated FROM referrals WHERE referrer_id = %s AND referred_id = %s LIMIT 1",
        (str(referrer_id), str(user_id)), fetch_one=True
    )
    if not ref_row or not ref_row.get('validated'):
        return

    commission_pct = float(get_config('referral_commission_pct', '5')) / 100.0
    commission = round(float(amount) * commission_pct, 8)
    if commission <= 0:
        return

    # Credit referrer and track earnings
    update_balance(referrer_id, commission, 'referral_commission',
                   f"5% commission from {source} of user {user_id}")
    execute_query(
        "UPDATE users SET referral_earnings = referral_earnings + %s WHERE user_id = %s",
        (commission, str(referrer_id))
    )
    logger.info(f"Referral commission: {commission:.8f} TON → referrer={referrer_id} from {source} of user={user_id}")

def get_referrals(user_id, limit=50):
    """Get user's referrals"""
    query = """
        SELECT r.*, u.doge_balance, u.last_active,
               r.is_fraud AS referred_fraud
        FROM referrals r
        LEFT JOIN users u ON r.referred_id = u.user_id
        WHERE r.referrer_id = %s
        ORDER BY r.created_at DESC
        LIMIT %s
    """
    return execute_query(query, (str(user_id), limit), fetch_all=True) or []

def get_referral_stats(user_id):
    """Get referral statistics"""
    user = get_user(user_id)
    if not user:
        return None

    return {
        'total_referrals': user.get('referral_count', 0),
        'validated_referrals': user.get('validated_referrals', 0),
        'total_earnings': float(user.get('referral_earnings', 0))
    }

# ============================================
# TASK OPERATIONS
# ============================================

def _normalize_task(t):
    """Normalize task field names for templates"""
    if not t:
        return t
    t['id']         = t.get('id') or t.get('task_id')
    t['link']       = t.get('url', '') or ''
    t['channel_id'] = t.get('channel_username', '') or ''
    t['is_active']  = bool(t.get('active', 1))
    t['completions']= t.get('current_completions', 0)
    t['category']   = t.get('task_type', 'telegram')
    t['locked']     = False  # default, can be overridden
    return t

def get_all_tasks(active_only=True):
    """Get all tasks"""
    if active_only:
        query = "SELECT * FROM tasks WHERE active = 1 ORDER BY sort_order ASC"
    else:
        query = "SELECT * FROM tasks ORDER BY sort_order ASC"
    tasks = execute_query(query, fetch_all=True) or []
    return [_normalize_task(t) for t in tasks]

def get_task(task_id):
    """Get task by ID or numeric id"""
    # Try by task_id (string) first, then by numeric id
    result = execute_query("SELECT * FROM tasks WHERE task_id = %s", (task_id,), fetch_one=True)
    if not result:
        result = execute_query("SELECT * FROM tasks WHERE id = %s", (task_id,), fetch_one=True)
    return _normalize_task(result)

def create_task(task_id, title, description, reward, url=None, icon='star',
                task_type='telegram', requires_channel=False, channel_username=None):
    """Create a new task"""
    query = """
        INSERT INTO tasks (task_id, title, description, reward, url, icon,
                          task_type, requires_channel, channel_username)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    execute_query(query, (task_id, title, description, float(reward), url, icon,
                         task_type, 1 if requires_channel else 0, channel_username))
    return get_task(task_id)

def update_task(task_id, **kwargs):
    """Update task fields"""
    if not kwargs:
        return

    set_clauses = []
    values = []

    for key, value in kwargs.items():
        set_clauses.append(f"{key} = %s")
        values.append(value)

    values.append(task_id)
    query = f"UPDATE tasks SET {', '.join(set_clauses)} WHERE task_id = %s"
    execute_query(query, tuple(values))

def delete_task(task_id):
    """Delete a task"""
    execute_query("DELETE FROM tasks WHERE task_id = %s", (task_id,))

def is_task_completed(user_id, task_id):
    """Check if user completed a task"""
    query = "SELECT id FROM task_completions WHERE user_id = %s AND task_id = %s"
    result = execute_query(query, (str(user_id), task_id), fetch_one=True)
    return result is not None

def complete_task(user_id, task_id):
    """Complete a task and reward user"""
    if is_task_completed(user_id, task_id):
        return None

    task = get_task(task_id)
    if not task or not task.get('active'):
        return None

    reward = float(task.get('reward', 0))

    # Record completion
    execute_query("""
        INSERT INTO task_completions (user_id, task_id, reward_amount)
        VALUES (%s, %s, %s)
    """, (str(user_id), task_id, reward))

    # Update task completions count
    execute_query(
        "UPDATE tasks SET current_completions = current_completions + 1 WHERE task_id = %s",
        (task_id,)
    )

    # Update user completed_tasks JSON
    user = get_user(user_id)
    completed = user.get('completed_tasks', []) or []
    if task_id not in completed:
        completed.append(task_id)
        update_user(user_id, completed_tasks=completed)

    # Pay reward
    if reward > 0:
        update_balance(user_id, reward, 'task_reward', f"Completed: {task['title']}")

    # Update stats
    increment_stat('total_tasks_completed')

    return {'reward': reward, 'task': task}

def get_user_tasks_status(user_id):
    """Get all tasks with user completion status"""
    tasks = get_all_tasks()
    user = get_user(user_id)
    completed = user.get('completed_tasks', []) or [] if user else []
    # Also check task_completions table as source of truth
    done_rows = execute_query(
        "SELECT task_id FROM task_completions WHERE user_id = %s",
        (str(user_id),), fetch_all=True
    ) or []
    done_ids = set(r['task_id'] for r in done_rows) | set(completed)

    for task in tasks:
        task['completed'] = task['task_id'] in done_ids

    return tasks

# ============================================
# WITHDRAWAL OPERATIONS
# ============================================

def create_withdrawal(user_id, amount, wallet_address):
    """Create a withdrawal request"""
    import secrets

    user = get_user(user_id)
    if not user:
        return None

    balance = float(user.get('doge_balance', 0))
    fee = float(get_config('withdrawal_fee', '0.5'))
    min_amount = float(get_config('min_withdrawal', '1.0'))

    if amount < min_amount:
        return {'error': f'Minimum withdrawal is {min_amount} DOGE'}

    if amount > balance:
        return {'error': 'Insufficient balance'}

    net_amount = amount - fee
    withdrawal_id = f"WD{secrets.token_hex(8).upper()}"

    # Deduct from balance
    update_balance(user_id, -amount, 'withdrawal', f"Withdrawal request: {withdrawal_id}")

    # Create withdrawal record
    execute_query("""
        INSERT INTO withdrawals (withdrawal_id, user_id, amount, fee, net_amount, wallet_address)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (withdrawal_id, str(user_id), amount, fee, net_amount, wallet_address))

    increment_stat('total_withdrawals')

    return {
        'withdrawal_id': withdrawal_id,
        'amount': amount,
        'fee': fee,
        'net_amount': net_amount
    }

def create_ton_withdrawal(user_id, doge_amount, ton_wallet):
    """Create a TON withdrawal request - deducts DOGE, admin sends TON manually"""
    import secrets

    user = get_user(user_id)
    if not user:
        return {'error': 'User not found'}

    balance = float(user.get('doge_balance', 0))
    min_doge = float(get_config('ton_withdrawal_min_doge', '0.01'))
    fee_pct  = float(get_config('ton_withdrawal_fee_percent', '2'))
    rate     = float(get_config('doge_to_ton_rate', '100'))  # DOGE per 1 TON → 1 DOGE = 1/rate TON

    if doge_amount < min_doge:
        return {'error': 'api_min_withdrawal', 'amount': str(min_doge)}
    if doge_amount > balance:
        return {'error': 'api_insuf_balance'}

    fee_doge   = round(doge_amount * fee_pct / 100, 8)
    net_doge   = round(doge_amount - fee_doge, 8)
    ton_amount = round(net_doge / rate, 9)

    withdrawal_id = f"TW{secrets.token_hex(8).upper()}"

    update_balance(user_id, -doge_amount, 'withdrawal_ton', f"Retiro TON: {withdrawal_id}")
    save_user_ton_wallet(user_id, ton_wallet)

    execute_query("""
        INSERT INTO withdrawals
          (withdrawal_id, user_id, amount, fee, net_amount, wallet_address,
           withdrawal_type, ton_wallet_address, ton_amount)
        VALUES (%s, %s, %s, %s, %s, %s, 'ton', %s, %s)
    """, (withdrawal_id, str(user_id), doge_amount, fee_doge, net_doge,
          ton_wallet, ton_wallet, ton_amount))

    return {
        'withdrawal_id': withdrawal_id,
        'doge_amount':   doge_amount,
        'fee_doge':      fee_doge,
        'net_doge':      net_doge,
        'ton_amount':    ton_amount,
        'ton_wallet':    ton_wallet,
    }


def get_user_withdrawals(user_id, limit=20):
    """Get user's withdrawal history"""
    query = """
        SELECT * FROM withdrawals
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT %s
    """
    return execute_query(query, (str(user_id), limit), fetch_all=True) or []

def get_pending_withdrawals():
    """Get all pending withdrawals"""
    query = "SELECT * FROM withdrawals WHERE status = 'pending' ORDER BY created_at ASC"
    return execute_query(query, fetch_all=True) or []

def update_withdrawal(withdrawal_id, status, tx_hash=None, admin_note=None):
    """Update withdrawal status"""
    execute_query("""
        UPDATE withdrawals
        SET status = %s, tx_hash = %s, admin_note = %s, processed_at = NOW()
        WHERE withdrawal_id = %s
    """, (status, tx_hash, admin_note, str(withdrawal_id)))

# ============================================
# PROMO CODE OPERATIONS
# ============================================

def get_all_promo_codes():
    """Get all promo codes with normalized fields"""
    codes = execute_query("SELECT * FROM promo_codes ORDER BY created_at DESC", fetch_all=True) or []

    # Normalize field names for templates
    for code in codes:
        code['uses'] = code.get('current_uses', 0)
        # Determine status
        if not code.get('active'):
            code['status'] = 'expired'
        elif code.get('max_uses') and code.get('current_uses', 0) >= code['max_uses']:
            code['status'] = 'depleted'
        elif code.get('expires_at') and datetime.now() > code['expires_at']:
            code['status'] = 'expired'
        else:
            code['status'] = 'active'

    return codes

def get_promo_code(code):
    """Get promo code by code with normalized fields"""
    query = "SELECT * FROM promo_codes WHERE code = %s"
    result = execute_query(query, (code.upper(),), fetch_one=True)

    if result:
        result['uses'] = result.get('current_uses', 0)
        # Determine status
        if not result.get('active'):
            result['status'] = 'expired'
        elif result.get('max_uses') and result.get('current_uses', 0) >= result['max_uses']:
            result['status'] = 'depleted'
        elif result.get('expires_at') and datetime.now() > result['expires_at']:
            result['status'] = 'expired'
        else:
            result['status'] = 'active'

    return result

def create_promo_code(code, reward, max_uses=None, expires_at=None, description=None):
    """Create a promo code"""
    execute_query("""
        INSERT INTO promo_codes (code, reward, max_uses, expires_at)
        VALUES (%s, %s, %s, %s)
    """, (code.upper(), float(reward), max_uses, expires_at))
    return get_promo_code(code)

def redeem_promo_code(user_id, code):
    """Redeem a promo code"""
    promo = get_promo_code(code)
    if not promo:
        return {'error': 'Invalid code'}

    if not promo.get('active'):
        return {'error': 'Code is no longer active'}

    if promo.get('expires_at') and datetime.now() > promo['expires_at']:
        return {'error': 'Code has expired'}

    if promo.get('max_uses') and promo.get('current_uses', 0) >= promo['max_uses']:
        return {'error': 'Code has reached maximum uses'}

    # Check if already redeemed
    check = execute_query(
        "SELECT id FROM promo_redemptions WHERE user_id = %s AND code = %s",
        (str(user_id), code.upper()), fetch_one=True
    )
    if check:
        return {'error': 'You have already redeemed this code'}

    reward = float(promo['reward'])

    # Record redemption
    execute_query("""
        INSERT INTO promo_redemptions (user_id, code, reward)
        VALUES (%s, %s, %s)
    """, (str(user_id), code.upper(), reward))

    # Update promo usage
    execute_query(
        "UPDATE promo_codes SET current_uses = current_uses + 1 WHERE code = %s",
        (code.upper(),)
    )

    # Pay reward
    update_balance(user_id, reward, 'promo_code', f"Redeemed code: {code.upper()}")

    return {'reward': reward, 'code': code.upper()}

# ============================================
# CONFIG OPERATIONS
# ============================================

def get_config(key, default=None):
    """Get config value"""
    query = "SELECT config_value FROM config WHERE config_key = %s"
    result = execute_query(query, (key,), fetch_one=True)
    return result['config_value'] if result else default

def set_config(key, value):
    """Set config value"""
    execute_query("""
        INSERT INTO config (config_key, config_value) VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE config_value = VALUES(config_value)
    """, (key, str(value)))

def get_all_config():
    """Get all config values"""
    results = execute_query("SELECT * FROM config", fetch_all=True) or []
    return {r['config_key']: r['config_value'] for r in results}

# ============================================
# STATS OPERATIONS
# ============================================

def get_stat(key, default=0):
    """Get stat value"""
    query = "SELECT stat_value FROM stats WHERE stat_key = %s"
    result = execute_query(query, (key,), fetch_one=True)
    return result['stat_value'] if result else default

def set_stat(key, value):
    """Set stat value"""
    execute_query("""
        INSERT INTO stats (stat_key, stat_value) VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE stat_value = VALUES(stat_value)
    """, (key, int(value)))

def increment_stat(key, amount=1):
    """Increment a stat"""
    execute_query("""
        INSERT INTO stats (stat_key, stat_value) VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE stat_value = stat_value + VALUES(stat_value)
    """, (key, amount))

def get_all_stats():
    """Get all stats"""
    results = execute_query("SELECT * FROM stats", fetch_all=True) or []
    return {r['stat_key']: r['stat_value'] for r in results}

# ============================================
# IP TRACKING
# ============================================

def record_user_ip(user_id, ip_address):
    """Record user IP address"""
    if not ip_address:
        return

    execute_query("""
        INSERT INTO user_ips (user_id, ip_address, times_seen)
        VALUES (%s, %s, 1)
        ON DUPLICATE KEY UPDATE
            times_seen = times_seen + 1,
            last_seen = NOW()
    """, (str(user_id), ip_address))

    update_user(user_id, last_ip=ip_address, last_active=datetime.now())

def is_ip_banned(ip_address):
    """Check if IP is banned"""
    if not ip_address:
        return False
    result = execute_query(
        "SELECT id FROM ip_bans WHERE ip_address = %s",
        (ip_address,), fetch_one=True
    )
    return result is not None

def ban_ip(ip_address, reason=None):
    """Ban an IP address"""
    execute_query("""
        INSERT INTO ip_bans (ip_address, reason) VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE reason = VALUES(reason)
    """, (ip_address, reason))

def unban_ip(ip_address):
    """Unban an IP address"""
    execute_query("DELETE FROM ip_bans WHERE ip_address = %s", (ip_address,))

# ============================================
# LEADERBOARD OPERATIONS
# ============================================

def get_top_earners(limit=10):
    """Get top earners by total DOGE earned"""
    query = """
        SELECT user_id, username, first_name, total_earned, doge_balance
        FROM users
        WHERE banned = 0
        ORDER BY total_earned DESC
        LIMIT %s
    """
    return execute_query(query, (limit,), fetch_all=True) or []

def get_top_referrers(limit=10):
    """Get top referrers"""
    query = """
        SELECT user_id, username, first_name, validated_referrals, referral_earnings
        FROM users
        WHERE banned = 0
        ORDER BY validated_referrals DESC
        LIMIT %s
    """
    return execute_query(query, (limit,), fetch_all=True) or []

def get_top_streakers(limit=10):
    """Get users with longest check-in streaks"""
    query = """
        SELECT user_id, username, first_name, checkin_streak, longest_streak
        FROM users
        WHERE banned = 0
        ORDER BY longest_streak DESC
        LIMIT %s
    """
    return execute_query(query, (limit,), fetch_all=True) or []

# ============================================
# PROMO CODE MANAGEMENT (Extended)
# ============================================

def get_promo_stats():
    """Get promo code statistics"""
    stats = {
        'total_codes': 0,
        'active_codes': 0,
        'total_uses': 0,
        'total_distributed': 0
    }

    result = execute_query("SELECT COUNT(*) as count FROM promo_codes", fetch_one=True)
    if result:
        stats['total_codes'] = result['count']

    # active column = 1 means active
    result = execute_query(
        "SELECT COUNT(*) as count FROM promo_codes WHERE active = 1",
        fetch_one=True
    )
    if result:
        stats['active_codes'] = result['count']

    result = execute_query("SELECT SUM(current_uses) as total FROM promo_codes", fetch_one=True)
    if result and result['total']:
        stats['total_uses'] = int(result['total'])

    result = execute_query(
        "SELECT SUM(reward * current_uses) as total FROM promo_codes",
        fetch_one=True
    )
    if result and result['total']:
        stats['total_distributed'] = float(result['total'])

    return stats

def get_recent_redemptions(limit=10):
    """Get recent promo code redemptions"""
    query = """
        SELECT pr.*, u.first_name, u.username, pc.reward
        FROM promo_redemptions pr
        JOIN users u ON pr.user_id = u.user_id
        JOIN promo_codes pc ON pr.code = pc.code
        ORDER BY pr.redeemed_at DESC
        LIMIT %s
    """
    return execute_query(query, (limit,), fetch_all=True) or []

def update_promo_status(code, status):
    """Update promo code status"""
    # Convert status to active flag
    active = 1 if status == 'active' else 0
    query = "UPDATE promo_codes SET active = %s WHERE code = %s"
    execute_query(query, (active, code))
    return True

def delete_promo_code(code):
    """Delete a promo code"""
    # First delete redemptions
    execute_query("DELETE FROM promo_redemptions WHERE code = %s", (code,))
    # Then delete the code
    execute_query("DELETE FROM promo_codes WHERE code = %s", (code,))
    return True

def reset_all_task_completions():
    """Reset all task completions - allows users to redo tasks"""
    result = execute_query("SELECT COUNT(*) as count FROM task_completions", fetch_one=True)
    count = result['count'] if result else 0

    execute_query("DELETE FROM task_completions")
    return count

# ============================================
# MINING OPERATIONS
# ============================================

def get_all_mining_plans(active_only=True):
    """Get all mining plans"""
    if active_only:
        query = "SELECT * FROM mining_plans WHERE active = 1 ORDER BY price ASC"
    else:
        query = "SELECT * FROM mining_plans ORDER BY price ASC"
    return execute_query(query, fetch_all=True) or []

def get_mining_plan(plan_id):
    """Get a specific mining plan"""
    query = "SELECT * FROM mining_plans WHERE id = %s"
    return execute_query(query, (plan_id,), fetch_one=True)

def purchase_mining_machine(user_id, plan_id):
    """Purchase a mining machine — free plans skip balance check, 30-day cooldown per plan"""
    import uuid

    plan = get_mining_plan(plan_id)
    if not plan:
        return {'success': False, 'err_code': 'api_plan_not_found'}
    if not plan.get('active'):
        return {'success': False, 'err_code': 'api_plan_unavailable'}

    user = get_user(user_id)
    if not user:
        return {'success': False, 'err_code': 'api_user_not_found'}

    price = float(plan['price'])
    is_free = price == 0.0

    # ── One-time-only check: never activated before (all history) ──
    is_one_time = int(plan.get('one_time_only', 0)) == 1
    if is_one_time:
        ever_used = execute_query(
            "SELECT id FROM user_mining_machines WHERE user_id=%s AND plan_id=%s LIMIT 1",
            (str(user_id), plan_id), fetch_one=True
        )
        if ever_used:
            return {'success': False, 'err_code': 'api_free_plan_once', 'plan_name': plan['name']}

    # ── 30-day cooldown: one active machine per plan at a time ──
    existing = execute_query(
        "SELECT expires_at FROM user_mining_machines WHERE user_id=%s AND plan_id=%s AND expires_at > NOW() ORDER BY expires_at DESC LIMIT 1",
        (str(user_id), plan_id), fetch_one=True
    )
    if existing:
        exp = existing['expires_at']
        return {'success': False, 'err_code': 'api_plan_active_until', 'date': exp.strftime("%d/%m/%Y")}

    # ── Balance check (skip for free plans) ──
    if not is_free:
        balance = float(user.get('doge_balance', 0))
        if balance < price:
            return {'success': False, 'err_code': 'api_insufficient_funds', 'amount': f'{price:.2f}'}
        update_balance(user_id, -price, 'mining_purchase', f'Plan {plan["name"]} activated')

    # ── Create machine ──
    machine_id = f"machine_{uuid.uuid4().hex[:12]}"
    duration_days = plan.get('duration_days', 30)
    expires_at = datetime.now() + timedelta(days=duration_days)

    execute_query("""
        INSERT INTO user_mining_machines
        (machine_id, user_id, plan_id, plan_name, hourly_rate, last_claim_at, expires_at)
        VALUES (%s, %s, %s, %s, %s, NOW(), %s)
    """, (machine_id, str(user_id), plan_id, plan['name'], plan['hourly_rate'], expires_at))

    action = 'free' if is_free else f'paid_{price:.2f}'
    return {
        'success': True,
        'err_code': 'api_plan_activated_free' if is_free else 'api_plan_activated_paid',
        'plan_name': plan['name'],
        'price': f'{price:.2f}',
        'machine_id': machine_id
    }

def get_user_machines(user_id):
    """Get user's active mining machines"""
    query = """
        SELECT * FROM user_mining_machines
        WHERE user_id = %s AND expires_at > NOW()
        ORDER BY purchased_at DESC
    """
    return execute_query(query, (str(user_id),), fetch_all=True) or []

def get_user_mining_stats(user_id):
    """Get user's mining statistics"""
    machines = get_user_machines(user_id)

    total_machines = len(machines)
    total_hourly_rate = sum(float(m.get('hourly_rate', 0)) for m in machines)
    total_mined = sum(float(m.get('total_mined', 0)) for m in machines)

    return {
        'total_machines': total_machines,
        'total_hourly_rate': total_hourly_rate,
        'total_mined': total_mined
    }

def get_pending_mining_rewards(user_id):
    """Calculate pending mining rewards"""
    machines = get_user_machines(user_id)

    total_pending = 0
    now = datetime.now()

    for machine in machines:
        last_claim = machine.get('last_claim_at')
        if last_claim:
            hours_elapsed = (now - last_claim).total_seconds() / 3600
            hourly_rate = float(machine.get('hourly_rate', 0))
            pending = hours_elapsed * hourly_rate
            total_pending += pending

    return total_pending

def claim_mining_rewards(user_id):
    """Claim all pending mining rewards"""
    machines = get_user_machines(user_id)

    if not machines:
        return {'success': False, 'err_code': 'api_no_machines'}

    total_claimed = 0
    now = datetime.now()

    for machine in machines:
        last_claim = machine.get('last_claim_at')
        if last_claim:
            hours_elapsed = (now - last_claim).total_seconds() / 3600
            hourly_rate = float(machine.get('hourly_rate', 0))
            pending = hours_elapsed * hourly_rate

            if pending > 0:
                total_claimed += pending

                # Update machine
                query = """
                    UPDATE user_mining_machines
                    SET last_claim_at = NOW(), total_mined = total_mined + %s
                    WHERE id = %s
                """
                execute_query(query, (pending, machine['id']))

    if total_claimed > 0:
        # Credit to user balance
        update_balance(user_id, total_claimed, 'mining_reward', 'Mining rewards claimed')
        increment_stat('total_doge_distributed', int(total_claimed * 100000000))

        # Pay 5% lifetime commission to referrer (if any)
        pay_referral_commission(user_id, total_claimed, 'mining')

        return {
            'success': True,
            'err_code': 'api_claimed_rewards',
            'claimed': f'{total_claimed:.8f}',
            'amount': total_claimed
        }

    return {'success': False, 'err_code': 'api_no_rewards'}

def process_mining_rewards(user_id):
    """Process mining rewards (background task)"""
    return claim_mining_rewards(user_id)

def create_mining_plan(name, tier, price, hourly_rate, duration_days=30, description=None):
    """Create a new mining plan"""
    query = """
        INSERT INTO mining_plans (name, tier, price, hourly_rate, duration_days, description)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    return execute_query(query, (name, tier, price, hourly_rate, duration_days, description))

def delete_mining_plan(plan_id):
    """Delete a mining plan"""
    query = "UPDATE mining_plans SET active = 0 WHERE id = %s"
    execute_query(query, (plan_id,))
    return True

def update_mining_plan(plan_id, name=None, price=None, hourly_rate=None, duration_days=None, description=None, active=None, one_time_only=None):
    """Update fields of an existing mining plan"""
    fields = []
    values = []
    if name is not None and str(name).strip() != '':
        fields.append("name = %s"); values.append(str(name).strip())
    if price is not None and str(price).strip() != '':
        fields.append("price = %s"); values.append(float(price))
    if hourly_rate is not None and str(hourly_rate).strip() != '':
        fields.append("hourly_rate = %s"); values.append(float(hourly_rate))
    if duration_days is not None and str(duration_days).strip() != '':
        fields.append("duration_days = %s"); values.append(int(duration_days))
    if description is not None:
        fields.append("description = %s"); values.append(str(description))
    if active is not None and str(active).strip() != '':
        fields.append("active = %s"); values.append(int(active))
    if one_time_only is not None and str(one_time_only).strip() != '':
        fields.append("one_time_only = %s"); values.append(int(one_time_only))
    if not fields:
        return None
    values.append(plan_id)
    query = f"UPDATE mining_plans SET {', '.join(fields)} WHERE id = %s"
    execute_query(query, tuple(values))
    return True

def get_mining_stats():
    """Get global mining statistics"""
    stats = {
        'total_machines': 0,
        'active_miners': 0,
        'total_mined': 0
    }

    # Total machines
    result = execute_query(
        "SELECT COUNT(*) as count FROM user_mining_machines WHERE expires_at > NOW()",
        fetch_one=True
    )
    if result:
        stats['total_machines'] = result['count']

    # Active miners (unique users with machines)
    result = execute_query(
        "SELECT COUNT(DISTINCT user_id) as count FROM user_mining_machines WHERE expires_at > NOW()",
        fetch_one=True
    )
    if result:
        stats['active_miners'] = result['count']

    # Total mined
    result = execute_query(
        "SELECT SUM(total_mined) as total FROM user_mining_machines",
        fetch_one=True
    )
    if result and result['total']:
        stats['total_mined'] = float(result['total'])

    return stats

# ============================================
# TON DEPOSIT FUNCTIONS
# ============================================

import logging as _ton_logger
_ton_log = _ton_logger.getLogger(__name__)

def _ton_column_exists(table, column):
    """Check if a column exists in a table"""
    try:
        result = execute_query(
            "SELECT COUNT(*) as cnt FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s",
            (table, column), fetch_one=True
        )
        return result and result.get('cnt', 0) > 0
    except Exception:
        return False

def _ton_table_exists(table):
    """Check if a table exists in current database"""
    try:
        result = execute_query(
            "SELECT COUNT(*) as cnt FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s",
            (table,), fetch_one=True
        )
        return result and result.get('cnt', 0) > 0
    except Exception:
        return False

def init_ton_tables():
    """
    Create TON tables and columns if they don't exist.
    Uses information_schema checks instead of IF NOT EXISTS
    to support older MySQL versions on PythonAnywhere.
    """
    # 1. Create ton_deposits table if missing
    if not _ton_table_exists('ton_deposits'):
        execute_query("""
            CREATE TABLE ton_deposits (
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
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        _ton_log.info("✓ Created ton_deposits table")

    # 2. Add ton_wallet column to users if missing
    if not _ton_column_exists('users', 'ton_wallet'):
        execute_query("ALTER TABLE users ADD COLUMN ton_wallet VARCHAR(100) DEFAULT NULL")
        _ton_log.info("✓ Added ton_wallet column to users")

    # 2b. Add ton_deposit_address — unique TON deposit address per user
    if not _ton_column_exists('users', 'ton_deposit_address'):
        execute_query("ALTER TABLE users ADD COLUMN ton_deposit_address VARCHAR(200) DEFAULT NULL")
        _ton_log.info("✓ Added ton_deposit_address column to users")

    # 2c. Add memo column to ton_deposits for matching incoming txs
    if not _ton_column_exists('ton_deposits', 'memo'):
        execute_query("ALTER TABLE ton_deposits ADD COLUMN memo VARCHAR(50) DEFAULT NULL")
        _ton_log.info("✓ Added memo column to ton_deposits")

    # 3. Insert default TON config values if missing
    defaults = [
        ('ton_wallet_address', 'AQUI_TU_WALLET_TON'),
        ('ton_to_doge_rate', '100'),
        ('ton_min_deposit', '0.1'),
        ('ton_deposits_enabled', '1'),
        ('ton_auto_confirm', '0'),
    ]
    for key, val in defaults:
        execute_query(
            "INSERT IGNORE INTO config (config_key, config_value) VALUES (%s, %s)",
            (key, val)
        )


# Run auto-init at import time — errors are logged but won't crash the app
try:
    init_ton_tables()
    _ton_log.info("✓ TON tables ready")
except Exception as _init_err:
    _ton_log.error(f"TON table init error: {_init_err}")


# ============================================
# FULL DATABASE INITIALIZATION (Railway / fresh install)
# Creates ALL tables from scratch if they don't exist.
# Safe to run on every startup — uses IF NOT EXISTS / INSERT IGNORE.
# ============================================

def init_all_tables():
    """
    Create all tables and seed default data.
    Called automatically on startup if INIT_DB=1 env var is set,
    or always on Railway (detected via RAILWAY_ENVIRONMENT env var).
    """
    log = logging.getLogger(__name__)
    log.info("[init_all_tables] Starting full DB initialization...")

    execute_query("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id VARCHAR(50) NOT NULL UNIQUE,
            username VARCHAR(100) DEFAULT NULL,
            first_name VARCHAR(100) DEFAULT 'Player',
            doge_balance DECIMAL(20,8) DEFAULT 0.00000000,
            total_earned DECIMAL(20,8) DEFAULT 0.00000000,
            checkin_streak INT DEFAULT 0,
            last_checkin DATE DEFAULT NULL,
            longest_streak INT DEFAULT 0,
            total_checkins INT DEFAULT 0,
            referral_count INT DEFAULT 0,
            validated_referrals INT DEFAULT 0,
            referred_by VARCHAR(50) DEFAULT NULL,
            referral_earnings DECIMAL(20,8) DEFAULT 0.00000000,
            wallet_address VARCHAR(100) DEFAULT NULL,
            wallet_linked_at DATETIME DEFAULT NULL,
            ton_wallet VARCHAR(100) DEFAULT NULL,
            banned TINYINT(1) DEFAULT 0,
            ban_reason VARCHAR(255) DEFAULT NULL,
            last_ip VARCHAR(50) DEFAULT NULL,
            completed_tasks JSON DEFAULT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            last_active DATETIME DEFAULT NULL,
            INDEX idx_user_id (user_id),
            INDEX idx_username (username),
            INDEX idx_referred_by (referred_by),
            INDEX idx_banned (banned)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    log.info("✓ users")

    execute_query("""
        CREATE TABLE IF NOT EXISTS daily_checkins (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id VARCHAR(50) NOT NULL,
            checkin_date DATE NOT NULL,
            day_number INT NOT NULL,
            reward DECIMAL(10,8) NOT NULL,
            streak_bonus DECIMAL(10,8) DEFAULT 0.00000000,
            total_reward DECIMAL(10,8) NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY unique_daily_checkin (user_id, checkin_date),
            INDEX idx_user_id (user_id),
            INDEX idx_checkin_date (checkin_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    log.info("✓ daily_checkins")

    execute_query("""
        CREATE TABLE IF NOT EXISTS referrals (
            id INT AUTO_INCREMENT PRIMARY KEY,
            referrer_id VARCHAR(50) NOT NULL,
            referred_id VARCHAR(50) NOT NULL,
            referred_username VARCHAR(100) DEFAULT NULL,
            referred_first_name VARCHAR(100) DEFAULT 'Player',
            validated TINYINT(1) DEFAULT 0,
            bonus_paid DECIMAL(10,8) DEFAULT 0.00000000,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            validated_at DATETIME DEFAULT NULL,
            UNIQUE KEY unique_referral (referrer_id, referred_id),
            INDEX idx_referrer_id (referrer_id),
            INDEX idx_validated (validated)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    log.info("✓ referrals")

    execute_query("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INT AUTO_INCREMENT PRIMARY KEY,
            task_id VARCHAR(50) NOT NULL UNIQUE,
            title VARCHAR(200) NOT NULL,
            description TEXT DEFAULT NULL,
            reward DECIMAL(10,8) DEFAULT 0.00000000,
            url VARCHAR(500) DEFAULT NULL,
            icon VARCHAR(50) DEFAULT 'star',
            task_type ENUM('telegram','social','external','daily','special') DEFAULT 'telegram',
            requires_channel TINYINT(1) DEFAULT 0,
            channel_username VARCHAR(100) DEFAULT NULL,
            active TINYINT(1) DEFAULT 1,
            max_completions INT DEFAULT NULL,
            current_completions INT DEFAULT 0,
            sort_order INT DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_task_id (task_id),
            INDEX idx_active (active)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    log.info("✓ tasks")

    execute_query("""
        CREATE TABLE IF NOT EXISTS task_completions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id VARCHAR(50) NOT NULL,
            task_id VARCHAR(50) NOT NULL,
            reward_amount DECIMAL(10,8) NOT NULL,
            completed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY unique_completion (user_id, task_id),
            INDEX idx_user_id (user_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    log.info("✓ task_completions")

    execute_query("""
        CREATE TABLE IF NOT EXISTS withdrawals (
            id INT AUTO_INCREMENT PRIMARY KEY,
            withdrawal_id VARCHAR(100) NOT NULL UNIQUE,
            user_id VARCHAR(50) NOT NULL,
            amount DECIMAL(20,8) NOT NULL,
            fee DECIMAL(20,8) DEFAULT 0.00000000,
            net_amount DECIMAL(20,8) NOT NULL,
            wallet_address VARCHAR(100) NOT NULL,
            withdrawal_type VARCHAR(20) DEFAULT 'doge',
            ton_wallet_address VARCHAR(100) DEFAULT NULL,
            ton_amount DECIMAL(20,9) DEFAULT NULL,
            ton_tx_hash VARCHAR(200) DEFAULT NULL,
            status ENUM('pending','processing','completed','failed','rejected') DEFAULT 'pending',
            tx_hash VARCHAR(100) DEFAULT NULL,
            admin_note TEXT DEFAULT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            processed_at DATETIME DEFAULT NULL,
            INDEX idx_user_id (user_id),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    log.info("✓ withdrawals")

    execute_query("""
        CREATE TABLE IF NOT EXISTS ton_deposits (
            id INT AUTO_INCREMENT PRIMARY KEY,
            deposit_id VARCHAR(100) NOT NULL UNIQUE,
            user_id VARCHAR(50) NOT NULL,
            ton_amount DECIMAL(20,9) NOT NULL,
            doge_credited DECIMAL(20,8) NOT NULL,
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
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    log.info("✓ ton_deposits")

    execute_query("""
        CREATE TABLE IF NOT EXISTS mining_plans (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            tier VARCHAR(50) DEFAULT 'basic',
            price DECIMAL(20,8) NOT NULL,
            hourly_rate DECIMAL(20,8) NOT NULL,
            duration_days INT DEFAULT 30,
            description TEXT DEFAULT NULL,
            active TINYINT(1) DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_active (active)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    log.info("✓ mining_plans")

    # ── Migration: add one_time_only column if missing ──────────
    try:
        execute_query("ALTER TABLE mining_plans ADD COLUMN one_time_only TINYINT(1) DEFAULT 0")
        log.info("✓ migration: added one_time_only to mining_plans")
    except Exception:
        pass  # Column already exists — safe to ignore

    execute_query("""
        CREATE TABLE IF NOT EXISTS user_mining_machines (
            id INT AUTO_INCREMENT PRIMARY KEY,
            machine_id VARCHAR(100) NOT NULL UNIQUE,
            user_id VARCHAR(50) NOT NULL,
            plan_id INT NOT NULL,
            plan_name VARCHAR(100) DEFAULT NULL,
            hourly_rate DECIMAL(20,8) NOT NULL,
            total_mined DECIMAL(20,8) DEFAULT 0.00000000,
            last_claim_at DATETIME DEFAULT NULL,
            purchased_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            expires_at DATETIME NOT NULL,
            INDEX idx_user_id (user_id),
            INDEX idx_expires_at (expires_at),
            INDEX idx_machine_id (machine_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    log.info("✓ user_mining_machines")

    execute_query("""
        CREATE TABLE IF NOT EXISTS promo_codes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            code VARCHAR(50) NOT NULL UNIQUE,
            reward DECIMAL(10,8) NOT NULL DEFAULT 0.00000000,
            max_uses INT DEFAULT NULL,
            current_uses INT DEFAULT 0,
            active TINYINT(1) DEFAULT 1,
            expires_at DATETIME DEFAULT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_code (code),
            INDEX idx_active (active)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    log.info("✓ promo_codes")

    execute_query("""
        CREATE TABLE IF NOT EXISTS promo_redemptions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id VARCHAR(50) NOT NULL,
            code VARCHAR(50) NOT NULL,
            reward DECIMAL(10,8) NOT NULL,
            redeemed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY unique_redemption (user_id, code),
            INDEX idx_user_id (user_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    log.info("✓ promo_redemptions")

    execute_query("""
        CREATE TABLE IF NOT EXISTS balance_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id VARCHAR(50) NOT NULL,
            action VARCHAR(100) NOT NULL,
            amount DECIMAL(20,8) NOT NULL,
            balance_before DECIMAL(20,8) DEFAULT 0.00000000,
            balance_after DECIMAL(20,8) DEFAULT 0.00000000,
            description TEXT DEFAULT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_user_id (user_id),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    log.info("✓ balance_history")

    execute_query("""
        CREATE TABLE IF NOT EXISTS config (
            id INT AUTO_INCREMENT PRIMARY KEY,
            config_key VARCHAR(100) NOT NULL UNIQUE,
            config_value TEXT DEFAULT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    log.info("✓ config")

    execute_query("""
        CREATE TABLE IF NOT EXISTS stats (
            id INT AUTO_INCREMENT PRIMARY KEY,
            stat_key VARCHAR(100) NOT NULL UNIQUE,
            stat_value BIGINT DEFAULT 0,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    log.info("✓ stats")

    execute_query("""
        CREATE TABLE IF NOT EXISTS user_ips (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id VARCHAR(50) NOT NULL,
            ip_address VARCHAR(50) NOT NULL,
            first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_seen DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            times_seen INT DEFAULT 1,
            UNIQUE KEY unique_user_ip (user_id, ip_address),
            INDEX idx_ip_address (ip_address)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    log.info("✓ user_ips")

    execute_query("""
        CREATE TABLE IF NOT EXISTS ip_bans (
            id INT AUTO_INCREMENT PRIMARY KEY,
            ip_address VARCHAR(50) NOT NULL UNIQUE,
            reason VARCHAR(255) DEFAULT NULL,
            banned_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    log.info("✓ ip_bans")

    execute_query("""
        CREATE TABLE IF NOT EXISTS admin_sessions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            admin_id VARCHAR(50) NOT NULL,
            session_token VARCHAR(255) NOT NULL,
            ip_address VARCHAR(50) DEFAULT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            expires_at DATETIME NOT NULL,
            INDEX idx_session_token (session_token)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    log.info("✓ admin_sessions")

    # ── Default config values ──────────────────────────────────
    config_defaults = [
        ('daily_base_reward',        '0.01'),
        ('daily_streak_bonus',       '0.002'),
        ('daily_max_streak_bonus',   '0.05'),
        ('referral_bonus',           '0.05'),
        ('referral_commission',      '0.10'),
        ('referral_commission_pct',  '5'),
        ('min_withdrawal',           '1.0'),
        ('withdrawal_fee',           '0.5'),
        ('withdrawal_mode',          'manual'),
        ('admin_password',           'admin123'),
        ('bot_token',                os.environ.get('BOT_TOKEN', '')),
        ('bot_username',             os.environ.get('BOT_USERNAME', 'DogePixelBot')),
        ('official_channel',         '@DogePixel'),
        ('support_link',             'https://t.me/DogePixelSupport'),
        # TON
        ('ton_wallet_address',       ''),
        ('ton_to_doge_rate',         '100'),
        ('ton_min_deposit',          '0.1'),
        ('ton_deposits_enabled',     '1'),
        ('ton_auto_confirm',         '0'),
        ('ton_withdrawal_enabled',   '1'),
        ('ton_withdrawal_min_doge',  '0.01'),
        ('ton_withdrawal_fee_percent','2'),
        ('doge_to_ton_rate',         '100'),
        ('ton_bot_mnemonic',         os.environ.get('TON_BOT_MNEMONIC', '')),
        ('toncenter_api_key',        os.environ.get('TONCENTER_API_KEY', '')),
    ]
    for key, val in config_defaults:
        execute_query(
            "INSERT IGNORE INTO config (config_key, config_value) VALUES (%s, %s)",
            (key, val)
        )
    log.info("✓ config defaults seeded")

    # ── Default stats ──────────────────────────────────────────
    for stat in ('total_users','total_checkins','total_tasks_completed',
                 'total_withdrawals','total_doge_distributed'):
        execute_query(
            "INSERT IGNORE INTO stats (stat_key, stat_value) VALUES (%s, 0)",
            (stat,)
        )
    log.info("✓ stats seeded")

    # ── Default mining plans (only if empty) ─────────────────
    count = execute_query("SELECT COUNT(*) as c FROM mining_plans", fetch_one=True)
    if count and count.get('c', 0) == 0:
        # Plans: price, 30-day return %, hourly_rate = price * return_pct / 100 / 720h
        # Starter: FREE, 20% return → earns 0.20 TON over 30d → 0.000278 TON/hr
        # Basic:   1 TON,  30% → earns 0.30 TON → 0.000417/hr
        # Pro:     5 TON,  50% → earns 2.50 TON → 0.003472/hr
        # Elite:   20 TON, 70% → earns 14 TON  → 0.019444/hr
        # Master:  50 TON, 85% → earns 42.5 TON → 0.059028/hr
        # Legend: 100 TON,100% → earns 100 TON  → 0.138889/hr
        default_plans = [
            ('Starter',  'starter',  0.0,   0.00027800, 30, 'Plan gratuito · Gana 20% en 30 días · Solo una activación'),
            ('Basic',    'basic',    1.0,   0.00041700, 30, 'Gana 30% en 30 días · Renovable cada mes'),
            ('Pro',      'pro',      5.0,   0.00347200, 30, 'Gana 50% en 30 días · Renovable cada mes'),
            ('Elite',    'elite',    20.0,  0.01944400, 30, 'Gana 70% en 30 días · Renovable cada mes'),
            ('Master',   'master',   50.0,  0.05902800, 30, 'Gana 85% en 30 días · Renovable cada mes'),
            ('Legend',   'legendary',100.0, 0.13888900, 30, 'Gana 100% en 30 días · Máximo rendimiento'),
        ]
        for plan in default_plans:
            execute_query(
                "INSERT IGNORE INTO mining_plans (name,tier,price,hourly_rate,duration_days,description) VALUES (%s,%s,%s,%s,%s,%s)",
                plan
            )
        log.info("✓ default mining plans seeded")

    # ── Sample tasks (only if tasks table is empty) ────────────
    count = execute_query("SELECT COUNT(*) as c FROM tasks", fetch_one=True)
    if count and count.get('c', 0) == 0:
        sample_tasks = [
            ('join_channel', 'Únete al Canal', 'Únete al canal oficial de Telegram', 0.02, 'channel', 'telegram', 1, '@DogePixel', 1),
            ('invite_friend', 'Invita un Amigo', 'Comparte tu enlace de referido', 0.05, 'users', 'social', 0, None, 2),
            ('daily_quest', 'Check-In Diario', 'Reclama tu recompensa diaria', 0.01, 'calendar', 'daily', 0, None, 3),
        ]
        for t in sample_tasks:
            execute_query(
                "INSERT IGNORE INTO tasks (task_id,title,description,reward,icon,task_type,requires_channel,channel_username,sort_order) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                t
            )
        log.info("✓ sample tasks seeded")

    log.info("[init_all_tables] ✅ All tables ready.")


# ── Auto-run on startup ────────────────────────────────────────
# On Railway: RAILWAY_ENVIRONMENT is set automatically.
# You can also force it with INIT_DB=1.
_should_init = (
    os.environ.get('RAILWAY_ENVIRONMENT') or
    os.environ.get('INIT_DB', '0') == '1'
)
if _should_init:
    try:
        init_all_tables()
    except Exception as _e:
        logging.getLogger(__name__).error(f"[init_all_tables] FAILED: {_e}")


def create_ton_deposit(user_id, ton_amount, doge_credited, ton_wallet_from, ton_tx_hash=None, boc=None):
    """Create a new TON deposit record"""
    import uuid
    deposit_id = 'TOND-' + str(uuid.uuid4())[:8].upper()
    
    execute_query("""
        INSERT INTO ton_deposits (deposit_id, user_id, ton_amount, doge_credited, ton_wallet_from, ton_tx_hash, boc, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending')
    """, (deposit_id, str(user_id), float(ton_amount), float(doge_credited), ton_wallet_from, ton_tx_hash, boc))
    
    return deposit_id


def confirm_ton_deposit(deposit_id, ton_tx_hash=None):
    """Confirm and credit a TON deposit"""
    deposit = execute_query(
        "SELECT * FROM ton_deposits WHERE deposit_id = %s AND status = 'pending'",
        (deposit_id,), fetch_one=True
    )
    if not deposit:
        return False
    
    # Credit DOGE to user
    success = update_balance(
        deposit['user_id'],
        deposit['doge_credited'],
        'ton_deposit',
        f"TON deposit {deposit_id}"
    )
    
    if success:
        execute_query("""
            UPDATE ton_deposits 
            SET status = 'credited', ton_tx_hash = COALESCE(%s, ton_tx_hash), confirmed_at = NOW()
            WHERE deposit_id = %s
        """, (ton_tx_hash, deposit_id))

        # Pay 5% lifetime commission to referrer (if any)
        pay_referral_commission(deposit['user_id'], deposit['doge_credited'], 'deposit')

        return True
    return False


def get_user_ton_deposits(user_id, limit=20):
    """Get user TON deposit history"""
    return execute_query(
        "SELECT * FROM ton_deposits WHERE user_id = %s ORDER BY created_at DESC LIMIT %s",
        (str(user_id), limit), fetch_all=True
    ) or []


def get_pending_ton_deposits():
    """Get all pending TON deposits"""
    return execute_query(
        "SELECT * FROM ton_deposits WHERE status = 'pending' ORDER BY created_at ASC",
        fetch_all=True
    ) or []


def save_user_ton_wallet(user_id, ton_wallet):
    """Save user's TON wallet address"""
    execute_query(
        "UPDATE users SET ton_wallet = %s WHERE user_id = %s",
        (ton_wallet, str(user_id))
    )


def get_or_create_user_deposit_address(user_id):
    """
    Returns the bot's shared deposit address + a unique memo for this user.
    The memo is used to identify which user sent the TON.
    Format: TONU-<user_id_short>  (e.g. TONU-12345678)
    """
    user = execute_query(
        "SELECT ton_deposit_address FROM users WHERE user_id = %s",
        (str(user_id),), fetch_one=True
    )
    if user and user.get('ton_deposit_address'):
        return user['ton_deposit_address']

    # Generate stable memo from user_id
    memo = f"TONU{str(user_id)[-8:]}"
    execute_query(
        "UPDATE users SET ton_deposit_address = %s WHERE user_id = %s",
        (memo, str(user_id))
    )
    return memo


def create_ton_deposit_pending(user_id, memo):
    """
    Create a pending deposit record identified by memo (user's unique comment).
    ton_amount and doge_credited will be filled when the TX is detected.
    """
    import uuid
    deposit_id = 'TOND-' + str(uuid.uuid4())[:8].upper()
    execute_query("""
        INSERT INTO ton_deposits
            (deposit_id, user_id, ton_amount, doge_credited, ton_wallet_from, memo, status)
        VALUES (%s, %s, 0, 0, '', %s, 'pending')
        ON DUPLICATE KEY UPDATE deposit_id = deposit_id
    """, (deposit_id, str(user_id), memo))
    return deposit_id


# ============================================
# ANTI-FRAUD / MULTI-ACCOUNT DETECTION
# ============================================

def _ensure_fraud_columns():
    """Add fraud columns to users table and referrals table if not present (run once at startup)."""
    for col, definition in [
        ('withdrawal_blocked', 'TINYINT(1) DEFAULT 0'),
        ('fraud_reason',       'VARCHAR(255) DEFAULT NULL'),
        ('fraud_flagged_at',   'DATETIME DEFAULT NULL'),
    ]:
        try:
            execute_query(f"ALTER TABLE users ADD COLUMN {col} {definition}")
        except Exception:
            pass  # column already exists

    # Add is_fraud column to referrals table
    try:
        execute_query("ALTER TABLE referrals ADD COLUMN is_fraud TINYINT(1) DEFAULT 0")
    except Exception:
        pass  # already exists

_ensure_fraud_columns()


def _migrate_existing_fraud_referrals():
    """
    Mark existing referrals as is_fraud=1 if referrer and referred share an IP.
    Safe to run on every startup — only updates unflagged rows.
    """
    try:
        execute_query("""
            UPDATE referrals r
            SET r.is_fraud = 1
            WHERE r.is_fraud = 0
              AND EXISTS (
                  SELECT 1
                  FROM user_ips ui1
                  JOIN user_ips ui2
                    ON ui1.ip_address = ui2.ip_address
                  WHERE ui1.user_id = r.referrer_id
                    AND ui2.user_id = r.referred_id
                    AND ui1.times_seen >= 2
                    AND ui2.times_seen >= 2
              )
        """)
        import logging
        logging.getLogger(__name__).info("[ANTI-FRAUD] Fraud referrals migration complete.")
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"[ANTI-FRAUD] Migration error: {e}")

_migrate_existing_fraud_referrals()


def get_shared_ip_accounts(user_id, min_times_seen=2):
    """
    Return list of OTHER user_ids that have shared at least one IP
    with this user (excluding single-hit proxies by requiring min_times_seen).
    """
    rows = execute_query("""
        SELECT DISTINCT ui2.user_id
        FROM user_ips ui1
        JOIN user_ips ui2
          ON ui1.ip_address = ui2.ip_address
         AND ui2.user_id != ui1.user_id
        WHERE ui1.user_id = %s
          AND ui1.times_seen >= %s
          AND ui2.times_seen >= %s
    """, (str(user_id), min_times_seen, min_times_seen), fetch_all=True)
    return [r['user_id'] for r in rows] if rows else []


def count_accounts_on_same_ip(user_id, min_times_seen=2):
    """
    Count how many DISTINCT accounts (including this user) share any IP.
    Returns (count, list_of_all_user_ids_on_shared_ip).
    """
    shared = get_shared_ip_accounts(user_id, min_times_seen=min_times_seen)
    all_accounts = [str(user_id)] + [str(u) for u in shared]
    return len(all_accounts), all_accounts


def flag_user_fraud(user_id, reason):
    """Mark user withdrawal as blocked and record reason."""
    execute_query("""
        UPDATE users
        SET withdrawal_blocked = 1,
            fraud_reason       = %s,
            fraud_flagged_at   = NOW()
        WHERE user_id = %s
    """, (reason[:255], str(user_id)))


def unflag_user_fraud(user_id):
    """Clear fraud flag (admin action)."""
    execute_query("""
        UPDATE users
        SET withdrawal_blocked = 0,
            fraud_reason       = NULL,
            fraud_flagged_at   = NULL
        WHERE user_id = %s
    """, (str(user_id),))


def is_withdrawal_blocked(user_id):
    """Return (blocked: bool, reason: str|None)."""
    row = execute_query(
        "SELECT withdrawal_blocked, fraud_reason FROM users WHERE user_id = %s",
        (str(user_id),), fetch_one=True
    )
    if not row:
        return False, None
    return bool(row.get('withdrawal_blocked')), row.get('fraud_reason')


# Maximum accounts allowed per shared IP before blocking withdrawals
MAX_ACCOUNTS_PER_IP = 3


def check_and_flag_multi_account(user_id, min_times_seen=2):
    """
    Check if IP group exceeds MAX_ACCOUNTS_PER_IP.
    - Up to MAX_ACCOUNTS_PER_IP accounts on same IP → allowed (no flag).
    - More than MAX_ACCOUNTS_PER_IP → block withdrawals for ALL involved.
    - Normal app usage (browsing, mining, tasks) is NEVER blocked.
    Returns list of flagged user_ids, or [] if within the allowed limit.
    """
    count, all_accounts = count_accounts_on_same_ip(user_id, min_times_seen=min_times_seen)

    if count <= MAX_ACCOUNTS_PER_IP:
        # Within allowed limit — lift any previous flag if situation improved
        # (e.g. admin removed a sibling account)
        blocked, _ = is_withdrawal_blocked(user_id)
        if blocked:
            # Re-check: if this specific user's group is now within limit, unblock
            unflag_user_fraud(user_id)
        return []

    # Exceeds limit — flag everyone in the group
    ids_str = ', '.join(all_accounts[:6])
    reason = f"Multi-account ({count} accounts on same IP): {ids_str}"

    flagged = []
    for uid in all_accounts:
        already_blocked, _ = is_withdrawal_blocked(uid)
        if not already_blocked:
            flag_user_fraud(uid, reason)
            flagged.append(uid)

    import logging
    if flagged:
        logging.getLogger(__name__).warning(
            f"[ANTI-FRAUD] Blocked {len(flagged)} accounts (>{MAX_ACCOUNTS_PER_IP} on same IP): {ids_str}"
        )
    return flagged


def are_accounts_related(user_id_a, user_id_b, min_times_seen=2):
    """
    Return True if user_id_a and user_id_b share at least one IP.
    Used to skip referral bonuses between linked accounts.
    """
    row = execute_query("""
        SELECT 1
        FROM user_ips ui1
        JOIN user_ips ui2
          ON ui1.ip_address = ui2.ip_address
        WHERE ui1.user_id = %s
          AND ui2.user_id = %s
          AND ui1.times_seen >= %s
          AND ui2.times_seen >= %s
        LIMIT 1
    """, (str(user_id_a), str(user_id_b), min_times_seen, min_times_seen), fetch_one=True)
    return row is not None

