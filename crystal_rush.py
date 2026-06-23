"""
crystal_rush.py — CRYSTAL RUSH ⛏️
Juego de minería activo (tap) para CraftGems.

Self-contained Flask Blueprint:
  • Mapa generado y resuelto 100% server-side (anti-cheat). El cliente solo
    envía coordenadas; nunca recibe el tipo de un bloque sin romper.
  • Toda la economía (GEM, upgrades, conversión GEM→TON) es atómica con
    transacciones SELECT ... FOR UPDATE para evitar doble-gasto.
  • Reutiliza la capa MySQL de database.py y el saldo TON (columna doge_balance).

Integración en app.py:
    from crystal_rush import crystal_rush_bp, init_crystal_rush
    app.register_blueprint(crystal_rush_bp)
    init_crystal_rush()
"""

import os
import json
import time
import random
import secrets
import logging
import contextlib
from functools import wraps
from decimal import Decimal

from flask import (
    Blueprint, render_template, request, jsonify,
    session, redirect, url_for
)

from database import get_connection, execute_query, get_user, get_config, set_config

logger = logging.getLogger(__name__)

crystal_rush_bp = Blueprint('crystal_rush', __name__)

# ════════════════════════════════════════════════════════════════
#  CONSTANTES DE JUEGO
# ════════════════════════════════════════════════════════════════

COLS = 8
ROWS = 12
GRID = COLS * ROWS                 # 96 bloques
MAX_LEVEL = 30
PICKAXE_MAX = 100
BASE_BAG = 30
MAX_DYNAMITE = 5
COMBO_THRESHOLD = 3                # minerales valiosos seguidos -> FEVER
COMBO_DURATION = 8                 # segundos de FEVER
COMBO_MULT = 2

# idx -> (key, emoji, base_hp, gem, base_prob)
MINERALS = [
    ('rock',    '🪨', 3, 0,    0.50),
    ('dirt',    '🟫', 1, 1,    0.20),
    ('coal',    '⬛', 2, 5,    0.12),
    ('iron',    '🔩', 3, 15,   0.08),
    ('gold',    '🥇', 4, 50,   0.05),
    ('crystal', '💎', 5, 150,  0.03),
    ('epic',    '🌟', 6, 500,  0.015),
    ('diamond', '👑', 8, 2000, 0.005),
]
RARE_START = 2                     # idx >= 2 cuenta como "valioso" (combo + venas)

# Upgrades permanentes por usuario
UPGRADES = {
    'speed':  {'max': 5, 'costs': [200, 500, 1000, 2000, 4000]},
    'damage': {'max': 5, 'costs': [300, 700, 1500, 3000, 6000]},
    'luck':   {'max': 5, 'costs': [500, 1000, 2000, 4000, 8000]},
    'bag':    {'max': 5, 'costs': [400, 800, 1600, 3200, 6400]},
}

# Defaults de config (clave -> valor)
CONFIG_DEFAULTS = {
    'mine_enabled':            '1',
    'mine_gem_to_ton_rate':    '0.0001',
    'mine_daily_convert_limit': '500',
    'mine_pickaxe_repair_cost': '50',
    'mine_dynamite_cost':       '300',
}


# ════════════════════════════════════════════════════════════════
#  DB: creación de tablas + helpers de transacción
# ════════════════════════════════════════════════════════════════

def init_crystal_rush():
    """Crea tablas e inserta config por defecto. Idempotente."""
    execute_query("""
        CREATE TABLE IF NOT EXISTS mine_sessions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id VARCHAR(50) NOT NULL,
            level INT DEFAULT 1,
            map_seed VARCHAR(100) NOT NULL,
            map_state JSON NOT NULL,
            inventory JSON,
            pickaxe_hp INT DEFAULT 100,
            combo_count INT DEFAULT 0,
            dynamite_count INT DEFAULT 0,
            started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_action DATETIME DEFAULT CURRENT_TIMESTAMP,
            status ENUM('active','sold','abandoned') DEFAULT 'active',
            INDEX idx_cr_user (user_id),
            INDEX idx_cr_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    execute_query("""
        CREATE TABLE IF NOT EXISTS mine_upgrades (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id VARCHAR(50) NOT NULL UNIQUE,
            gem_balance DECIMAL(20,2) DEFAULT 0,
            gem_total_earned DECIMAL(20,2) DEFAULT 0,
            upgrade_speed INT DEFAULT 0,
            upgrade_damage INT DEFAULT 0,
            upgrade_luck INT DEFAULT 0,
            upgrade_bag INT DEFAULT 0,
            total_runs INT DEFAULT 0,
            total_minerals INT DEFAULT 0,
            deepest_level INT DEFAULT 0,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_cru_user (user_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    execute_query("""
        CREATE TABLE IF NOT EXISTS mine_conversions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id VARCHAR(50) NOT NULL,
            gem_amount DECIMAL(20,2) NOT NULL,
            ton_amount DECIMAL(20,9) NOT NULL,
            rate DECIMAL(10,6) NOT NULL,
            converted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_crc_user (user_id),
            INDEX idx_crc_date (converted_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    for k, v in CONFIG_DEFAULTS.items():
        execute_query(
            "INSERT IGNORE INTO config (config_key, config_value) VALUES (%s, %s)",
            (k, v)
        )
    logger.info("[crystal_rush] tablas + config listas")


@contextlib.contextmanager
def _tx():
    """Transacción explícita con cursor dict. Hace rollback ante error."""
    conn = get_connection()
    cur = None
    try:
        conn.autocommit = False
        cur = conn.cursor(dictionary=True)
        yield conn, cur
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        if cur:
            try:
                cur.close()
            except Exception:
                pass
        try:
            conn.autocommit = True
        except Exception:
            pass
        conn.close()


def _loads(v, default):
    if v is None:
        return default
    if isinstance(v, (bytes, bytearray)):
        v = v.decode('utf-8')
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return default
    return v


# ════════════════════════════════════════════════════════════════
#  GENERACIÓN DE MAPA (determinista + venas)
# ════════════════════════════════════════════════════════════════

def _weights(luck_level):
    """Pesos por mineral. Suerte mueve masa de Roca hacia minerales raros."""
    bonus = luck_level * 0.02
    rock_w = max(0.05, MINERALS[0][4] - bonus)
    removed = MINERALS[0][4] - rock_w
    rare_sum = sum(MINERALS[i][4] for i in range(RARE_START, len(MINERALS)))
    w = [rock_w, MINERALS[1][4]]
    for i in range(RARE_START, len(MINERALS)):
        w.append(MINERALS[i][4] + (removed * MINERALS[i][4] / rare_sum if rare_sum else 0))
    return w


def _pick(rnd, weights):
    r = rnd.random() * sum(weights)
    acc = 0.0
    for i, wv in enumerate(weights):
        acc += wv
        if r <= acc:
            return i
    return len(weights) - 1


def _neighbors(x, y):
    out = []
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < COLS and 0 <= ny < ROWS:
            out.append((nx, ny))
    return out


def _extra_hp(level):
    return (level - 1) // 3            # +1 HP cada 3 niveles


def _gen_map(seed, level, luck_level):
    rnd = random.Random("%s:%d" % (seed, level))
    extra = _extra_hp(level)
    weights = _weights(luck_level)
    cells = []
    for _ in range(GRID):
        idx = _pick(rnd, weights)
        mh = MINERALS[idx][2] + extra
        cells.append({'t': idx, 'hp': mh, 'mh': mh, 'b': 0, 'h': 0})

    # Venas: un mineral valioso "contagia" a vecinos de roca/tierra (60%)
    for i in range(GRID):
        t = cells[i]['t']
        if t >= RARE_START:
            x, y = i % COLS, i // COLS
            for nx, ny in _neighbors(x, y):
                ni = ny * COLS + nx
                if cells[ni]['t'] <= 1 and rnd.random() < 0.60:
                    mh = MINERALS[t][2] + extra
                    cells[ni] = {'t': t, 'hp': mh, 'mh': mh, 'b': 0, 'h': 0}

    return {'cells': cells, 'cleared': 0, 'cf': 0}


def _level_mult(level):
    return 1.0 + (level - 1) * 0.10    # tabla = valores en nivel 1


# ════════════════════════════════════════════════════════════════
#  SERIALIZACIÓN SEGURA (nunca filtra bloques sin romper)
# ════════════════════════════════════════════════════════════════

def _client_cells(map_state):
    out = []
    for i, c in enumerate(map_state['cells']):
        cell = {'i': i, 'b': c['b'], 'h': c['h']}
        if c['b']:
            t = c['t']
            cell['e'] = MINERALS[t][1] if t >= 1 else ''      # roca rota = vacío
            cell['g'] = MINERALS[t][3]
        out.append(cell)
    return out


def _upgrades_row(cur, user_id):
    cur.execute(
        "SELECT * FROM mine_upgrades WHERE user_id=%s FOR UPDATE", (str(user_id),)
    )
    row = cur.fetchone()
    if not row:
        cur.execute(
            "INSERT INTO mine_upgrades (user_id) VALUES (%s)", (str(user_id),)
        )
        cur.execute(
            "SELECT * FROM mine_upgrades WHERE user_id=%s FOR UPDATE", (str(user_id),)
        )
        row = cur.fetchone()
    return row


def _ensure_upgrades(user_id):
    row = execute_query(
        "SELECT * FROM mine_upgrades WHERE user_id=%s", (str(user_id),), fetch_one=True
    )
    if not row:
        execute_query("INSERT IGNORE INTO mine_upgrades (user_id) VALUES (%s)", (str(user_id),))
        row = execute_query(
            "SELECT * FROM mine_upgrades WHERE user_id=%s", (str(user_id),), fetch_one=True
        )
    return row or {}


def _bag_slots(bag_level):
    return BASE_BAG + int(bag_level) * 5


def _public_state(user_id, sess, upg):
    """Estado compacto que ve el cliente."""
    inv = _loads(sess.get('inventory'), []) if sess else []
    ms = _loads(sess.get('map_state'), {'cells': [], 'cleared': 0, 'cf': 0}) if sess else None
    cf = (ms or {}).get('cf', 0)
    return {
        'enabled':       get_config('mine_enabled', '1') == '1',
        'level':         int(sess['level']) if sess else 0,
        'pickaxe_hp':    int(sess['pickaxe_hp']) if sess else PICKAXE_MAX,
        'pickaxe_max':   PICKAXE_MAX,
        'dynamite':      int(sess['dynamite_count']) if sess else 0,
        'dynamite_max':  MAX_DYNAMITE,
        'combo_count':   int(sess['combo_count']) if sess else 0,
        'combo_until':   cf,
        'inv_count':     len(inv),
        'inv_max':       _bag_slots(upg.get('upgrade_bag', 0)),
        'gem_balance':   float(upg.get('gem_balance', 0)),
        'gem_total':     float(upg.get('gem_total_earned', 0)),
        'up_speed':      int(upg.get('upgrade_speed', 0)),
        'up_damage':     int(upg.get('upgrade_damage', 0)),
        'up_luck':       int(upg.get('upgrade_luck', 0)),
        'up_bag':        int(upg.get('upgrade_bag', 0)),
        'deepest':       int(upg.get('deepest_level', 0)),
        'total_runs':    int(upg.get('total_runs', 0)),
        'has_session':   sess is not None and sess['status'] == 'active',
    }


# ════════════════════════════════════════════════════════════════
#  DECORATORS (auth propia, sin importar app.py -> evita ciclo)
# ════════════════════════════════════════════════════════════════

def _is_api():
    return request.path.startswith('/api/') or request.is_json


def _require_user(f):
    @wraps(f)
    def wrap(*a, **k):
        uid = session.get('user_id')
        if not uid:
            if _is_api():
                return jsonify({'success': False, 'error': 'auth'}), 401
            return render_template('telegram_required.html')
        user = get_user(uid)
        if not user:
            from database import create_user
            user = create_user(uid, session.get('username'), session.get('first_name', 'Player'))
        if user.get('banned'):
            if _is_api():
                return jsonify({'success': False, 'error': 'banned'}), 403
            return render_template('banned.html', reason=user.get('ban_reason'))
        return f(user, *a, **k)
    return wrap


def _require_admin(f):
    @wraps(f)
    def wrap(*a, **k):
        if not session.get('admin_authenticated'):
            return redirect(url_for('admin_login'))
        return f(*a, **k)
    return wrap


def _enabled():
    return get_config('mine_enabled', '1') == '1'


# ════════════════════════════════════════════════════════════════
#  PÁGINA
# ════════════════════════════════════════════════════════════════

@crystal_rush_bp.route('/mine')
@_require_user
def mine_page(user):
    upg = _ensure_upgrades(user['user_id'])
    sess = execute_query(
        "SELECT * FROM mine_sessions WHERE user_id=%s AND status='active' "
        "ORDER BY id DESC LIMIT 1", (str(user['user_id']),), fetch_one=True
    )
    minerals = [
        {'key': m[0], 'emoji': m[1], 'hp': m[2], 'gem': m[3],
         'prob': round(m[4] * 100, 1)} for m in MINERALS
    ]
    upgrades = {k: {'max': v['max'], 'costs': v['costs']} for k, v in UPGRADES.items()}
    return render_template(
        'mine.html',
        user=user,
        enabled=_enabled(),
        state=_public_state(user['user_id'], sess, upg),
        minerals=minerals,
        upgrades=upgrades,
        repair_cost=int(float(get_config('mine_pickaxe_repair_cost', '50'))),
        dynamite_cost=int(float(get_config('mine_dynamite_cost', '300'))),
        gem_rate=float(get_config('mine_gem_to_ton_rate', '0.0001')),
        daily_limit=float(get_config('mine_daily_convert_limit', '500')),
        format_ton=lambda a: "%.4f" % float(a or 0),
    )


# ════════════════════════════════════════════════════════════════
#  API
# ════════════════════════════════════════════════════════════════

@crystal_rush_bp.route('/api/mine/start', methods=['POST'])
@_require_user
def api_start(user):
    if not _enabled():
        return jsonify({'success': False, 'error': 'disabled'})
    uid = str(user['user_id'])

    with _tx() as (conn, cur):
        upg = _upgrades_row(cur, uid)
        cur.execute(
            "SELECT * FROM mine_sessions WHERE user_id=%s AND status='active' "
            "ORDER BY id DESC LIMIT 1", (uid,)
        )
        sess = cur.fetchone()
        if not sess:
            seed = secrets.token_hex(8)
            ms = _gen_map(seed, 1, int(upg.get('upgrade_luck', 0)))
            cur.execute(
                "INSERT INTO mine_sessions (user_id, level, map_seed, map_state, "
                "inventory, pickaxe_hp) VALUES (%s,1,%s,%s,'[]',%s)",
                (uid, seed, json.dumps(ms), PICKAXE_MAX)
            )
            cur.execute(
                "UPDATE mine_upgrades SET total_runs=total_runs+1, "
                "deepest_level=GREATEST(deepest_level,1) WHERE user_id=%s", (uid,)
            )
            cur.execute("SELECT * FROM mine_sessions WHERE id=%s", (cur.lastrowid,))
            sess = cur.fetchone()
            cur.execute("SELECT * FROM mine_upgrades WHERE user_id=%s", (uid,))
            upg = cur.fetchone()

        st = _public_state(uid, sess, upg)
        ms = _loads(sess['map_state'], {'cells': []})

    return jsonify({'success': True, 'state': st, 'cells': _client_cells(ms)})


@crystal_rush_bp.route('/api/mine/tap', methods=['POST'])
@_require_user
def api_tap(user):
    if not _enabled():
        return jsonify({'success': False, 'error': 'disabled'})
    uid = str(user['user_id'])
    data = request.get_json(silent=True) or {}
    try:
        x = int(data.get('x')); y = int(data.get('y'))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'coords'})
    if not (0 <= x < COLS and 0 <= y < ROWS):
        return jsonify({'success': False, 'error': 'coords'})
    idx = y * COLS + x

    with _tx() as (conn, cur):
        upg = _upgrades_row(cur, uid)
        cur.execute(
            "SELECT * FROM mine_sessions WHERE user_id=%s AND status='active' "
            "ORDER BY id DESC LIMIT 1 FOR UPDATE", (uid,)
        )
        sess = cur.fetchone()
        if not sess:
            return jsonify({'success': False, 'error': 'no_session'})

        ms = _loads(sess['map_state'], None)
        inv = _loads(sess['inventory'], [])
        if not ms or idx >= len(ms['cells']):
            return jsonify({'success': False, 'error': 'state'})
        cell = ms['cells'][idx]

        now = int(time.time())
        res = {'success': True, 'x': x, 'y': y, 'broke': False, 'full': False,
               'pickaxe_broken': False, 'level_cleared': False, 'mineral': None}

        if cell['b']:
            res.update({'broke': True, 'cells': _client_cells(ms),
                        'state': _public_state(uid, sess, upg)})
            return jsonify(res)

        dmg = 1 + int(upg.get('upgrade_damage', 0))
        cell['h'] += 1
        cell['hp'] -= dmg
        broke = cell['hp'] <= 0
        bag = _bag_slots(upg.get('upgrade_bag', 0))
        combo = int(sess['combo_count'])
        pick = int(sess['pickaxe_hp'])
        cf = ms.get('cf', 0)
        fever_now = now < cf

        if broke:
            t = cell['t']
            is_mineral = t >= 1
            if is_mineral and len(inv) >= bag:
                # mochila llena: no se rompe todavía, deja el bloque "casi roto"
                cell['hp'] = 1
                res.update({'full': True, 'cells': _client_cells(ms),
                            'state': _public_state(uid, sess, upg)})
                cur.execute(
                    "UPDATE mine_sessions SET map_state=%s, last_action=NOW() WHERE id=%s",
                    (json.dumps(ms), sess['id'])
                )
                return jsonify(res)

            cell['b'] = 1
            ms['cleared'] = ms.get('cleared', 0) + 1
            if is_mineral:
                inv.append({'k': t, 'x2': 1 if fever_now else 0})
                res['mineral'] = {'key': MINERALS[t][0], 'emoji': MINERALS[t][1],
                                  'gem': MINERALS[t][3], 'x2': fever_now}
            # pico
            pick -= 2 if t == 0 else 1
            # combo
            if t >= RARE_START:
                combo += 1
                if combo >= COMBO_THRESHOLD:
                    cf = now + COMBO_DURATION
            elif t == 0:
                combo = 0
                cf = 0
            ms['cf'] = cf

            res['broke'] = True

            if pick <= 0:
                pick = 0
                cur.execute(
                    "UPDATE mine_sessions SET status='abandoned', pickaxe_hp=0, "
                    "inventory='[]', map_state=%s, combo_count=%s, last_action=NOW() "
                    "WHERE id=%s", (json.dumps(ms), combo, sess['id'])
                )
                sess['status'] = 'abandoned'; sess['pickaxe_hp'] = 0
                sess['inventory'] = '[]'; sess['combo_count'] = combo
                res['pickaxe_broken'] = True
                res['cells'] = _client_cells(ms)
                res['state'] = _public_state(uid, sess, upg)
                return jsonify(res)

            # nivel completado -> baja un nivel (mapa nuevo, pico se conserva)
            if ms['cleared'] >= GRID and int(sess['level']) < MAX_LEVEL:
                new_level = int(sess['level']) + 1
                new_ms = _gen_map(sess['map_seed'], new_level, int(upg.get('upgrade_luck', 0)))
                cur.execute(
                    "UPDATE mine_sessions SET level=%s, map_state=%s, combo_count=0, "
                    "pickaxe_hp=%s, last_action=NOW() WHERE id=%s",
                    (new_level, json.dumps(new_ms), pick, sess['id'])
                )
                cur.execute(
                    "UPDATE mine_upgrades SET deepest_level=GREATEST(deepest_level,%s) "
                    "WHERE user_id=%s", (new_level, uid)
                )
                # persistir inventario actual (no se pierde al bajar)
                cur.execute(
                    "UPDATE mine_sessions SET inventory=%s WHERE id=%s",
                    (json.dumps(inv), sess['id'])
                )
                sess['level'] = new_level; sess['map_state'] = json.dumps(new_ms)
                sess['combo_count'] = 0; sess['pickaxe_hp'] = pick
                sess['inventory'] = json.dumps(inv)
                upg['deepest_level'] = max(int(upg.get('deepest_level', 0)), new_level)
                res['level_cleared'] = True
                res['cells'] = _client_cells(new_ms)
                res['state'] = _public_state(uid, sess, upg)
                return jsonify(res)

        # persistir estado normal
        cur.execute(
            "UPDATE mine_sessions SET map_state=%s, inventory=%s, pickaxe_hp=%s, "
            "combo_count=%s, last_action=NOW() WHERE id=%s",
            (json.dumps(ms), json.dumps(inv), pick, combo, sess['id'])
        )
        sess['map_state'] = json.dumps(ms); sess['inventory'] = json.dumps(inv)
        sess['pickaxe_hp'] = pick; sess['combo_count'] = combo
        res['cells'] = _client_cells(ms)
        res['state'] = _public_state(uid, sess, upg)

    return jsonify(res)


@crystal_rush_bp.route('/api/mine/dynamite', methods=['POST'])
@_require_user
def api_dynamite(user):
    if not _enabled():
        return jsonify({'success': False, 'error': 'disabled'})
    uid = str(user['user_id'])
    data = request.get_json(silent=True) or {}
    try:
        cx = int(data.get('x')); cy = int(data.get('y'))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'coords'})

    with _tx() as (conn, cur):
        upg = _upgrades_row(cur, uid)
        cur.execute(
            "SELECT * FROM mine_sessions WHERE user_id=%s AND status='active' "
            "ORDER BY id DESC LIMIT 1 FOR UPDATE", (uid,)
        )
        sess = cur.fetchone()
        if not sess:
            return jsonify({'success': False, 'error': 'no_session'})
        if int(sess['dynamite_count']) <= 0:
            return jsonify({'success': False, 'error': 'no_dynamite'})

        ms = _loads(sess['map_state'], None)
        inv = _loads(sess['inventory'], [])
        if not ms:
            return jsonify({'success': False, 'error': 'state'})
        bag = _bag_slots(upg.get('upgrade_bag', 0))
        now = int(time.time())
        fever_now = now < ms.get('cf', 0)
        gained = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                x, y = cx + dx, cy + dy
                if not (0 <= x < COLS and 0 <= y < ROWS):
                    continue
                c = ms['cells'][y * COLS + x]
                if c['b']:
                    continue
                c['b'] = 1; c['hp'] = 0; c['h'] = c['mh']
                ms['cleared'] = ms.get('cleared', 0) + 1
                t = c['t']
                if t >= 1 and len(inv) < bag:
                    inv.append({'k': t, 'x2': 1 if fever_now else 0})
                    gained.append(MINERALS[t][1])

        cur.execute(
            "UPDATE mine_sessions SET map_state=%s, inventory=%s, dynamite_count=dynamite_count-1, "
            "last_action=NOW() WHERE id=%s", (json.dumps(ms), json.dumps(inv), sess['id'])
        )
        cur.execute("SELECT * FROM mine_sessions WHERE id=%s", (sess['id'],))
        sess = cur.fetchone()
        st = _public_state(uid, sess, upg)

    return jsonify({'success': True, 'gained': gained, 'cells': _client_cells(ms), 'state': st})


@crystal_rush_bp.route('/api/mine/sell', methods=['POST'])
@_require_user
def api_sell(user):
    uid = str(user['user_id'])
    with _tx() as (conn, cur):
        upg = _upgrades_row(cur, uid)
        cur.execute(
            "SELECT * FROM mine_sessions WHERE user_id=%s AND status='active' "
            "ORDER BY id DESC LIMIT 1 FOR UPDATE", (uid,)
        )
        sess = cur.fetchone()
        if not sess:
            return jsonify({'success': False, 'error': 'no_session'})
        inv = _loads(sess['inventory'], [])
        if not inv:
            st = _public_state(uid, sess, upg)
            return jsonify({'success': True, 'sold': 0, 'gem_gained': 0, 'state': st})

        mult = _level_mult(int(sess['level']))
        total = 0.0
        for it in inv:
            k = int(it.get('k', 0))
            base = MINERALS[k][3]
            total += base * mult * (COMBO_MULT if it.get('x2') else 1)
        total = round(total, 2)
        count = len(inv)

        cur.execute(
            "UPDATE mine_upgrades SET gem_balance=gem_balance+%s, "
            "gem_total_earned=gem_total_earned+%s, total_minerals=total_minerals+%s "
            "WHERE user_id=%s", (total, total, count, uid)
        )
        cur.execute(
            "UPDATE mine_sessions SET inventory='[]', last_action=NOW() WHERE id=%s",
            (sess['id'],)
        )
        sess['inventory'] = '[]'
        cur.execute("SELECT * FROM mine_upgrades WHERE user_id=%s", (uid,))
        upg = cur.fetchone()
        st = _public_state(uid, sess, upg)

    return jsonify({'success': True, 'sold': count, 'gem_gained': total, 'state': st})


@crystal_rush_bp.route('/api/mine/upgrade', methods=['POST'])
@_require_user
def api_upgrade(user):
    uid = str(user['user_id'])
    data = request.get_json(silent=True) or {}
    key = data.get('key')
    if key not in UPGRADES:
        return jsonify({'success': False, 'error': 'bad_key'})
    col = 'upgrade_' + key
    spec = UPGRADES[key]

    with _tx() as (conn, cur):
        upg = _upgrades_row(cur, uid)
        cur_level = int(upg.get(col, 0))
        if cur_level >= spec['max']:
            return jsonify({'success': False, 'error': 'maxed'})
        cost = spec['costs'][cur_level]
        if float(upg.get('gem_balance', 0)) < cost:
            return jsonify({'success': False, 'error': 'insufficient', 'cost': cost})
        # `col` proviene de un whitelist fijo (UPGRADES) -> seguro interpolar.
        query = (
            "UPDATE mine_upgrades SET gem_balance=gem_balance-%s, "
            + col + "=" + col + "+1 "
            "WHERE user_id=%s AND gem_balance>=%s"
        )
        cur.execute(query, (cost, uid, cost))
        if cur.rowcount == 0:
            return jsonify({'success': False, 'error': 'insufficient'})
        cur.execute("SELECT * FROM mine_upgrades WHERE user_id=%s", (uid,))
        upg = cur.fetchone()
        sess = execute_query(
            "SELECT * FROM mine_sessions WHERE user_id=%s AND status='active' "
            "ORDER BY id DESC LIMIT 1", (uid,), fetch_one=True
        )
        st = _public_state(uid, sess, upg)

    return jsonify({'success': True, 'new_level': cur_level + 1, 'state': st})


@crystal_rush_bp.route('/api/mine/repair', methods=['POST'])
@_require_user
def api_repair(user):
    uid = str(user['user_id'])
    cost = int(float(get_config('mine_pickaxe_repair_cost', '50')))
    with _tx() as (conn, cur):
        upg = _upgrades_row(cur, uid)
        cur.execute(
            "SELECT * FROM mine_sessions WHERE user_id=%s AND status='active' "
            "ORDER BY id DESC LIMIT 1 FOR UPDATE", (uid,)
        )
        sess = cur.fetchone()
        if not sess:
            return jsonify({'success': False, 'error': 'no_session'})
        if int(sess['pickaxe_hp']) >= PICKAXE_MAX:
            return jsonify({'success': False, 'error': 'full_hp'})
        if float(upg.get('gem_balance', 0)) < cost:
            return jsonify({'success': False, 'error': 'insufficient', 'cost': cost})
        cur.execute(
            "UPDATE mine_upgrades SET gem_balance=gem_balance-%s "
            "WHERE user_id=%s AND gem_balance>=%s", (cost, uid, cost)
        )
        if cur.rowcount == 0:
            return jsonify({'success': False, 'error': 'insufficient'})
        cur.execute(
            "UPDATE mine_sessions SET pickaxe_hp=%s WHERE id=%s", (PICKAXE_MAX, sess['id'])
        )
        sess['pickaxe_hp'] = PICKAXE_MAX
        cur.execute("SELECT * FROM mine_upgrades WHERE user_id=%s", (uid,))
        upg = cur.fetchone()
        st = _public_state(uid, sess, upg)

    return jsonify({'success': True, 'state': st})


@crystal_rush_bp.route('/api/mine/buy-dynamite', methods=['POST'])
@_require_user
def api_buy_dynamite(user):
    uid = str(user['user_id'])
    cost = int(float(get_config('mine_dynamite_cost', '300')))
    with _tx() as (conn, cur):
        upg = _upgrades_row(cur, uid)
        cur.execute(
            "SELECT * FROM mine_sessions WHERE user_id=%s AND status='active' "
            "ORDER BY id DESC LIMIT 1 FOR UPDATE", (uid,)
        )
        sess = cur.fetchone()
        if not sess:
            return jsonify({'success': False, 'error': 'no_session'})
        if int(sess['dynamite_count']) >= MAX_DYNAMITE:
            return jsonify({'success': False, 'error': 'max_dynamite'})
        if float(upg.get('gem_balance', 0)) < cost:
            return jsonify({'success': False, 'error': 'insufficient', 'cost': cost})
        cur.execute(
            "UPDATE mine_upgrades SET gem_balance=gem_balance-%s "
            "WHERE user_id=%s AND gem_balance>=%s", (cost, uid, cost)
        )
        if cur.rowcount == 0:
            return jsonify({'success': False, 'error': 'insufficient'})
        cur.execute(
            "UPDATE mine_sessions SET dynamite_count=dynamite_count+1 WHERE id=%s", (sess['id'],)
        )
        cur.execute("SELECT * FROM mine_sessions WHERE id=%s", (sess['id'],))
        sess = cur.fetchone()
        cur.execute("SELECT * FROM mine_upgrades WHERE user_id=%s", (uid,))
        upg = cur.fetchone()
        st = _public_state(uid, sess, upg)

    return jsonify({'success': True, 'state': st})


@crystal_rush_bp.route('/api/mine/convert', methods=['POST'])
@_require_user
def api_convert(user):
    uid = str(user['user_id'])
    data = request.get_json(silent=True) or {}
    try:
        amount = round(float(data.get('amount', 0)), 2)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'amount'})
    if amount <= 0:
        return jsonify({'success': False, 'error': 'amount'})

    rate = float(get_config('mine_gem_to_ton_rate', '0.0001'))
    daily_limit = float(get_config('mine_daily_convert_limit', '500'))
    ton = round(amount * rate, 9)

    with _tx() as (conn, cur):
        upg = _upgrades_row(cur, uid)
        # límite diario
        cur.execute(
            "SELECT COALESCE(SUM(gem_amount),0) AS s FROM mine_conversions "
            "WHERE user_id=%s AND DATE(converted_at)=CURRENT_DATE", (uid,)
        )
        today = float(cur.fetchone()['s'] or 0)
        if today + amount > daily_limit:
            return jsonify({'success': False, 'error': 'daily_limit',
                            'remaining': max(0, daily_limit - today)})
        if float(upg.get('gem_balance', 0)) < amount:
            return jsonify({'success': False, 'error': 'insufficient'})

        # gasto atómico de GEM
        cur.execute(
            "UPDATE mine_upgrades SET gem_balance=gem_balance-%s "
            "WHERE user_id=%s AND gem_balance>=%s", (amount, uid, amount)
        )
        if cur.rowcount == 0:
            return jsonify({'success': False, 'error': 'insufficient'})

        # crédito TON (inline, misma transacción que el gasto de GEM)
        cur.execute("SELECT doge_balance FROM users WHERE user_id=%s FOR UPDATE", (uid,))
        urow = cur.fetchone()
        before = Decimal(str(urow['doge_balance'] or 0))
        after = before + Decimal(str(ton))
        cur.execute(
            "UPDATE users SET doge_balance=%s, total_earned=total_earned+%s WHERE user_id=%s",
            (float(after), float(ton), uid)
        )
        try:
            cur.execute(
                "INSERT INTO balance_history (user_id, action, amount, balance_before, "
                "balance_after, description) VALUES (%s,'mine_convert',%s,%s,%s,%s)",
                (uid, float(ton), float(before), float(after),
                 'Crystal Rush: %s GEM -> %s TON' % (amount, ton))
            )
        except Exception:
            pass  # balance_history es opcional
        cur.execute(
            "INSERT INTO mine_conversions (user_id, gem_amount, ton_amount, rate) "
            "VALUES (%s,%s,%s,%s)", (uid, amount, ton, rate)
        )
        cur.execute("SELECT * FROM mine_upgrades WHERE user_id=%s", (uid,))
        upg = cur.fetchone()
        sess = execute_query(
            "SELECT * FROM mine_sessions WHERE user_id=%s AND status='active' "
            "ORDER BY id DESC LIMIT 1", (uid,), fetch_one=True
        )
        st = _public_state(uid, sess, upg)

    return jsonify({'success': True, 'ton': ton, 'gem_spent': amount, 'state': st})


@crystal_rush_bp.route('/api/mine/stats')
@_require_user
def api_stats(user):
    uid = str(user['user_id'])
    upg = _ensure_upgrades(uid)
    sess = execute_query(
        "SELECT * FROM mine_sessions WHERE user_id=%s AND status='active' "
        "ORDER BY id DESC LIMIT 1", (uid,), fetch_one=True
    )
    today = execute_query(
        "SELECT COALESCE(SUM(gem_amount),0) AS s FROM mine_conversions "
        "WHERE user_id=%s AND DATE(converted_at)=CURRENT_DATE", (uid,), fetch_one=True
    )
    st = _public_state(uid, sess, upg)
    st['today_converted'] = float((today or {}).get('s', 0) or 0)
    st['daily_limit'] = float(get_config('mine_daily_convert_limit', '500'))
    return jsonify({'success': True, 'state': st})


# Hook opcional: el sistema de tasks puede regalar dynamite llamando esto.
def grant_dynamite(user_id, n=1):
    execute_query(
        "UPDATE mine_sessions SET dynamite_count=LEAST(%s, dynamite_count+%s) "
        "WHERE user_id=%s AND status='active'", (MAX_DYNAMITE, int(n), str(user_id))
    )


# ════════════════════════════════════════════════════════════════
#  ADMIN
# ════════════════════════════════════════════════════════════════

@crystal_rush_bp.route('/admin/mine')
@_require_admin
def admin_mine():
    stats = execute_query(
        "SELECT COUNT(*) AS players, COALESCE(SUM(gem_total_earned),0) AS gem_earned, "
        "COALESCE(SUM(total_runs),0) AS runs, COALESCE(MAX(deepest_level),0) AS deepest "
        "FROM mine_upgrades", fetch_one=True
    ) or {}
    conv = execute_query(
        "SELECT COUNT(*) AS n, COALESCE(SUM(gem_amount),0) AS gem, "
        "COALESCE(SUM(ton_amount),0) AS ton FROM mine_conversions", fetch_one=True
    ) or {}
    top = execute_query(
        "SELECT u.user_id, u.gem_balance, u.gem_total_earned, u.deepest_level, "
        "u.total_minerals, x.first_name, x.username FROM mine_upgrades u "
        "LEFT JOIN users x ON x.user_id=u.user_id "
        "ORDER BY u.gem_total_earned DESC LIMIT 25", fetch_all=True
    ) or []
    recent = execute_query(
        "SELECT c.*, x.first_name FROM mine_conversions c "
        "LEFT JOIN users x ON x.user_id=c.user_id "
        "ORDER BY c.id DESC LIMIT 30", fetch_all=True
    ) or []
    cfg = {
        'mine_enabled': get_config('mine_enabled', '1'),
        'mine_gem_to_ton_rate': get_config('mine_gem_to_ton_rate', '0.0001'),
        'mine_daily_convert_limit': get_config('mine_daily_convert_limit', '500'),
        'mine_pickaxe_repair_cost': get_config('mine_pickaxe_repair_cost', '50'),
        'mine_dynamite_cost': get_config('mine_dynamite_cost', '300'),
    }
    return render_template(
        'admin_mine.html', active_page='mine',
        stats=stats, conv=conv, top=top, recent=recent, cfg=cfg
    )


@crystal_rush_bp.route('/admin/mine/config', methods=['POST'])
@_require_admin
def admin_mine_config():
    fields = ['mine_gem_to_ton_rate', 'mine_daily_convert_limit',
              'mine_pickaxe_repair_cost', 'mine_dynamite_cost']
    for f in fields:
        v = request.form.get(f)
        if v is not None and v != '':
            set_config(f, v)
    set_config('mine_enabled', '1' if request.form.get('mine_enabled') == 'on' else '0')
    return redirect(url_for('crystal_rush.admin_mine'))
