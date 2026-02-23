"""
app.py - Doge Pixel Flask Application
Completely Rebuilt - Pixel Retro Design - DOGE Only
"""

import os
import sys
import json
import secrets
import logging
import requests
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from translations import get_t, get_supported_langs

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Import Database Operations
from database import (
    get_user, create_user, update_user, get_users_count,
    update_balance, get_balance_history,
    get_checkin_status, claim_daily_checkin, get_checkin_history,
    add_referral, validate_referral, get_referrals, get_referral_stats,
    get_all_tasks, get_task, create_task, update_task, delete_task,
    is_task_completed, complete_task, get_user_tasks_status,
    create_withdrawal, get_user_withdrawals, get_pending_withdrawals, update_withdrawal,
    get_all_promo_codes, get_promo_code, create_promo_code, redeem_promo_code,
    get_config, set_config, get_all_config,
    get_stat, get_all_stats, increment_stat,
    record_user_ip, is_ip_banned, ban_user, unban_user,
    get_top_earners, get_top_referrers, get_top_streakers,
    get_all_users, ban_ip, unban_ip,
    # Mining functions
    get_all_mining_plans, get_mining_plan, purchase_mining_machine,
    get_user_machines, get_user_mining_stats, get_pending_mining_rewards,
    claim_mining_rewards, process_mining_rewards, create_mining_plan,
    delete_mining_plan, update_mining_plan, get_mining_stats,
    # TON Deposit functions
    create_ton_deposit, confirm_ton_deposit, get_user_ton_deposits,
    create_ton_withdrawal,
    get_pending_ton_deposits, save_user_ton_wallet,
    get_or_create_user_deposit_address, create_ton_deposit_pending
)

# ── NOTIFICATION HELPERS ──────────────────────────────────────────
try:
    from notifications import (
        detect_lang,
        notify_deposit, notify_withdrawal_approved, notify_withdrawal_rejected,
        notify_plan_activated, notify_referral_validated, notify_welcome
    )
    _NOTIF_OK = True
except ImportError:
    _NOTIF_OK = False

# Flask App Setup
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.permanent_session_lifetime = timedelta(days=7)

# ── LANGUAGE / i18n ─────────────────────────────────────────────
@app.context_processor
def inject_lang():
    """Inject `t` (translations) and `current_lang` into every template."""
    lang = session.get('lang', 'en')
    return dict(t=get_t(lang), current_lang=lang)


def _t(key, **kwargs):
    """Translate an API message key using the current session language."""
    lang = session.get('lang', 'en')
    t = get_t(lang)
    msg = getattr(t, key, key)
    for k, v in kwargs.items():
        msg = msg.replace('{' + k + '}', str(v))
    return msg


def translate_result(result):
    """Translate err_code in a database result dict into a localized message."""
    if not isinstance(result, dict):
        return result
    if 'err_code' in result:
        code      = result.pop('err_code')
        plan_name = result.pop('plan_name', '')
        date      = result.pop('date', '')
        amount    = result.pop('amount', '') if isinstance(result.get('amount'), str) else ''
        price     = result.pop('price', '')
        claimed   = result.pop('claimed', '')
        result['message'] = _t(code, name=plan_name, date=date, amount=amount, price=price, claimed=claimed)
    if 'error' in result and isinstance(result['error'], str) and result['error'].startswith('api_'):
        code = result.pop('error')
        amount = result.pop('amount', '')
        result['error'] = _t(code, amount=amount)
    return result

@app.route('/lang/<code>')
def set_lang(code):
    """Switch UI language and redirect back."""
    if code in get_supported_langs():
        session['lang'] = code
    return redirect(request.referrer or url_for('index'))


# Configuration
ADMIN_IDS = os.environ.get('ADMIN_IDS', '5515244003').split(',')
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
BOT_USERNAME = os.environ.get('BOT_USERNAME', 'Dogepixelbot')
APP_NAME     = os.environ.get('APP_NAME', 'app')   # Mini App short name
APP_URL      = os.environ.get('APP_URL', f'https://t.me/{os.environ.get("BOT_USERNAME","Dogepixelbot")}/app')
OFFICIAL_CHANNEL = os.environ.get('OFFICIAL_CHANNEL', '@Doge Pixel')

# ============================================
# ICON SYSTEM
# ============================================

# Load icon configuration
ICONS_CONFIG = {}
ICONS_PATH = os.path.join(app.static_folder, 'icons')

def load_icons_config():
    """Load icons configuration from JSON file"""
    global ICONS_CONFIG
    config_path = os.path.join(ICONS_PATH, 'icons.json')
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                ICONS_CONFIG = json.load(f)
            logger.info("Icons configuration loaded")
        else:
            logger.warning("Icons config not found, using defaults")
    except Exception as e:
        logger.error(f"Error loading icons config: {e}")
        ICONS_CONFIG = {}

# Load on startup
load_icons_config()

def get_icon(category, name, size='md', css_class=''):
    """
    Get icon HTML - returns img tag if PNG exists, otherwise emoji fallback
    
    Usage in templates: {{ icon('menu', 'home') }}
    
    Sizes: xs (12px), sm (16px), md (20px), lg (24px), xl (32px), xxl (48px)
    """
    size_map = {
        'xs': '12px',
        'sm': '16px',
        'md': '20px',
        'lg': '24px',
        'xl': '32px',
        'xxl': '48px'
    }
    
    pixel_size = size_map.get(size, '20px')
    
    # Get icon config
    icon_data = ICONS_CONFIG.get(category, {}).get(name, {})
    image_file = icon_data.get('image')
    fallback = icon_data.get('fallback', '?')
    
    # Check if image file exists and is set
    if image_file:
        image_path = os.path.join(ICONS_PATH, category, image_file)
        if os.path.exists(image_path):
            url = url_for('static', filename=f'icons/{category}/{image_file}')
            return f'<img src="{url}" alt="{name}" class="app-icon icon-{size} {css_class}" style="width:{pixel_size};height:{pixel_size};">'
    
    # Return emoji fallback wrapped in span
    return f'<span class="app-icon icon-emoji icon-{size} {css_class}" style="font-size:{pixel_size};line-height:{pixel_size};">{fallback}</span>'

def icon_url(category, name):
    """Get icon URL or None if using emoji fallback"""
    icon_data = ICONS_CONFIG.get(category, {}).get(name, {})
    image_file = icon_data.get('image')
    
    if image_file:
        image_path = os.path.join(ICONS_PATH, category, image_file)
        if os.path.exists(image_path):
            return url_for('static', filename=f'icons/{category}/{image_file}')
    return None

def icon_fallback(category, name):
    """Get emoji fallback for an icon"""
    icon_data = ICONS_CONFIG.get(category, {}).get(name, {})
    return icon_data.get('fallback', '?')

# Register icon functions with Jinja2
app.jinja_env.globals['icon'] = get_icon
app.jinja_env.globals['icon_url'] = icon_url
app.jinja_env.globals['icon_fallback'] = icon_fallback
app.jinja_env.globals['icons_config'] = lambda: ICONS_CONFIG
app.jinja_env.globals['format_doge'] = lambda amount: format_doge(amount)
app.jinja_env.globals['format_ton'] = lambda amount: format_ton(amount)

# ============================================
# TELEGRAM VERIFICATION
# ============================================

_channel_cache = {}
_CACHE_DURATION = 60  # seconds

def verify_channel_membership(user_id, channel_username):
    """Verify if user is member of Telegram channel"""
    if not BOT_TOKEN or not channel_username:
        return False, "Configuration error"
    
    channel = channel_username.strip()
    if not channel.startswith('@'):
        channel = f"@{channel}"
    
    # Check cache
    cache_key = f"{user_id}:{channel}"
    if cache_key in _channel_cache:
        cached = _channel_cache[cache_key]
        if (datetime.now() - cached['time']).seconds < _CACHE_DURATION:
            return cached['result']
    
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember"
        response = requests.get(url, params={
            'chat_id': channel,
            'user_id': user_id
        }, timeout=10)
        
        data = response.json()
        if data.get('ok'):
            status = data.get('result', {}).get('status', '')
            is_member = status in ['member', 'administrator', 'creator']
            result = (is_member, "Member" if is_member else "Not a member")
        else:
            result = (False, data.get('description', 'Verification failed'))
        
        # Cache result
        _channel_cache[cache_key] = {'result': result, 'time': datetime.now()}
        return result
        
    except Exception as e:
        logger.error(f"Channel verification error: {e}")
        return False, str(e)

# ============================================
# HELPER FUNCTIONS
# ============================================

def get_client_ip():
    """Get client IP address"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr or '127.0.0.1'

def get_user_id():
    """Extract user ID from Telegram WebApp data"""
    # Check session first
    if session.get('user_id'):
        return session.get('user_id')
    
    # Check initData (sent from Telegram WebApp JS)
    init_data = request.args.get('initData', '')
    if init_data:
        try:
            import urllib.parse
            params = dict(urllib.parse.parse_qsl(init_data))
            if 'user' in params:
                user_data = json.loads(params['user'])
                user_id = str(user_data.get('id'))
                session['user_id'] = user_id
                session['username'] = user_data.get('username', '')
                session['first_name'] = user_data.get('first_name', 'Player')
                # Save start_param (referral) from Mini App launch
                start_param = params.get('start_param', '')
                if start_param and start_param != user_id:
                    session['pending_ref'] = start_param
                return user_id
        except Exception as e:
            logger.error(f"initData parse error: {e}")
    
    # Check URL parameters
    user_id = request.args.get('user_id') or request.args.get('id')
    if user_id:
        session['user_id'] = str(user_id)
        return str(user_id)
    
    return None

def ensure_user(user_id):
    """Ensure user exists and return user data"""
    from database import execute_query
    user = get_user(user_id)
    username   = session.get('username')
    first_name = session.get('first_name', 'Player')

    # Get ref from any possible param
    ref = (request.args.get('ref') or request.args.get('start') or
           request.args.get('referral') or session.get('pending_ref'))

    # Clean ref: can't refer yourself
    if ref and str(ref) == str(user_id):
        ref = None

    if not user:
        # New user — create and record referral (NOT validated yet, requires plan purchase)
        user = create_user(user_id, username, first_name, ref)
        if ref:
            referrer = get_user(ref)
            if referrer:
                add_referral(ref, user_id, username, first_name)
                # ⚠ NO auto-validation — referral is validated only after plan purchase
        # Clear pending ref
        session.pop('pending_ref', None)
    else:
        # Existing user — save ref in session if provided and not already referred
        if ref and not user.get('referred_by'):
            session['pending_ref'] = ref
            # Update referred_by on the user
            execute_query(
                "UPDATE users SET referred_by = %s WHERE user_id = %s AND (referred_by IS NULL OR referred_by = '')",
                (str(ref), str(user_id))
            )
            referrer = get_user(ref)
            if referrer:
                # Check not already in referrals table
                existing = execute_query(
                    "SELECT id FROM referrals WHERE referrer_id = %s AND referred_id = %s",
                    (str(ref), str(user_id)), fetch_one=True
                )
                if not existing:
                    add_referral(ref, user_id,
                                 user.get('username'), user.get('first_name', 'Player'))
                    # ⚠ NO auto-validation — referral is validated only after plan purchase
            session.pop('pending_ref', None)
            # Refresh user
            user = get_user(user_id)
        # No fallback validation either — only purchase triggers it

    return user


def _validate_referral_on_purchase(user_id):
    """Validate a pending referral when the referred user purchases their first mining plan."""
    from database import execute_query
    user = get_user(user_id)
    if not user:
        return
    referrer_id = user.get('referred_by')
    if not referrer_id:
        return

    referred_name = user.get('first_name') or user.get('username') or 'Usuario'

    # Check there is an unvalidated referral record
    ref_row = execute_query(
        "SELECT id, validated FROM referrals WHERE referrer_id = %s AND referred_id = %s LIMIT 1",
        (str(referrer_id), str(user_id)), fetch_one=True
    )
    validated = False
    if not ref_row:
        referrer = get_user(referrer_id)
        if referrer:
            add_referral(referrer_id, user_id, user.get('username'), user.get('first_name', 'Player'))
            validate_referral(str(referrer_id), str(user_id))
            logger.info(f"Referral validated on plan purchase: referrer={referrer_id} referred={user_id}")
            validated = True
    elif not ref_row.get('validated'):
        validate_referral(str(referrer_id), str(user_id))
        logger.info(f"Referral validated on plan purchase: referrer={referrer_id} referred={user_id}")
        validated = True

    # ── Notificación al referidor ──
    if validated and _NOTIF_OK:
        try:
            referrer_obj = get_user(referrer_id)
            lang_code = referrer_obj.get('language_code') if referrer_obj else None
            notify_referral_validated(
                referrer_id=int(referrer_id),
                referred_name=referred_name,
                reward='1',
                language_code=lang_code,
            )
        except Exception as _ne:
            logger.warning(f"Referral notification error: {_ne}")

def format_doge(amount):
    """Format DOGE amount for display"""
    if amount is None:
        return "0.0000"
    return f"{float(amount):.4f}"

def format_ton(amount):
    """Format TON amount for display — no conversion, value IS already TON"""
    if amount is None:
        return "0.0000"
    return f"{float(amount):.4f}"

# ============================================
# DECORATORS
# ============================================

def require_user(f):
    """Decorator to require authenticated user"""
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = get_user_id()
        if not user_id:
            if request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            return render_template('telegram_required.html')
        
        user = ensure_user(user_id)
        if user.get('banned'):
            if request.is_json:
                return jsonify({'error': 'Account suspended'}), 403
            return render_template('banned.html', reason=user.get('ban_reason'))
        
        # Check IP ban
        client_ip = get_client_ip()
        if is_ip_banned(client_ip):
            if request.is_json:
                return jsonify({'error': 'Access denied'}), 403
            return render_template('banned.html', reason='IP address blocked')
        
        # Record activity
        record_user_ip(user_id, client_ip)
        
        return f(user, *args, **kwargs)
    return decorated

def require_admin(f):
    """Decorator to require admin access"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_authenticated'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

# ============================================
# USER ROUTES
# ============================================


@app.route('/auth', methods=['POST'])
def auth():
    """Receive initData from Telegram WebApp JS and save to session"""
    data = request.get_json(force=True) or {}
    init_data_raw = data.get('initData', '')
    
    if not init_data_raw:
        return jsonify({'success': False, 'message': 'No initData'})
    
    try:
        import urllib.parse
        params = dict(urllib.parse.parse_qsl(init_data_raw))
        if 'user' not in params:
            return jsonify({'success': False, 'message': 'No user in initData'})
        
        user_data = json.loads(params['user'])
        user_id   = str(user_data.get('id'))
        username  = user_data.get('username', '')
        first_name = user_data.get('first_name', 'Player')
        
        session['user_id']    = user_id
        session['username']   = username
        session['first_name'] = first_name
        session.permanent     = True
        
        # start_param = referral
        start_param = params.get('start_param') or data.get('start_param', '')
        if start_param and start_param != user_id:
            session['pending_ref'] = str(start_param)
        
        # Ensure user exists in DB
        ensure_user(user_id)
        
        return jsonify({'success': True, 'user_id': user_id})
    except Exception as e:
        logger.error(f"Auth error: {e}")
        return jsonify({'success': False, 'message': 'Auth failed'})


@app.route('/ref/<ref_id>')
def referral_landing(ref_id):
    """Landing page for referral links — saves ref in session"""
    if ref_id:
        session['pending_ref'] = str(ref_id)
    return redirect(url_for('index'))

@app.route('/')
def index():
    """Main dashboard - Home with Daily Check-In"""
    user_id = get_user_id()

    # Save ref param to session if present
    ref = request.args.get('ref') or request.args.get('start') or request.args.get('referral')
    if ref:
        session['pending_ref'] = str(ref)
    
    if not user_id:
        return render_template('telegram_required.html')
    
    user = ensure_user(user_id)
    if user.get('banned'):
        return render_template('banned.html', reason=user.get('ban_reason'))
    
    record_user_ip(user_id, get_client_ip())
    
    # Get check-in status
    checkin = get_checkin_status(user_id)
    
    return render_template('index.html',
        user=user,
        checkin=checkin,
        bot_username=BOT_USERNAME,
        format_doge=format_doge
    )

@app.route('/wallet')
@require_user
def wallet(user):
    """Wallet page - Balance and transactions"""
    history = get_balance_history(user['user_id'], limit=30)
    withdrawals = get_user_withdrawals(user['user_id'], limit=20)
    
    min_withdrawal = float(get_config('min_withdrawal', '1.0'))
    fee = float(get_config('withdrawal_fee', '0.5'))
    
    ton_deposits = get_user_ton_deposits(user['user_id'], limit=10)
    ton_rate = float(get_config('ton_to_doge_rate', '100'))
    ton_min = float(get_config('ton_min_deposit', '0.1'))
    ton_enabled = get_config('ton_deposits_enabled', '1') == '1'
    ton_wallet_addr = get_config('ton_wallet_address', '')
    # Unique memo per user for deposit identification
    user_deposit_memo = get_or_create_user_deposit_address(user['user_id']) if ton_enabled else ''

    # TON withdrawal config
    ton_withdrawal_enabled = get_config('ton_withdrawal_enabled', '1') == '1'
    ton_withdrawal_min = float(get_config('ton_withdrawal_min_doge', '10'))
    ton_withdrawal_fee_pct = float(get_config('ton_withdrawal_fee_percent', '2'))
    doge_to_ton_rate = float(get_config('doge_to_ton_rate', '100'))

    return render_template('wallet.html',
        user=user,
        history=history,
        withdrawals=withdrawals,
        min_withdrawal=min_withdrawal,
        withdrawal_fee=fee,
        format_doge=format_doge,
        ton_deposits=ton_deposits,
        ton_rate=ton_rate,
        ton_min=ton_min,
        ton_enabled=ton_enabled,
        ton_wallet_address=ton_wallet_addr,
        user_deposit_memo=user_deposit_memo,
        ton_withdrawal_enabled=ton_withdrawal_enabled,
        ton_withdrawal_min=ton_withdrawal_min,
        ton_withdrawal_fee_pct=ton_withdrawal_fee_pct,
        doge_to_ton_rate=doge_to_ton_rate,
    )


@app.route('/api/ton/withdraw/init', methods=['POST'])
@require_user
def api_ton_withdraw_init(user):
    """TON withdrawal — deducts DOGE and sends TON automatically via TON Connect / toncenter API"""
    data        = request.get_json() or {}
    doge_amount = float(data.get('doge_amount', 0))
    ton_wallet  = data.get('ton_wallet', '').strip()

    if not ton_wallet:
        return jsonify({'success': False, 'message': _t('api_no_wallet')})

    if get_config('ton_withdrawal_enabled', '1') != '1':
        return jsonify({'success': False, 'message': _t('api_wd_disabled')})

    # Create the withdrawal record (deducts DOGE balance)
    result = create_ton_withdrawal(user['user_id'], doge_amount, ton_wallet)
    if 'error' in result:
        err = result['error']
        amount = result.get('amount', '')
        return jsonify({'success': False, 'message': _t(err, amount=amount) if err.startswith('api_') else err})

    withdrawal_id = result['withdrawal_id']
    ton_amount    = result['ton_amount']

    # --- Attempt automatic TON send ---
    auto_sent, tx_hash, send_err = _auto_send_ton(ton_wallet, ton_amount, withdrawal_id)

    if auto_sent:
        # Mark withdrawal as completed immediately
        from database import execute_query
        execute_query(
            "UPDATE withdrawals SET status='completed', ton_tx_hash=%s, processed_at=NOW() WHERE withdrawal_id=%s",
            (tx_hash, withdrawal_id)
        )
        logger.info(f"TON auto-withdrawal {withdrawal_id}: sent {ton_amount} TON to {ton_wallet} tx={tx_hash}")
        return jsonify({
            'success':       True,
            'auto_sent':     True,
            'withdrawal_id': withdrawal_id,
            'doge_amount':   result['doge_amount'],
            'ton_amount':    ton_amount,
            'ton_wallet':    ton_wallet,
            'tx_hash':       tx_hash,
            'message':       f"¡Enviado! {ton_amount:.4f} TON enviados automáticamente a tu wallet ✅"
        })
    else:
        # Fallback: withdrawal stays pending, admin processes manually
        logger.warning(f"TON auto-send failed for {withdrawal_id}: {send_err} — queued for manual processing")
        return jsonify({
            'success':       True,
            'auto_sent':     False,
            'withdrawal_id': withdrawal_id,
            'doge_amount':   result['doge_amount'],
            'ton_amount':    ton_amount,
            'ton_wallet':    ton_wallet,
            'message':       f"Retiro en proceso: {ton_amount:.4f} TON serán enviados a tu wallet en breve."
        })


def _auto_send_ton(destination, ton_amount, memo=''):
    """
    Enviar TON automáticamente desde la wallet del bot.
    Returns: (success: bool, tx_hash: str|None, error_msg: str|None)
    """
    try:
        mnemonic_str = get_config('ton_bot_mnemonic', '') or os.getenv('TON_BOT_MNEMONIC', '')
        if not mnemonic_str or len(mnemonic_str.strip().split()) < 12:
            return False, None, 'TON_BOT_MNEMONIC no configurado (panel admin → Configuración → Retiros Automáticos TON)'

        api_key = get_config('toncenter_api_key', '') or os.getenv('TONCENTER_API_KEY', '')

        # Dirección real de la wallet del bot (Tonkeeper)
        bot_wallet = get_config('ton_bot_wallet_address', 'UQCqD6yy4uQvbmsZ792ScmyfynK6GnlLkkaE6T-xBSWAKtJN') or os.getenv('TON_BOT_WALLET_ADDRESS', 'UQCqD6yy4uQvbmsZ792ScmyfynK6GnlLkkaE6T-xBSWAKtJN')

        from ton_wallet import send_ton
        return send_ton(
            mnemonic           = mnemonic_str,
            to_addr            = destination,
            ton_amount         = float(ton_amount),
            memo               = str(memo)[:50],
            api_key            = api_key,
            bot_wallet_address = bot_wallet,
        )

    except Exception as exc:
        logger.exception(f'_auto_send_ton error: {exc}')
        return False, None, str(exc)


@app.route('/api/ton/deposit/address')
@require_user
def api_ton_deposit_address(user):
    """
    Returns the bot's deposit address + this user's unique memo.
    Frontend uses this to show QR and address.
    Also creates a pending deposit record for polling.
    """
    if get_config('ton_deposits_enabled', '1') != '1':
        return jsonify({'success': False, 'message': _t('api_dep_disabled')})
    
    bot_addr = get_config('ton_wallet_address', '') or os.getenv('TON_BOT_WALLET_ADDRESS', '')
    if not bot_addr:
        return jsonify({'success': False, 'message': _t('api_bot_addr_missing')})

    ton_wallet_addr = get_config('ton_wallet_address', '')
    if not ton_wallet_addr or 'AQUI' in ton_wallet_addr:
        return jsonify({'success': False, 'message': _t('api_bot_addr_missing')})

    memo = get_or_create_user_deposit_address(user['user_id'])
    ton_min = float(get_config('ton_min_deposit', '0.1'))
    ton_rate = float(get_config('ton_to_doge_rate', '100'))

    # Create or reuse a pending deposit for this user
    from database import execute_query
    existing = execute_query(
        "SELECT deposit_id FROM ton_deposits WHERE user_id=%s AND status='pending' ORDER BY created_at DESC LIMIT 1",
        (str(user['user_id']),), fetch_one=True
    )
    if existing:
        deposit_id = existing['deposit_id']
    else:
        deposit_id = create_ton_deposit_pending(user['user_id'], memo)

    return jsonify({
        'success': True,
        'deposit_address': ton_wallet_addr,
        'memo': memo,
        'deposit_id': deposit_id,
        'ton_min': ton_min,
        'ton_rate': ton_rate,
    })


@app.route('/api/ton/deposit/init', methods=['POST'])
@require_user
def api_ton_deposit_init(user):
    """Legacy endpoint — kept for compatibility"""
    return api_ton_deposit_address(user)


@app.route('/api/ton/deposit/verify', methods=['POST'])
@require_user
def api_ton_deposit_verify(user):
    """Legacy endpoint kept for compatibility — no longer used by frontend"""
    return jsonify({'success': False, 'pending': True,
                    'message': 'Usa el nuevo sistema de QR. Recarga la página.'})


@app.route('/api/ton/deposit/status/<deposit_id>')
@require_user
def api_ton_deposit_status(user, deposit_id):
    """
    Polling: frontend calls every 8s.
    Scans Toncenter for incoming TX matching the user's memo, then credits DOGE.
    """
    from database import execute_query
    deposit = execute_query(
        "SELECT status, doge_credited, ton_amount FROM ton_deposits WHERE deposit_id=%s AND user_id=%s",
        (deposit_id, str(user['user_id'])), fetch_one=True
    )
    if not deposit:
        return jsonify({'status': 'not_found'})

    if deposit['status'] == 'pending':
        _scan_and_credit_deposit(user['user_id'], deposit_id)
        deposit = execute_query(
            "SELECT status, doge_credited, ton_amount FROM ton_deposits WHERE deposit_id=%s",
            (deposit_id,), fetch_one=True
        )

    return jsonify({
        'status': deposit['status'] if deposit else 'not_found',
        'doge_credited': float(deposit['doge_credited']) if deposit else 0,
        'ton_amount': float(deposit['ton_amount']) if deposit else 0,
    })


def _scan_and_credit_deposit(user_id, deposit_id):
    """
    Scan the bot wallet's recent transactions for a TX whose comment matches
    this user's memo. If found, credit DOGE automatically.
    """
    from database import execute_query
    try:
        receiver = get_config('ton_wallet_address', '')
        api_key  = get_config('toncenter_api_key', '') or os.getenv('TONCENTER_API_KEY', '')
        if not receiver or 'AQUI' in receiver:
            return

        memo = get_or_create_user_deposit_address(user_id)
        ton_rate = float(get_config('ton_to_doge_rate', '100'))
        ton_min  = float(get_config('ton_min_deposit', '0.1'))

        headers = {}
        if api_key:
            headers['X-API-Key'] = api_key

        resp = requests.get(
            'https://toncenter.com/api/v2/getTransactions',
            params={'address': receiver, 'limit': 50},
            headers=headers, timeout=10
        )
        data = resp.json()
        if not data.get('ok'):
            return

        for tx in data.get('result', []):
            in_msg = tx.get('in_msg', {})
            comment = str(in_msg.get('message', '') or '').strip()
            value_nano = int(in_msg.get('value', '0') or 0)
            tx_hash = tx.get('transaction_id', {}).get('hash', '')

            if memo not in comment:
                continue

            ton_amount = value_nano / 1e9
            if ton_amount < ton_min * 0.95:  # 5% tolerance
                continue

            # Check not already processed
            already = execute_query(
                "SELECT id FROM ton_deposits WHERE ton_tx_hash=%s",
                (tx_hash,), fetch_one=True
            )
            if already:
                continue

            doge_credited = ton_amount * ton_rate
            sender = str(in_msg.get('source', ''))

            execute_query("""
                UPDATE ton_deposits
                SET ton_amount=%s, doge_credited=%s, ton_wallet_from=%s,
                    ton_tx_hash=%s, memo=%s
                WHERE deposit_id=%s AND status='pending'
            """, (ton_amount, doge_credited, sender, tx_hash, memo, deposit_id))

            confirm_ton_deposit(deposit_id, tx_hash)
            logger.info(f"TON deposit auto-credited: {ton_amount} TON → {doge_credited} DOGE for user {user_id}")

            # ── Notificación de depósito confirmado ──
            if _NOTIF_OK:
                try:
                    user_obj = get_user(user_id)
                    lang_code = user_obj.get('language_code') if user_obj else None
                    from datetime import datetime as _dt
                    notify_deposit(
                        user_id=int(user_id),
                        amount=ton_amount,
                        currency='TON',
                        credited=doge_credited,
                        deposit_id=str(deposit_id),
                        date=_dt.now().strftime('%Y-%m-%d %H:%M'),
                        language_code=lang_code,
                    )
                except Exception as _ne:
                    logger.warning(f"Deposit notification error: {_ne}")
            return

    except Exception as e:
        logger.warning(f"_scan_and_credit_deposit error: {e}")


@app.route('/admin/ton-deposits')
@require_admin
def admin_ton_deposits():
    """Admin: TON deposits management"""
    pending = get_pending_ton_deposits()
    from database import execute_query
    all_deposits = execute_query(
        "SELECT d.*, u.username, u.first_name FROM ton_deposits d LEFT JOIN users u ON d.user_id=u.user_id ORDER BY d.created_at DESC LIMIT 100",
        fetch_all=True
    ) or []
    return render_template('admin_ton_deposits.html', pending=pending, deposits=all_deposits)


@app.route('/admin/ton-deposits/<deposit_id>/approve', methods=['POST'])
@require_admin
def admin_ton_approve(deposit_id):
    """Admin: approve a TON deposit manually"""
    data = request.get_json() or {}
    result = confirm_ton_deposit(deposit_id, data.get('tx_hash') or None)
    if result:
        # ── Notificación de depósito aprobado por admin ──
        if _NOTIF_OK:
            try:
                from database import execute_query as _eq
                from datetime import datetime as _dt
                dep = _eq("SELECT user_id, ton_amount, doge_credited FROM ton_deposits WHERE deposit_id=%s",
                          (deposit_id,), fetch_one=True)
                if dep:
                    user_obj = get_user(dep['user_id'])
                    lang_code = user_obj.get('language_code') if user_obj else None
                    notify_deposit(
                        user_id=int(dep['user_id']),
                        amount=dep.get('ton_amount', '?'),
                        currency='TON',
                        credited=dep.get('doge_credited', '?'),
                        deposit_id=str(deposit_id),
                        date=_dt.now().strftime('%Y-%m-%d %H:%M'),
                        language_code=lang_code,
                    )
            except Exception as _ne:
                logger.warning(f"Admin deposit notification error: {_ne}")
        return jsonify({'success': True, 'message': 'DOGE acreditado correctamente'})
    return jsonify({'success': False, 'message': 'No encontrado o ya procesado'})


@app.route('/admin/ton-deposits/<deposit_id>/reject', methods=['POST'])
@require_admin
def admin_ton_reject(deposit_id):
    """Admin: reject a TON deposit"""
    data = request.get_json() or {}
    from database import execute_query
    execute_query("UPDATE ton_deposits SET status='failed', admin_note=%s WHERE deposit_id=%s",
                  (data.get('note','Rechazado'), deposit_id))
    return jsonify({'success': True, 'message': 'Deposito rechazado'})


@app.route('/tasks')
@require_user
def tasks(user):
    """Tasks page"""
    tasks_list = get_user_tasks_status(user['user_id'])
    
    # Calculate stats
    completed_tasks = sum(1 for t in tasks_list if t.get('completed')) if tasks_list else 0
    available_tasks = len(tasks_list) - completed_tasks if tasks_list else 0
    total_earned = float(user.get('total_earned', 0))
    
    return render_template('tasks.html',
        user=user,
        tasks=tasks_list,
        completed_tasks=completed_tasks,
        available_tasks=available_tasks,
        total_earned=total_earned,
        format_doge=format_doge
    )

@app.route('/referrals')
@require_user
def referrals(user):
    """Referrals page"""
    refs = get_referrals(user['user_id'])
    stats = get_referral_stats(user['user_id'])
    
    # Get referral bonus from config
    referral_bonus = float(get_config('referral_bonus', '0.05'))
    
    # Calculate stats
    total_referrals = len(refs) if refs else 0
    validated_referrals = sum(1 for r in refs if r.get('validated')) if refs else 0
    pending_referrals = total_referrals - validated_referrals
    referral_earnings = float(user.get('referral_earnings', 0))
    
    # Generate referral links — Telegram bot link + direct web link
    referral_link     = f"{APP_URL}?startapp={user['user_id']}"
    referral_web_link = f"{request.host_url}ref/{user['user_id']}"

    return render_template('referrals.html',
        user=user,
        referrals=refs,
        referral_bonus=referral_bonus,
        total_referrals=total_referrals,
        validated_referrals=validated_referrals,
        pending_referrals=pending_referrals,
        referral_earnings=referral_earnings,
        referral_link=referral_link,
        referral_web_link=referral_web_link,
        format_doge=format_doge
    )

@app.route('/explore')
@require_user
def explore(user):
    """Explore page - Leaderboards and discovery"""
    top_earners = get_top_earners(10)
    top_referrers = get_top_referrers(10)
    top_streakers = get_top_streakers(10)
    
    stats = get_all_stats()
    
    # Calculate user rank
    user_rank = None
    for i, earner in enumerate(top_earners, 1):
        if str(earner.get('user_id')) == str(user['user_id']):
            user_rank = i
            break
    
    # If not in top 10, calculate approximate rank
    if user_rank is None:
        total_users = int(stats.get('total_users', 0))
        if total_users > 0:
            user_rank = f"{total_users}+"
    
    # Community stats
    total_users = int(stats.get('total_users', 0))
    total_distributed = float(stats.get('total_doge_distributed', 0)) / 100000000  # Convert from satoshis
    total_checkins = int(stats.get('total_checkins', 0))
    
    return render_template('explore.html',
        user=user,
        top_earners=top_earners,
        top_referrers=top_referrers,
        top_streakers=top_streakers,
        user_rank=user_rank,
        total_users=total_users,
        total_distributed=total_distributed,
        total_checkins=total_checkins,
        stats=stats,
        format_doge=format_doge
    )

@app.route('/promo')
@require_user
def promo(user):
    """Promo code redemption page"""
    return render_template('promo.html',
        user=user,
        format_doge=format_doge
    )

@app.route('/mining')
@require_user
def mining(user):
    """Mining page - Purchase and manage mining machines"""
    plans = get_all_mining_plans(active_only=True)
    user_machines = get_user_machines(user['user_id'])
    mining_stats = get_user_mining_stats(user['user_id'])
    pending_rewards = get_pending_mining_rewards(user['user_id'])
    
    return render_template('mining.html',
        user=user,
        plans=plans,
        user_machines=user_machines,
        mining_stats=mining_stats,
        pending_rewards=pending_rewards,
        format_doge=format_doge
    )

# ============================================
# API ROUTES
# ============================================

@app.route('/api/checkin', methods=['POST'])
@require_user
def api_checkin(user):
    """Claim daily check-in"""
    result = claim_daily_checkin(user['user_id'])
    
    if not result:
        return jsonify({
            'success': False,
            'message': 'Already claimed today!'
        })
    
    return jsonify({
        'success': True,
        'reward': result['reward'],
        'streak': result['streak'],
        'streak_bonus': result['streak_bonus'],
        'message': f'Day {result["streak"]} complete!'
    })

@app.route('/api/task/complete', methods=['POST'])
@require_user
def api_complete_task(user):
    """Complete a task"""
    data = request.get_json() or {}
    task_id = data.get('task_id')
    
    if not task_id:
        return jsonify({'success': False, 'message': 'Task ID required'})
    
    task = get_task(str(task_id))
    if not task:
        return jsonify({'success': False, 'message': 'Task not found'})
    # Use the string task_id from the DB record
    task_id = task['task_id']
    
    if is_task_completed(user['user_id'], task_id):
        return jsonify({'success': False, 'message': 'Task already completed'})
    
    # Check channel requirement
    if task.get('requires_channel') and task.get('channel_username'):
        is_member, msg = verify_channel_membership(user['user_id'], task['channel_username'])
        if not is_member:
            return jsonify({
                'success': False, 
                'message': 'Please join the channel first',
                'requires_join': True,
                'channel': task['channel_username']
            })
    
    result = complete_task(user['user_id'], task_id)
    if not result:
        return jsonify({'success': False, 'message': 'Could not complete task'})
    
    return jsonify({
        'success': True,
        'reward': result['reward'],
        'message': f'+{format_doge(result["reward"])} DOGE earned!'
    })

@app.route('/api/withdraw', methods=['POST'])
@require_user
def api_withdraw(user):
    """Request withdrawal"""
    data = request.get_json() or {}
    amount = float(data.get('amount', 0))
    wallet = data.get('wallet_address', '').strip()
    
    if not wallet:
        return jsonify({'success': False, 'message': 'Wallet address required'})
    
    if not wallet.startswith('D') or len(wallet) < 30:
        return jsonify({'success': False, 'message': 'Invalid DOGE wallet address'})
    
    result = create_withdrawal(user['user_id'], amount, wallet)
    
    if 'error' in result:
        return jsonify({'success': False, 'message': result['error']})
    
    return jsonify({
        'success': True,
        'withdrawal_id': result['withdrawal_id'],
        'net_amount': result['net_amount'],
        'message': 'Withdrawal request submitted!'
    })

@app.route('/api/promo/redeem', methods=['POST'])
@require_user
def api_redeem_promo(user):
    """Redeem promo code"""
    data = request.get_json() or {}
    code = data.get('code', '').strip()
    
    if not code:
        return jsonify({'success': False, 'message': 'Enter a promo code'})
    
    result = redeem_promo_code(user['user_id'], code)
    
    if 'error' in result:
        return jsonify({'success': False, 'message': result['error']})
    
    return jsonify({
        'success': True,
        'reward': result['reward'],
        'message': f'+{format_doge(result["reward"])} DOGE received!'
    })

@app.route('/api/user/data')
@require_user
def api_user_data(user):
    """Get current user data"""
    checkin = get_checkin_status(user['user_id'])
    
    return jsonify({
        'success': True,
        'user': {
            'user_id': user['user_id'],
            'username': user.get('username'),
            'first_name': user.get('first_name', 'Player'),
            'balance': float(user.get('doge_balance', 0)),
            'total_earned': float(user.get('total_earned', 0)),
            'streak': user.get('checkin_streak', 0),
            'referral_count': user.get('referral_count', 0)
        },
        'checkin': checkin
    })

@app.route('/api/channel/verify', methods=['POST'])
@require_user
def api_verify_channel(user):
    """Verify channel membership"""
    data = request.get_json() or {}
    channel = data.get('channel', OFFICIAL_CHANNEL)
    
    is_member, msg = verify_channel_membership(user['user_id'], channel)
    
    return jsonify({
        'success': is_member,
        'message': 'Verified!' if is_member else 'Please join the channel first',
        'is_member': is_member
    })

# ============================================
# MINING API ROUTES
# ============================================

@app.route('/api/mining/purchase', methods=['POST'])
@require_user
def api_mining_purchase(user):
    """Purchase a mining machine"""
    data = request.get_json() or {}
    plan_id = data.get('plan_id')
    
    if not plan_id:
        return jsonify({'success': False, 'message': 'Plan ID required'})
    
    result = purchase_mining_machine(user['user_id'], plan_id)
    translated = translate_result(result)

    # ── Validate referral on first plan purchase ──────────────────
    if translated.get('success'):
        _validate_referral_on_purchase(user['user_id'])

        # ── Notificación: plan activado ──
        if _NOTIF_OK:
            try:
                plan = get_mining_plan(plan_id)
                machines = get_user_machines(user['user_id'])
                expires = None
                if machines:
                    exp = machines[0].get('expires_at')
                    expires = exp.strftime('%Y-%m-%d') if exp and hasattr(exp, 'strftime') else str(exp) if exp else 'N/A'
                lang_code = user.get('language_code')
                notify_plan_activated(
                    user_id=int(user['user_id']),
                    plan_name=plan.get('name', plan_id) if plan else str(plan_id),
                    ton_per_hour=plan.get('ton_per_hour', '?') if plan else '?',
                    expires=expires or 'N/A',
                    language_code=lang_code,
                )
            except Exception as _ne:
                logger.warning(f"Plan notification error: {_ne}")

    return jsonify(translated)

@app.route('/api/mining/claim', methods=['POST'])
@require_user
def api_mining_claim(user):
    """Claim mining rewards"""
    result = claim_mining_rewards(user['user_id'])
    return jsonify(translate_result(result))

@app.route('/api/mining/stats')
@require_user
def api_mining_stats(user):
    """Get user's mining stats"""
    mining_stats = get_user_mining_stats(user['user_id'])
    pending_rewards = get_pending_mining_rewards(user['user_id'])
    machines = get_user_machines(user['user_id'])
    
    # Build extra info for index page display
    plan_name = None
    expires_at = None
    if machines:
        first = machines[0]
        plan_name = first.get('plan_name') or first.get('name')
        exp = first.get('expires_at')
        expires_at = exp.strftime('%Y-%m-%d') if exp and hasattr(exp, 'strftime') else str(exp) if exp else None

    return jsonify({
        'success': True,
        'stats': mining_stats,
        'pending_rewards': pending_rewards,
        'total_machines': mining_stats.get('total_machines', 0),
        'total_hourly_rate': mining_stats.get('total_hourly_rate', 0),
        'plan_name': plan_name,
        'expires_at': expires_at
    })

# ============================================
# ICONS API ROUTES
# ============================================

@app.route('/api/icons/reload', methods=['POST'])
@require_admin
def api_reload_icons():
    """Reload icons configuration"""
    load_icons_config()
    return jsonify({'success': True, 'message': 'Icons reloaded'})

@app.route('/api/icons/config')
@require_admin
def api_icons_config():
    """Get current icons configuration"""
    return jsonify({'success': True, 'config': ICONS_CONFIG})

@app.route('/api/icons/update', methods=['POST'])
@require_admin
def api_update_icon():
    """Update a single icon configuration"""
    data = request.get_json() or {}
    category = data.get('category')
    name = data.get('name')
    image = data.get('image')  # filename or null
    fallback = data.get('fallback')
    
    if not category or not name:
        return jsonify({'success': False, 'message': 'Category and name required'})
    
    # Update config
    if category not in ICONS_CONFIG:
        ICONS_CONFIG[category] = {}
    
    if name not in ICONS_CONFIG[category]:
        ICONS_CONFIG[category][name] = {}
    
    if image is not None:
        ICONS_CONFIG[category][name]['image'] = image if image else None
    
    if fallback is not None:
        ICONS_CONFIG[category][name]['fallback'] = fallback
    
    # Save to file
    config_path = os.path.join(ICONS_PATH, 'icons.json')
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(ICONS_CONFIG, f, indent=2, ensure_ascii=False)
        return jsonify({'success': True, 'message': 'Icon updated'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# ============================================
# ADMIN ROUTES
# ============================================

@app.route('/admin')
def admin_login():
    """Admin login page"""
    if session.get('admin_authenticated'):
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_login.html')

@app.route('/admin/auth', methods=['POST'])
@app.route('/admin/login', methods=['POST'])
def admin_auth():
    """Admin authentication"""
    username = request.form.get('username', '')
    password = request.form.get('password', '')
    admin_pass = get_config('admin_password', 'admin123')
    admin_user = get_config('admin_username', 'admin')
    
    # Support both username+password login and password-only login
    if password == admin_pass and (not username or username == admin_user):
        session['admin_authenticated'] = True
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin_login.html', error='Invalid username or password')

@app.route('/admin/dashboard')
@require_admin
def admin_dashboard():
    """Admin dashboard"""
    from datetime import datetime
    stats = get_all_stats()
    config = get_all_config()
    
    # Counts
    total_users = get_users_count()
    pending_withdrawal_list = get_pending_withdrawals()
    pending_withdrawals = len(pending_withdrawal_list)
    
    # Stats from the stats table (with defaults)
    total_distributed = float(stats.get('total_distributed', 0))
    total_checkins    = int(stats.get('total_checkins', 0))
    checkins_today    = int(stats.get('checkins_today', 0))
    total_tasks_completed = int(stats.get('total_tasks_completed', 0))
    total_referrals   = int(stats.get('total_referrals', 0))
    
    # Active today: users active in last 24h
    from database import execute_query
    res = execute_query(
        "SELECT COUNT(*) as c FROM users WHERE last_active >= NOW() - INTERVAL 1 DAY",
        fetch_one=True
    )
    active_today = res["c"] if res else 0
    
    # Recent users (last 10)
    recent_users = get_all_users(limit=10, offset=0)
    
    # Top earners
    top_earners = get_top_earners(limit=10)
    
    # Active tasks
    active_tasks = get_all_tasks(active_only=True)
    
    return render_template("admin_dashboard.html",
        stats=stats,
        config=config,
        users_count=total_users,
        total_users=total_users,
        active_today=active_today,
        total_distributed=total_distributed,
        pending_withdrawals=pending_withdrawals,
        pending_withdrawal_list=pending_withdrawal_list,
        total_checkins=total_checkins,
        checkins_today=checkins_today,
        total_tasks_completed=total_tasks_completed,
        total_referrals=total_referrals,
        recent_users=recent_users,
        top_earners=top_earners,
        active_tasks=active_tasks,
        now=datetime.now().strftime("%Y-%m-%d %H:%M"),
        format_doge=format_doge,
    )

@app.route('/admin/users')
@require_admin
def admin_users():
    """Admin users management"""
    from database import execute_query
    page        = int(request.args.get('page', 1))
    filter_type = request.args.get('filter', 'all')
    search      = request.args.get('search', '').strip()
    per_page    = 50
    offset      = (page - 1) * per_page

    if search:
        users = execute_query(
            """SELECT * FROM users
               WHERE username LIKE %s OR first_name LIKE %s OR telegram_id LIKE %s
               ORDER BY created_at DESC LIMIT %s OFFSET %s""",
            (f'%{search}%', f'%{search}%', f'%{search}%', per_page, offset),
            fetch_all=True
        ) or []
        res = execute_query(
            "SELECT COUNT(*) as c FROM users WHERE username LIKE %s OR first_name LIKE %s OR telegram_id LIKE %s",
            (f'%{search}%', f'%{search}%', f'%{search}%'), fetch_one=True
        )
        total_users = res['c'] if res else 0
    elif filter_type == 'banned':
        users = execute_query(
            "SELECT * FROM users WHERE banned=1 ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (per_page, offset), fetch_all=True) or []
        res = execute_query("SELECT COUNT(*) as c FROM users WHERE banned=1", fetch_one=True)
        total_users = res['c'] if res else 0
    elif filter_type == 'active':
        users = execute_query(
            "SELECT * FROM users WHERE last_active >= NOW() - INTERVAL 1 DAY ORDER BY last_active DESC LIMIT %s OFFSET %s",
            (per_page, offset), fetch_all=True) or []
        res = execute_query("SELECT COUNT(*) as c FROM users WHERE last_active >= NOW() - INTERVAL 1 DAY", fetch_one=True)
        total_users = res['c'] if res else 0
    elif filter_type == 'top':
        users = execute_query(
            "SELECT * FROM users ORDER BY total_earned DESC LIMIT %s OFFSET %s",
            (per_page, offset), fetch_all=True) or []
        total_users = get_users_count()
    else:
        users = get_all_users(limit=per_page, offset=offset)
        total_users = get_users_count()

    total_pages = max(1, (total_users + per_page - 1) // per_page)

    # Normalise field names so template finds them
    for u in users:
        u.setdefault('longest_streak',     u.get('longest_streak', u.get('checkin_streak', 0)))
        u.setdefault('validated_referrals', u.get('validated_referrals', u.get('referral_count', 0)))
        u.setdefault('referral_earnings',   u.get('referral_earnings', 0))
        u['is_banned'] = bool(u.get('banned', 0))

    return render_template('admin_users.html',
        users=users,
        page=page,
        total_pages=total_pages,
        total_users=total_users,
        filter=filter_type,
        search=search,
        format_doge=format_doge,
    )

@app.route('/admin/tasks')
@require_admin
def admin_tasks():
    """Admin tasks management"""
    from database import execute_query
    tasks_list = get_all_tasks(active_only=False)

    # Fields already normalized by _normalize_task() in database.py
    # Just ensure nothing is missing
    for t in tasks_list:
        t.setdefault('completions', t.get('current_completions', 0))
        t.setdefault('category',    t.get('task_type', 'telegram'))
        t.setdefault('is_active',   bool(t.get('active', 1)))

    total_tasks       = len(tasks_list)
    active_tasks_count = sum(1 for t in tasks_list if t.get('is_active'))
    total_completions = sum(t.get('completions', 0) for t in tasks_list)

    res = execute_query(
        "SELECT SUM(reward * current_completions) as total FROM tasks",
        fetch_one=True
    )
    total_rewards_paid = float(res['total']) if res and res.get('total') else 0.0

    return render_template('admin_tasks.html',
        tasks=tasks_list,
        total_tasks=total_tasks,
        active_tasks=active_tasks_count,
        total_completions=total_completions,
        total_rewards_paid=total_rewards_paid,
        format_doge=format_doge,
    )

@app.route('/admin/task/create', methods=['POST'])
@require_admin
def admin_create_task():
    """Create new task"""
    data = request.form
    task_id = data.get('task_id', f"task_{secrets.token_hex(4)}")
    
    create_task(
        task_id=task_id,
        title=data.get('title'),
        description=data.get('description'),
        reward=float(data.get('reward', 0)),
        url=data.get('url'),
        icon=data.get('icon', 'star'),
        task_type=data.get('task_type', 'telegram'),
        requires_channel=data.get('requires_channel') == 'on',
        channel_username=data.get('channel_username')
    )
    
    return redirect(url_for('admin_tasks'))

@app.route('/admin/task/delete/<task_id>', methods=['POST'])
@require_admin
def admin_delete_task(task_id):
    """Delete task"""
    delete_task(task_id)
    return jsonify({'success': True})

@app.route('/admin/withdrawals')
@require_admin
def admin_withdrawals():
    """Admin withdrawals management"""
    from database import execute_query
    filter_type = request.args.get('filter', 'pending')
    page = int(request.args.get('page', 1))
    per_page = 50

    if filter_type == 'all':
        rows = execute_query("SELECT * FROM withdrawals ORDER BY created_at DESC LIMIT %s OFFSET %s",
                             (per_page, (page-1)*per_page), fetch_all=True) or []
        total_count = (execute_query("SELECT COUNT(*) as c FROM withdrawals", fetch_one=True) or {}).get('c', 0)
    else:
        rows = execute_query(
            "SELECT * FROM withdrawals WHERE status=%s ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (filter_type, per_page, (page-1)*per_page), fetch_all=True) or []
        total_count = (execute_query("SELECT COUNT(*) as c FROM withdrawals WHERE status=%s",
                                     (filter_type,), fetch_one=True) or {}).get('c', 0)

    total_pages = max(1, (total_count + per_page - 1) // per_page)

    # Stats
    def _count(s):
        r = execute_query("SELECT COUNT(*) as c FROM withdrawals WHERE status=%s",(s,),fetch_one=True)
        return r['c'] if r else 0
    def _sum(s):
        r = execute_query("SELECT SUM(amount) as t FROM withdrawals WHERE status=%s",(s,),fetch_one=True)
        return float(r['t']) if r and r.get('t') else 0.0

    pending_count  = _count('pending')
    approved_count = _count('completed')
    rejected_count = _count('rejected')
    total_withdrawn = _sum('completed')

    return render_template('admin_withdrawals.html',
        withdrawals=rows,
        page=page,
        total_pages=total_pages,
        filter=filter_type,
        pending_count=pending_count,
        approved_count=approved_count,
        rejected_count=rejected_count,
        total_withdrawn=total_withdrawn,
        format_doge=format_doge,
    )

@app.route('/admin/withdrawal/<withdrawal_id>/process', methods=['POST'])
@require_admin
def admin_process_withdrawal(withdrawal_id):
    """Process withdrawal"""
    data = request.form
    action = data.get('action')
    tx_hash = data.get('tx_hash')
    note = data.get('note')
    
    if action == 'approve':
        update_withdrawal(withdrawal_id, 'completed', tx_hash, note)
    elif action == 'reject':
        update_withdrawal(withdrawal_id, 'rejected', None, note)
        # TODO: Refund balance
    
    return redirect(url_for('admin_withdrawals'))

@app.route('/admin/promo')
@require_admin
def admin_promo():
    """Admin promo codes management"""
    from database import get_promo_stats, get_recent_redemptions
    codes = get_all_promo_codes()
    stats = get_promo_stats()
    recent_redemptions = get_recent_redemptions(limit=10)
    return render_template('admin_promo.html', 
                         codes=codes, 
                         stats=stats,
                         recent_redemptions=recent_redemptions,
                         format_doge=format_doge)

@app.route('/admin/promo/create', methods=['POST'])
@require_admin
def admin_create_promo():
    """Create promo code"""
    data = request.get_json() if request.is_json else request.form
    code = data.get('code', secrets.token_hex(4).upper()).upper()
    reward = float(data.get('reward', 0))
    max_uses = int(data.get('max_uses')) if data.get('max_uses') else None
    expires_at = data.get('expires_at') if data.get('expires_at') else None
    description = data.get('description', '')
    
    success = create_promo_code(code, reward, max_uses, expires_at, description)
    
    if request.is_json:
        return jsonify({'success': success, 'code': code})
    return redirect(url_for('admin_promo'))

@app.route('/admin/promo/<code>/details')
@require_admin
def admin_promo_details(code):
    """Get promo code details"""
    promo = get_promo_code(code)
    if not promo:
        return jsonify({'success': False, 'error': 'Code not found'})
    
    return jsonify({
        'success': True,
        'code': {
            'code': promo['code'],
            'reward': format_doge(promo['reward']),
            'uses': promo['uses'],
            'max_uses': promo['max_uses'],
            'status': promo['status'],
            'created_at': promo['created_at'].strftime('%Y-%m-%d %H:%M') if promo.get('created_at') else None,
            'expires_at': promo['expires_at'].strftime('%Y-%m-%d %H:%M') if promo.get('expires_at') else None,
            'description': promo.get('description', '')
        }
    })

@app.route('/admin/promo/<code>/deactivate', methods=['POST'])
@require_admin
def admin_deactivate_promo(code):
    """Deactivate promo code"""
    from database import update_promo_status
    success = update_promo_status(code, 'expired')
    return jsonify({'success': success})

@app.route('/admin/promo/<code>/activate', methods=['POST'])
@require_admin
def admin_activate_promo(code):
    """Activate promo code"""
    from database import update_promo_status
    success = update_promo_status(code, 'active')
    return jsonify({'success': success})

@app.route('/admin/promo/<code>/delete', methods=['POST'])
@require_admin
def admin_delete_promo(code):
    """Delete promo code"""
    from database import delete_promo_code
    success = delete_promo_code(code)
    return jsonify({'success': success})

@app.route('/admin/config', methods=['GET', 'POST'])
@require_admin
def admin_config():
    """Admin configuration"""
    if request.method == 'POST':
        for key, value in request.form.items():
            set_config(key, value)
        return redirect(url_for('admin_config'))
    
    config = get_all_config()
    return render_template('admin_config.html', config=config)

# ── ADMIN MINING PLANS ─────────────────────────────────────────────────────
@app.route('/admin/mining')
@require_admin
def admin_mining():
    """Admin panel: manage mining plans"""
    raw_plans = get_all_mining_plans(active_only=False)
    # Convert Decimal/other non-serializable types to plain Python types
    plans = []
    for p in (raw_plans or []):
        plans.append({
            'id':            p.get('id'),
            'name':          p.get('name', ''),
            'tier':          p.get('tier', ''),
            'price':         float(p.get('price', 0)),
            'hourly_rate':   float(p.get('hourly_rate', 0)),
            'duration_days': int(p.get('duration_days', 30)),
            'description':   p.get('description', '') or '',
            'active':        int(p.get('active', 1)),
            'one_time_only': int(p.get('one_time_only', 0)),
        })
    return render_template('admin_mining.html', plans=plans, active_page='mining')

@app.route('/admin/mining/plan/create', methods=['POST'])
@require_admin
def admin_mining_plan_create():
    data = request.get_json() or request.form.to_dict()
    try:
        name         = data['name']
        tier         = data.get('tier', name.lower())
        price        = float(data['price'])
        hourly_rate  = float(data['hourly_rate'])
        duration_days= int(data.get('duration_days', 30))
        description  = data.get('description', '')
        create_mining_plan(name, tier, price, hourly_rate, duration_days, description)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/admin/mining/plan/<int:plan_id>/update', methods=['POST'])
@require_admin
def admin_mining_plan_update(plan_id):
    data = request.get_json() or request.form.to_dict()
    try:
        update_mining_plan(
            plan_id,
            name=data.get('name'),
            price=data.get('price'),
            hourly_rate=data.get('hourly_rate'),
            duration_days=data.get('duration_days'),
            description=data.get('description'),
            active=data.get('active'),
            one_time_only=data.get('one_time_only')
        )
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/admin/mining/plan/<int:plan_id>/delete', methods=['POST'])
@require_admin
def admin_mining_plan_delete(plan_id):
    try:
        delete_mining_plan(plan_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/admin/icons')
@require_admin
def admin_icons():
    """Admin icons management"""
    # Get list of uploaded icon files
    uploaded_icons = {}
    for category in ['menu', 'status', 'currency', 'misc', 'tiers', 'actions', 'arrows']:
        category_path = os.path.join(ICONS_PATH, category)
        if os.path.exists(category_path):
            files = [f for f in os.listdir(category_path) if f.endswith(('.png', '.gif', '.svg', '.webp'))]
            uploaded_icons[category] = files
        else:
            uploaded_icons[category] = []
    
    return render_template('admin_icons.html', 
        icons_config=ICONS_CONFIG,
        uploaded_icons=uploaded_icons
    )

@app.route('/admin/icons/upload', methods=['POST'])
@require_admin
def admin_upload_icon():
    """Upload icon file"""
    if 'icon_file' not in request.files:
        return jsonify({'success': False, 'message': 'No file provided'})
    
    file = request.files['icon_file']
    category = request.form.get('category', 'misc')
    
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'})
    
    # Check file extension
    allowed_extensions = {'png', 'gif', 'svg', 'webp'}
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in allowed_extensions:
        return jsonify({'success': False, 'message': 'Invalid file type. Use PNG, GIF, SVG or WEBP'})
    
    # Save file
    category_path = os.path.join(ICONS_PATH, category)
    os.makedirs(category_path, exist_ok=True)
    
    # Secure filename
    filename = file.filename.replace(' ', '_').lower()
    filepath = os.path.join(category_path, filename)
    file.save(filepath)
    
    return jsonify({
        'success': True, 
        'message': f'Icon uploaded: {filename}',
        'filename': filename,
        'category': category
    })

@app.route('/admin/config/save', methods=['POST'])
@require_admin
def admin_config_save():
    """Save all config via JSON"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'})
    
    for key, value in data.items():
        set_config(key, value)
    
    return jsonify({'success': True})

@app.route('/admin/config/reset-tasks', methods=['POST'])
@require_admin
def admin_reset_tasks():
    """Reset all task completions"""
    from database import reset_all_task_completions
    count = reset_all_task_completions()
    return jsonify({'success': True, 'count': count})

@app.route('/admin/config/clear-cache', methods=['POST'])
@require_admin
def admin_clear_cache():
    """Clear verification cache"""
    global _channel_cache
    _channel_cache = {}
    return jsonify({'success': True})

@app.route('/admin/user/<user_id>/ban', methods=['POST'])
@require_admin
def admin_ban_user(user_id):
    """Ban user"""
    reason = request.form.get('reason', 'Violation of terms')
    ban_user(user_id, reason)
    return jsonify({'success': True})

@app.route('/admin/user/<user_id>/unban', methods=['POST'])
@require_admin
def admin_unban_user(user_id):
    """Unban user"""
    unban_user(user_id)
    return jsonify({'success': True})


# ============================================
# ADMIN API — Tasks
# ============================================

@app.route('/admin/api/task/<task_id>')
@require_admin
def admin_api_get_task(task_id):
    """Get task details as JSON"""
    task = get_task(task_id)
    if not task:
        return jsonify({'success': False, 'message': 'Task not found'})
    t = dict(task)
    for k, v in t.items():
        if hasattr(v, 'isoformat'): t[k] = str(v)
        elif hasattr(v, '__float__'): t[k] = float(v)
    t.setdefault('category', t.get('task_type', 'telegram'))
    t.setdefault('is_active', bool(t.get('active', 1)))
    t.setdefault('completions', t.get('current_completions', 0))
    t.setdefault('link', t.get('url', ''))
    return jsonify({'success': True, 'task': t})


@app.route('/admin/api/task/update', methods=['POST'])
@require_admin
def admin_api_update_task():
    """Update a task"""
    data = request.get_json(force=True) or {}
    task_id_raw = data.get('task_id')
    if not task_id_raw:
        return jsonify({'success': False, 'message': 'Missing task_id'})
    task = get_task(str(task_id_raw))
    if not task:
        return jsonify({'success': False, 'message': 'Task not found'})
    updates = {}
    if 'title'            in data: updates['title']            = data['title']
    if 'description'      in data: updates['description']      = data['description']
    if 'reward'           in data: updates['reward']           = float(data['reward'])
    if 'icon'             in data: updates['icon']             = data['icon']
    if 'sort_order'       in data: updates['sort_order']       = int(data['sort_order'])
    if 'link'             in data: updates['url']              = data['link']
    if 'channel_username' in data: updates['channel_username'] = data['channel_username']
    if updates:
        update_task(task['task_id'], **updates)
    return jsonify({'success': True})


@app.route('/admin/api/task/<task_id>/toggle', methods=['POST'])
@require_admin
def admin_api_toggle_task(task_id):
    """Enable or disable a task"""
    from database import execute_query
    data = request.get_json(force=True) or {}
    is_active = data.get('is_active', True)
    # task_id may be numeric id or string task_id
    task = get_task(str(task_id))
    if not task:
        return jsonify({'success': False, 'message': 'Task not found'})
    update_task(task['task_id'], active=1 if is_active else 0)
    return jsonify({'success': True})


@app.route('/admin/api/task/<task_id>/delete', methods=['POST'])
@require_admin
def admin_api_delete_task(task_id):
    """Delete a task"""
    task = get_task(str(task_id))
    if task:
        delete_task(task['task_id'])
    return jsonify({'success': True})


@app.route('/admin/api/task/<task_id>/move', methods=['POST'])
@require_admin
def admin_api_move_task(task_id):
    """Move a task up or down in sort order"""
    from database import execute_query
    data = request.get_json(force=True) or {}
    direction = data.get('direction', 'down')
    task = get_task(task_id)
    if not task:
        return jsonify({'success': False, 'message': 'Task not found'})
    current_order = task.get('sort_order', 0)
    if direction == 'up':
        neighbour = execute_query(
            "SELECT task_id, sort_order FROM tasks WHERE sort_order < %s ORDER BY sort_order DESC LIMIT 1",
            (current_order,), fetch_one=True)
    else:
        neighbour = execute_query(
            "SELECT task_id, sort_order FROM tasks WHERE sort_order > %s ORDER BY sort_order ASC LIMIT 1",
            (current_order,), fetch_one=True)
    if neighbour:
        update_task(task_id, sort_order=neighbour['sort_order'])
        update_task(neighbour['task_id'], sort_order=current_order)
    return jsonify({'success': True})


# ============================================
# ADMIN API — Withdrawals
# ============================================

@app.route('/admin/api/withdrawal/approve', methods=['POST'])
@require_admin
def admin_api_approve_withdrawal():
    """Approve a withdrawal"""
    data = request.get_json(force=True) or {}
    withdrawal_id = data.get('withdrawal_id')
    tx_hash = data.get('tx_hash', '')
    note = data.get('note', '')
    if not withdrawal_id:
        return jsonify({'success': False, 'message': 'Missing withdrawal_id'})
    update_withdrawal(str(withdrawal_id), 'completed', tx_hash or None, note or None)

    # ── Notificación al usuario ──
    if _NOTIF_OK:
        try:
            from database import execute_query as _eq
            from datetime import datetime as _dt
            w = _eq("SELECT user_id, amount, currency, wallet_address FROM withdrawals WHERE withdrawal_id=%s OR id=%s",
                    (str(withdrawal_id), str(withdrawal_id)), fetch_one=True)
            if w:
                user_obj = get_user(w['user_id'])
                lang_code = user_obj.get('language_code') if user_obj else None
                notify_withdrawal_approved(
                    user_id=int(w['user_id']),
                    amount=w.get('amount', '?'),
                    currency=w.get('currency', 'DOGE'),
                    wallet=w.get('wallet_address', '?'),
                    withdrawal_id=str(withdrawal_id),
                    date=_dt.now().strftime('%Y-%m-%d %H:%M'),
                    language_code=lang_code,
                )
        except Exception as _ne:
            logger.warning(f"Withdrawal approve notification error: {_ne}")
    return jsonify({'success': True})


@app.route('/admin/api/withdrawal/reject', methods=['POST'])
@require_admin
def admin_api_reject_withdrawal():
    """Reject a withdrawal and refund the user"""
    from database import execute_query
    data = request.get_json(force=True) or {}
    withdrawal_id = data.get('withdrawal_id')
    reason = data.get('reason', 'Rejected by admin')
    if not withdrawal_id:
        return jsonify({'success': False, 'message': 'Missing withdrawal_id'})
    # Get the withdrawal to refund
    w = execute_query(
        "SELECT * FROM withdrawals WHERE withdrawal_id = %s OR id = %s",
        (str(withdrawal_id), str(withdrawal_id)), fetch_one=True
    )
    if w and w.get('status') == 'pending':
        update_withdrawal(w['withdrawal_id'], 'rejected', None, reason)
        # Refund: return amount (including fee) to user
        refund = float(w.get('amount', 0))
        if refund > 0:
            update_balance(w['user_id'], refund, 'withdrawal_refund', f'Withdrawal rejected: {reason}')

        # ── Notificación al usuario ──
        if _NOTIF_OK:
            try:
                user_obj = get_user(w['user_id'])
                lang_code = user_obj.get('language_code') if user_obj else None
                notify_withdrawal_rejected(
                    user_id=int(w['user_id']),
                    amount=w.get('amount', '?'),
                    currency=w.get('currency', 'DOGE'),
                    withdrawal_id=str(w['withdrawal_id']),
                    reason=reason,
                    language_code=lang_code,
                )
            except Exception as _ne:
                logger.warning(f"Withdrawal reject notification error: {_ne}")
    return jsonify({'success': True})


# ============================================
# ADMIN API — User detail, balance & history
# ============================================

@app.route('/admin/api/user/<user_id>')
@require_admin
def admin_api_get_user(user_id):
    """Return user details as JSON for the modal"""
    user = get_user(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found'})
    user_dict = dict(user)
    # Convert non-serialisable types
    for k, v in user_dict.items():
        if hasattr(v, 'isoformat'):
            user_dict[k] = str(v)
        elif hasattr(v, '__float__'):
            user_dict[k] = float(v)
    user_dict['is_banned'] = bool(user_dict.get('banned', 0))
    return jsonify({'success': True, 'user': user_dict})


@app.route('/admin/api/user/adjust-balance', methods=['POST'])
@require_admin
def admin_api_adjust_balance():
    """Add or remove DOGE balance for a user"""
    data = request.get_json(force=True) or {}
    user_id = data.get('user_id')
    try:
        amount = float(data.get('amount', 0))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Invalid amount'})
    reason = data.get('reason', 'Admin adjustment') or 'Admin adjustment'

    if not user_id:
        return jsonify({'success': False, 'message': 'Missing user_id'})
    if amount == 0:
        return jsonify({'success': False, 'message': 'Amount cannot be zero'})

    user = get_user(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found'})

    action = 'admin_add' if amount > 0 else 'admin_remove'
    ok = update_balance(user_id, amount, action, f'[ADMIN] {reason}')
    if ok:
        return jsonify({'success': True, 'message': f'Balance adjusted by {amount:+.8f} DOGE'})
    return jsonify({'success': False, 'message': 'Balance adjustment failed (insufficient funds?)'})


@app.route('/admin/api/user/<user_id>/history')
@require_admin
def admin_api_user_history(user_id):
    """Return full balance history for a user"""
    limit  = int(request.args.get('limit', 50))
    history = get_balance_history(user_id, limit=limit)
    rows = []
    for h in history:
        row = dict(h)
        for k, v in row.items():
            if hasattr(v, 'isoformat'):
                row[k] = str(v)
            elif hasattr(v, '__float__'):
                row[k] = float(v)
        rows.append(row)
    return jsonify({'success': True, 'history': rows})


@app.route('/admin/api/user/<user_id>/ban', methods=['POST'])
@require_admin
def admin_api_ban_user(user_id):
    """Ban a user via API"""
    reason = (request.get_json(force=True) or {}).get('reason', 'Admin action')
    ban_user(user_id, reason)
    return jsonify({'success': True})


@app.route('/admin/api/user/<user_id>/unban', methods=['POST'])
@require_admin
def admin_api_unban_user(user_id):
    """Unban a user via API"""
    unban_user(user_id)
    return jsonify({'success': True})

@app.route('/admin/logout')
def admin_logout():
    """Admin logout"""
    session.pop('admin_authenticated', None)
    return redirect(url_for('admin_login'))

# ============================================
# ERROR HANDLERS
# ============================================

@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', code=404, message='Page not found'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', code=500, message='Server error'), 500

# ============================================
# TEMPLATE FILTERS
# ============================================

@app.template_filter('format_doge')
def format_doge_filter(value):
    return format_doge(value)

@app.template_filter('timeago')
def timeago_filter(dt):
    if not dt:
        return 'Never'
    if isinstance(dt, str):
        dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
    
    diff = datetime.now() - dt
    if diff.days > 0:
        return f"{diff.days}d ago"
    elif diff.seconds > 3600:
        return f"{diff.seconds // 3600}h ago"
    elif diff.seconds > 60:
        return f"{diff.seconds // 60}m ago"
    return "Just now"

# ============================================
# RUN
# ============================================

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
