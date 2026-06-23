"""
crystal_rush.py — CRYSTAL RUSH ⛏️  (v2 · alto nivel)
Juego de minería activo (tap) para CraftGems.

Self-contained Flask Blueprint:
  • Mapa generado y resuelto 100% server-side (anti-cheat). El cliente solo
    envía coordenadas; nunca recibe el tipo de un bloque sin romper.
  • Toda la economía (GEM, upgrades, conversión GEM→TON, misiones, logros,
    prestigio) es atómica con transacciones SELECT ... FOR UPDATE.
  • Reutiliza la capa MySQL de database.py y el saldo TON (columna doge_balance).

Sistemas:
  ⚡ Energía con regeneración offline      🔥 Combos escalables (x1.5 → x5)
  💥 Golpes críticos                       ⭐ Nivel de minero (XP)
  🏆 Prestigio / Renacimiento              🎯 Misiones diarias
  🥇 Logros permanentes                    🎁 Cofres / ☠️ Roca madre / 💥 Bombas
  ⛏️ Rangos de pico (Madera→Mítico)        🏅 Ranking global

Integración en app.py:
    from crystal_rush import crystal_rush_bp, init_crystal_rush
    app.register_blueprint(crystal_rush_bp)
    init_crystal_rush()
"""

import json
import time
import random
import secrets
import hashlib
import logging
import contextlib
from functools import wraps
from datetime import datetime, timezone
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
MAX_LEVEL = 50                     # más profundidad = más recorrido

# Pico
PICKAXE_MAX = 100

# Mochila
BASE_BAG = 30

# Energía
ENERGY_BASE = 120
DYNAMITE_ENERGY = 12

# Combo
COMBO_MIN_IDX = 3                  # idx>=3 (hierro+) construye combo
COMBO_WINDOW = 6                   # seg sin romper valioso -> se rompe el combo
# (umbral_combo, multiplicador)  — evaluar de mayor a menor
COMBO_TIERS = [(35, 5.0), (20, 3.0), (10, 2.0), (5, 1.5)]

# Misiones / logros
RARE_FIND_IDX = 4                  # idx>=4 (oro+) cuenta como "mineral raro"
DIAMOND_IDX = 7

# Dinamita
MAX_DYNAMITE = 9

# Especiales (campo cell['s']): 0 nada · 1 cofre · 2 roca madre · 3 bomba
SP_NONE, SP_TREASURE, SP_BEDROCK, SP_BOMB = 0, 1, 2, 3

# idx -> (key, emoji, base_hp, gem, base_prob)
MINERALS = [
    ('rock',    '🪨', 3,  0,    0.50),
    ('dirt',    '🟫', 1,  1,    0.20),
    ('coal',    '⬛', 2,  6,    0.12),
    ('iron',    '🔩', 3,  18,   0.08),
    ('gold',    '🥇', 4,  60,   0.05),
    ('crystal', '💎', 5,  180,  0.03),
    ('epic',    '🌟', 7,  650,  0.015),
    ('diamond', '👑', 9,  2500, 0.005),
]


def _costs(base, growth, n):
    out = []
    for i in range(n):
        out.append(int(round(base * (growth ** i) / 10.0)) * 10)
    return out


# Upgrades permanentes por usuario (6 ramas, costos exponenciales)
UPGRADES = {
    'damage': {'max': 10, 'costs': _costs(250, 1.85, 10),
               'name': 'Daño',     'icon': '⚔️',
               'desc': 'Cada nivel = +1 de daño por golpe.'},
    'luck':   {'max': 8,  'costs': _costs(450, 1.85, 8),
               'name': 'Suerte',   'icon': '🍀',
               'desc': '+2,5% de probabilidad de minerales raros.'},
    'bag':    {'max': 8,  'costs': _costs(350, 1.8, 8),
               'name': 'Mochila',  'icon': '🎒',
               'desc': '+6 espacios de inventario por nivel.'},
    'speed':  {'max': 8,  'costs': _costs(180, 1.7, 8),
               'name': 'Velocidad','icon': '⚡',
               'desc': 'Anima más rápido el pico (mejor sensación).'},
    'crit':   {'max': 6,  'costs': _costs(700, 1.95, 6),
               'name': 'Crítico',  'icon': '💥',
               'desc': '+6% de golpe crítico (x4 de daño).'},
    'energy': {'max': 6,  'costs': _costs(600, 1.9, 6),
               'name': 'Energía',  'icon': '🔋',
               'desc': '+30 de energía máxima por nivel.'},
}
UPGRADE_KEYS = list(UPGRADES.keys())

# Rangos de pico según nivel de la rama "damage"
PICK_TIERS = [
    (0,  'Madera',   '🪵', '#a06a3a'),
    (2,  'Piedra',   '🪨', '#9aa0a8'),
    (4,  'Hierro',   '🔩', '#c0c6cc'),
    (6,  'Oro',      '🥇', '#ffd24a'),
    (8,  'Diamante', '💎', '#5fe6ff'),
    (10, 'Mítico',   '🌌', '#c77dff'),
]

# Logros permanentes (una vez). cond evalúa stats de por vida.
ACHIEVEMENTS = [
    ('first_blood',    'Primer golpe',      '🪨', 50,    'Rompe tu primer bloque.',
     lambda s: s['total_minerals'] >= 1),
    ('depth_10',       'Las profundidades', '🔦', 400,   'Llega a profundidad 10.',
     lambda s: s['deepest'] >= 10),
    ('depth_25',       'Abismo',            '🌑', 1500,  'Llega a profundidad 25.',
     lambda s: s['deepest'] >= 25),
    ('depth_50',       'El núcleo',         '🔥', 8000,  'Llega a profundidad 50.',
     lambda s: s['deepest'] >= 50),
    ('min_1k',         'Minero dedicado',   '⛏️', 600,   'Recolecta 1.000 minerales.',
     lambda s: s['total_minerals'] >= 1000),
    ('min_10k',        'Maestro minero',    '🏗️', 4000,  'Recolecta 10.000 minerales.',
     lambda s: s['total_minerals'] >= 10000),
    ('rich_10k',       'Bolsillos llenos',  '💰', 1200,  'Gana 10.000 GEM en total.',
     lambda s: s['gem_total'] >= 10000),
    ('rich_100k',      'Magnate',           '🤑', 9000,  'Gana 100.000 GEM en total.',
     lambda s: s['gem_total'] >= 100000),
    ('first_diamond',  'Brillo eterno',     '👑', 800,   'Encuentra tu primer diamante.',
     lambda s: s['diamonds'] >= 1),
    ('diamond_10',     'Cazador de joyas',  '💠', 5000,  'Encuentra 10 diamantes.',
     lambda s: s['diamonds'] >= 10),
    ('treasure_5',     'Buscatesoros',      '🎁', 1800,  'Abre 5 cofres del tesoro.',
     lambda s: s['treasures'] >= 5),
    ('combo_20',       'Imparable',         '🔥', 1500,  'Encadena un combo de 20.',
     lambda s: s['best_combo'] >= 20),
    ('prestige_1',     'Renacido',          '♻️', 2500,  'Renace por primera vez.',
     lambda s: s['prestige'] >= 1),
    ('prestige_5',     'Leyenda viva',      '🌟', 18000, 'Renace 5 veces.',
     lambda s: s['prestige'] >= 5),
]

# Plantillas de misiones diarias: (key, plantilla_texto, min_t, max_t, paso, min_r, max_r)
MISSION_TEMPLATES = [
    ('blocks',   'Rompe %d bloques',              200, 420, 20, 300, 520),
    ('rares',    'Encuentra %d minerales raros',  10,  26,  2,  420, 720),
    ('level',    'Alcanza profundidad %d',        6,   13,  1,  360, 640),
    ('gem',      'Gana %d GEM minando',           3000, 9000, 500, 520, 940),
    ('treasure', 'Abre %d cofres del tesoro',     1,   3,   1,  640, 1040),
]

# Defaults de config (clave -> valor)
CONFIG_DEFAULTS = {
    'mine_enabled':             '1',
    'mine_gem_to_ton_rate':     '0.0001',
    'mine_daily_convert_limit': '500',
    'mine_pickaxe_repair_cost': '50',
    'mine_dynamite_cost':       '300',
    'mine_energy_regen_sec':    '18',     # seg por +1 de energía
    'mine_treasure_min':        '250',
    'mine_treasure_max':        '1400',
    'mine_prestige_req':        '15',     # profundidad base para 1er prestigio
}


# ════════════════════════════════════════════════════════════════
#  DB: creación de tablas + migraciones idempotentes
# ════════════════════════════════════════════════════════════════

def _safe_exec(sql, params=None):
    try:
        execute_query(sql, params)
        return True
    except Exception:
        return False


def init_crystal_rush():
    """Crea tablas, agrega columnas nuevas e inserta config. Idempotente."""
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

    # ── Columnas nuevas (v2) — ALTER individual, ignora si ya existen ──
    _alts = [
        "ALTER TABLE mine_upgrades ADD COLUMN upgrade_crit INT DEFAULT 0",
        "ALTER TABLE mine_upgrades ADD COLUMN upgrade_energy INT DEFAULT 0",
        "ALTER TABLE mine_upgrades ADD COLUMN energy INT DEFAULT %d" % ENERGY_BASE,
        "ALTER TABLE mine_upgrades ADD COLUMN energy_updated BIGINT DEFAULT 0",
        "ALTER TABLE mine_upgrades ADD COLUMN xp BIGINT DEFAULT 0",
        "ALTER TABLE mine_upgrades ADD COLUMN miner_level INT DEFAULT 1",
        "ALTER TABLE mine_upgrades ADD COLUMN prestige INT DEFAULT 0",
        "ALTER TABLE mine_upgrades ADD COLUMN diamonds_total INT DEFAULT 0",
        "ALTER TABLE mine_upgrades ADD COLUMN treasures_total INT DEFAULT 0",
        "ALTER TABLE mine_upgrades ADD COLUMN best_combo INT DEFAULT 0",
        "ALTER TABLE mine_upgrades ADD COLUMN claimed_ach JSON",
        "ALTER TABLE mine_upgrades ADD COLUMN daily_state JSON",
        "ALTER TABLE mine_sessions ADD COLUMN treasure_gem DECIMAL(20,2) DEFAULT 0",
    ]
    for a in _alts:
        _safe_exec(a)

    for k, v in CONFIG_DEFAULTS.items():
        _safe_exec(
            "INSERT IGNORE INTO config (config_key, config_value) VALUES (%s, %s)",
            (k, v)
        )
    logger.info("[crystal_rush] v2 tablas + columnas + config listas")


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
#  FÓRMULAS PURAS (sin DB)
# ════════════════════════════════════════════════════════════════

def _energy_regen_sec():
    try:
        return max(2, int(float(get_config('mine_energy_regen_sec', '18'))))
    except Exception:
        return 18


def _energy_max(energy_level, miner_level):
    return ENERGY_BASE + int(energy_level) * 30 + int(miner_level) * 2


def _live_energy(energy, energy_updated, emax, regen_sec, now=None):
    """Regenera energía según el tiempo transcurrido. Devuelve (energy, updated)."""
    now = now if now is not None else int(time.time())
    energy = int(energy)
    eu = int(energy_updated or 0)
    if eu == 0:
        return min(energy, emax), now
    if energy >= emax:
        return emax, now
    elapsed = now - eu
    if elapsed < regen_sec:
        return energy, eu
    gained = elapsed // regen_sec
    new_e = min(emax, energy + gained)
    new_eu = eu + gained * regen_sec
    return new_e, new_eu


def _combo_mult(combo):
    for thr, m in COMBO_TIERS:
        if combo >= thr:
            return m
    return 1.0


def _combo_next(combo):
    """(siguiente_umbral, mult_actual, mult_siguiente) para la barra de combo."""
    cur_m = _combo_mult(combo)
    nxt = None
    nxt_m = cur_m
    for thr, m in sorted(COMBO_TIERS):
        if combo < thr:
            nxt, nxt_m = thr, m
            break
    return nxt, cur_m, nxt_m


def _pick_tier(damage_level):
    chosen = PICK_TIERS[0]
    for thr, name, emoji, color in PICK_TIERS:
        if damage_level >= thr:
            chosen = (thr, name, emoji, color)
    return {'name': chosen[1], 'emoji': chosen[2], 'color': chosen[3]}


def _xp_needed(level):
    return 80 + (int(level) - 1) * 55      # crece por nivel


def _prestige_mult(prestige):
    return 1.0 + int(prestige) * 0.15


def _miner_mult(miner_level):
    return 1.0 + int(miner_level) * 0.01


def _prestige_req(prestige):
    try:
        base = int(float(get_config('mine_prestige_req', '15')))
    except Exception:
        base = 15
    return base + int(prestige) * 10


def _bag_slots(bag_level):
    return BASE_BAG + int(bag_level) * 6


def _extra_hp(level):
    return int(round((level - 1) * 0.6))    # escalado de dureza por profundidad


def _level_mult(level):
    return 1.0 + (level - 1) * 0.15         # tabla = valores en nivel 1


# ════════════════════════════════════════════════════════════════
#  MISIONES DIARIAS (deterministas por usuario+día)
# ════════════════════════════════════════════════════════════════

def _today_str():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')


def _gen_missions(user_id, day):
    """Elige 3 plantillas y las parametriza de forma determinista."""
    h = hashlib.sha256(("%s:%s" % (user_id, day)).encode()).hexdigest()
    rnd = random.Random(int(h[:16], 16))
    picks = rnd.sample(MISSION_TEMPLATES, 3)
    out = []
    for key, tpl, mn, mx, step, rmn, rmx in picks:
        steps = (mx - mn) // step if step else 0
        target = mn + (rnd.randint(0, steps) * step if steps > 0 else 0)
        reward = rnd.randint(rmn, rmx)
        reward = int(round(reward / 10.0)) * 10
        out.append({'id': key, 'key': key, 'text': tpl % target,
                    'target': target, 'reward': reward})
    return out


def _daily_state(upg, user_id):
    """Asegura el estado diario para hoy. Devuelve (state_dict, missions_meta)."""
    day = _today_str()
    ds = _loads(upg.get('daily_state'), None) or {}
    if ds.get('d') != day:
        ds = {'d': day, 'c': {'blocks': 0, 'rares': 0, 'treasures': 0,
                              'gem': 0, 'level': 0}, 'claimed': []}
    missions = _gen_missions(str(user_id), day)
    return ds, missions


def _missions_view(ds, missions):
    c = ds.get('c', {})
    claimed = ds.get('claimed', [])
    out = []
    for m in missions:
        prog = int(c.get(m['key'], 0))
        out.append({
            'id': m['id'], 'text': m['text'], 'target': m['target'],
            'reward': m['reward'], 'prog': min(prog, m['target']),
            'done': prog >= m['target'], 'claimed': m['id'] in claimed,
        })
    return out


# ════════════════════════════════════════════════════════════════
#  LOGROS
# ════════════════════════════════════════════════════════════════

def _life_stats(upg):
    return {
        'total_minerals': int(upg.get('total_minerals', 0)),
        'deepest':        int(upg.get('deepest_level', 0)),
        'gem_total':      float(upg.get('gem_total_earned', 0)),
        'diamonds':       int(upg.get('diamonds_total', 0)),
        'treasures':      int(upg.get('treasures_total', 0)),
        'best_combo':     int(upg.get('best_combo', 0)),
        'prestige':       int(upg.get('prestige', 0)),
    }


def _ach_view(upg):
    stats = _life_stats(upg)
    claimed = _loads(upg.get('claimed_ach'), []) or []
    out = []
    for aid, label, emoji, reward, desc, cond in ACHIEVEMENTS:
        done = bool(cond(stats))
        out.append({'id': aid, 'label': label, 'emoji': emoji, 'reward': reward,
                    'desc': desc, 'done': done, 'claimed': aid in claimed})
    return out


# ════════════════════════════════════════════════════════════════
#  GENERACIÓN DE MAPA (determinista + venas + especiales)
# ════════════════════════════════════════════════════════════════

def _weights(luck_level):
    bonus = luck_level * 0.025
    rock_w = max(0.05, MINERALS[0][4] - bonus)
    removed = MINERALS[0][4] - rock_w
    rare_sum = sum(MINERALS[i][4] for i in range(2, len(MINERALS)))
    w = [rock_w, MINERALS[1][4]]
    for i in range(2, len(MINERALS)):
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


def _gen_map(seed, level, luck_level):
    rnd = random.Random("%s:%d" % (seed, level))
    extra = _extra_hp(level)
    weights = _weights(luck_level)
    cells = []
    for _ in range(GRID):
        idx = _pick(rnd, weights)
        mh = MINERALS[idx][2] + extra
        cells.append({'t': idx, 'hp': mh, 'mh': mh, 'b': 0, 'h': 0, 's': SP_NONE})

    # Venas: un mineral valioso "contagia" vecinos de roca/tierra
    for i in range(GRID):
        t = cells[i]['t']
        if t >= 3:
            x, y = i % COLS, i // COLS
            for nx, ny in _neighbors(x, y):
                ni = ny * COLS + nx
                if cells[ni]['t'] <= 1 and cells[ni]['s'] == SP_NONE and rnd.random() < 0.55:
                    mh = MINERALS[t][2] + extra
                    cells[ni] = {'t': t, 'hp': mh, 'mh': mh, 'b': 0, 'h': 0, 's': SP_NONE}

    # Especiales (un solo paso, prioridad cofre > bomba > roca madre)
    bedrock_p = min(0.09, 0.025 + level * 0.0025)
    for i in range(GRID):
        c = cells[i]
        if c['s'] != SP_NONE:
            continue
        r = rnd.random()
        if r < 0.012:                                   # 🎁 cofre (oculto)
            c['s'] = SP_TREASURE
            c['t'] = 0
            c['mh'] = c['hp'] = 4 + extra
        elif r < 0.012 + 0.018:                         # 💥 bomba (oculta)
            c['s'] = SP_BOMB
            c['t'] = 0
            c['mh'] = c['hp'] = 2 + extra
        elif c['t'] <= 1 and rnd.random() < bedrock_p:  # ☠️ roca madre (visible)
            c['s'] = SP_BEDROCK
            c['t'] = 0
            c['mh'] = c['hp'] = 16 + int(level * 1.2)

    return {'cells': cells, 'cleared': 0, 'cf': 0}


# ════════════════════════════════════════════════════════════════
#  SERIALIZACIÓN SEGURA (nunca filtra bloques sin romper)
# ════════════════════════════════════════════════════════════════

def _client_cells(map_state):
    out = []
    for i, c in enumerate(map_state['cells']):
        cell = {'i': i, 'b': c['b'], 'h': c['h']}
        # Roca madre es visible aún sin romper (obstáculo), no revela botín.
        if not c['b'] and c.get('s') == SP_BEDROCK:
            cell['s'] = SP_BEDROCK
        if c['b']:
            s = c.get('s', SP_NONE)
            cell['s'] = s
            if s == SP_TREASURE:
                cell['e'] = '🎁'
            elif s == SP_BOMB:
                cell['e'] = '💥'
            elif s == SP_BEDROCK:
                cell['e'] = ''
            else:
                t = c['t']
                cell['e'] = MINERALS[t][1] if t >= 1 else ''
                cell['g'] = MINERALS[t][3]
        out.append(cell)
    return out


# ════════════════════════════════════════════════════════════════
#  ESTADO PÚBLICO
# ════════════════════════════════════════════════════════════════

def _public_state(user_id, sess, upg, now=None):
    now = now if now is not None else int(time.time())
    inv = _loads(sess.get('inventory'), []) if sess else []
    ms = _loads(sess.get('map_state'), {'cells': [], 'cleared': 0, 'cf': 0}) if sess else None
    cf = (ms or {}).get('cf', 0)

    energy_level = int(upg.get('upgrade_energy', 0))
    miner_level = int(upg.get('miner_level', 1) or 1)
    prestige = int(upg.get('prestige', 0))
    emax = _energy_max(energy_level, miner_level)
    energy, _eu = _live_energy(upg.get('energy', emax), upg.get('energy_updated', 0),
                               emax, _energy_regen_sec(), now)
    dmg_level = int(upg.get('upgrade_damage', 0))
    combo = int(sess['combo_count']) if sess else 0
    if sess and cf and now > cf:
        combo = 0
    nxt, cur_m, nxt_m = _combo_next(combo)
    xp = int(upg.get('xp', 0))
    xp_need = _xp_needed(miner_level)

    return {
        'enabled':       get_config('mine_enabled', '1') == '1',
        'level':         int(sess['level']) if sess else 0,
        'max_level':     MAX_LEVEL,
        'pickaxe_hp':    int(sess['pickaxe_hp']) if sess else PICKAXE_MAX,
        'pickaxe_max':   PICKAXE_MAX,
        'pick_tier':     _pick_tier(dmg_level),
        'dynamite':      int(sess['dynamite_count']) if sess else 0,
        'dynamite_max':  MAX_DYNAMITE,
        'combo_count':   combo,
        'combo_until':   cf,
        'combo_mult':    cur_m,
        'combo_next':    nxt,
        'combo_next_mult': nxt_m,
        'energy':        energy,
        'energy_max':    emax,
        'energy_regen':  _energy_regen_sec(),
        'inv_count':     len(inv),
        'inv_max':       _bag_slots(upg.get('upgrade_bag', 0)),
        'gem_balance':   float(upg.get('gem_balance', 0)),
        'gem_total':     float(upg.get('gem_total_earned', 0)),
        'xp':            xp,
        'xp_needed':     xp_need,
        'miner_level':   miner_level,
        'prestige':      prestige,
        'prestige_mult': round(_prestige_mult(prestige), 2),
        'prestige_req':  _prestige_req(prestige),
        'up_speed':      int(upg.get('upgrade_speed', 0)),
        'up_damage':     dmg_level,
        'up_luck':       int(upg.get('upgrade_luck', 0)),
        'up_bag':        int(upg.get('upgrade_bag', 0)),
        'up_crit':       int(upg.get('upgrade_crit', 0)),
        'up_energy':     energy_level,
        'crit_chance':   int(upg.get('upgrade_crit', 0)) * 6,
        'deepest':       int(upg.get('deepest_level', 0)),
        'total_runs':    int(upg.get('total_runs', 0)),
        'total_minerals': int(upg.get('total_minerals', 0)),
        'diamonds':      int(upg.get('diamonds_total', 0)),
        'treasures':     int(upg.get('treasures_total', 0)),
        'best_combo':    int(upg.get('best_combo', 0)),
        'has_session':   sess is not None and sess['status'] == 'active',
    }


def _upgrades_row(cur, user_id):
    cur.execute("SELECT * FROM mine_upgrades WHERE user_id=%s FOR UPDATE", (str(user_id),))
    row = cur.fetchone()
    if not row:
        cur.execute("INSERT INTO mine_upgrades (user_id, energy, energy_updated) VALUES (%s,%s,%s)",
                    (str(user_id), ENERGY_BASE, int(time.time())))
        cur.execute("SELECT * FROM mine_upgrades WHERE user_id=%s FOR UPDATE", (str(user_id),))
        row = cur.fetchone()
    return row


def _ensure_upgrades(user_id):
    row = execute_query("SELECT * FROM mine_upgrades WHERE user_id=%s", (str(user_id),), fetch_one=True)
    if not row:
        execute_query("INSERT IGNORE INTO mine_upgrades (user_id, energy, energy_updated) VALUES (%s,%s,%s)",
                      (str(user_id), ENERGY_BASE, int(time.time())))
        row = execute_query("SELECT * FROM mine_upgrades WHERE user_id=%s", (str(user_id),), fetch_one=True)
    return row or {}


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
    upgrades = {k: {'max': v['max'], 'costs': v['costs'], 'name': v['name'],
                    'icon': v['icon'], 'desc': v['desc']} for k, v in UPGRADES.items()}
    ds, missions = _daily_state(upg, user['user_id'])
    return render_template(
        'mine.html',
        user=user,
        enabled=_enabled(),
        state=_public_state(user['user_id'], sess, upg),
        minerals=minerals,
        upgrades=upgrades,
        upgrade_order=UPGRADE_KEYS,
        pick_tiers=[{'thr': t[0], 'name': t[1], 'emoji': t[2], 'color': t[3]} for t in PICK_TIERS],
        missions=_missions_view(ds, missions),
        achievements=_ach_view(upg),
        repair_cost=int(float(get_config('mine_pickaxe_repair_cost', '50'))),
        dynamite_cost=int(float(get_config('mine_dynamite_cost', '300'))),
        dynamite_energy=DYNAMITE_ENERGY,
        gem_rate=float(get_config('mine_gem_to_ton_rate', '0.0001')),
        daily_limit=float(get_config('mine_daily_convert_limit', '500')),
        format_ton=lambda a: "%.4f" % float(a or 0),
    )


# ════════════════════════════════════════════════════════════════
#  HELPERS DE ESCRITURA (XP / nivel / energía / misiones)
# ════════════════════════════════════════════════════════════════

def _apply_xp(upg, gain):
    """Suma XP y sube de nivel. Muta upg (xp, miner_level, energy, energy_updated).
    Devuelve (levels_subidos, gem_bonus)."""
    xp = int(upg.get('xp', 0)) + int(gain)
    lvl = int(upg.get('miner_level', 1) or 1)
    levels = 0
    bonus = 0
    while xp >= _xp_needed(lvl):
        xp -= _xp_needed(lvl)
        lvl += 1
        levels += 1
        bonus += 40 + lvl * 10
    upg['xp'] = xp
    upg['miner_level'] = lvl
    if levels > 0:
        # recarga energía al máximo al subir de nivel
        emax = _energy_max(int(upg.get('upgrade_energy', 0)), lvl)
        upg['energy'] = emax
        upg['energy_updated'] = int(time.time())
    return levels, bonus


# ════════════════════════════════════════════════════════════════
#  API: START
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


# ════════════════════════════════════════════════════════════════
#  API: TAP  (corazón del juego)
# ════════════════════════════════════════════════════════════════

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
    now = int(time.time())

    with _tx() as (conn, cur):
        upg = _upgrades_row(cur, uid)
        cur.execute(
            "SELECT * FROM mine_sessions WHERE user_id=%s AND status='active' "
            "ORDER BY id DESC LIMIT 1 FOR UPDATE", (uid,)
        )
        sess = cur.fetchone()
        if not sess:
            return jsonify({'success': False, 'error': 'no_session'})

        # ── Energía ──
        energy_level = int(upg.get('upgrade_energy', 0))
        miner_level = int(upg.get('miner_level', 1) or 1)
        emax = _energy_max(energy_level, miner_level)
        energy, eu = _live_energy(upg.get('energy', emax), upg.get('energy_updated', 0),
                                  emax, _energy_regen_sec(), now)
        if energy < 1:
            upg['energy'] = energy; upg['energy_updated'] = eu
            cur.execute("UPDATE mine_upgrades SET energy=%s, energy_updated=%s WHERE user_id=%s",
                        (energy, eu, uid))
            return jsonify({'success': False, 'error': 'no_energy',
                            'state': _public_state(uid, sess, upg, now)})

        ms = _loads(sess['map_state'], None)
        inv = _loads(sess['inventory'], [])
        if not ms or idx >= len(ms['cells']):
            return jsonify({'success': False, 'error': 'state'})
        cell = ms['cells'][idx]

        res = {'success': True, 'x': x, 'y': y, 'broke': False, 'full': False,
               'crit': False, 'pickaxe_broken': False, 'level_cleared': False,
               'mineral': None, 'special': None, 'treasure_gem': 0,
               'levelups': 0, 'level_bonus': 0, 'events': []}

        if cell['b']:
            res.update({'broke': True, 'cells': _client_cells(ms),
                        'state': _public_state(uid, sess, upg, now)})
            return jsonify(res)

        # consumir energía
        energy -= 1
        eu = now if eu == 0 else eu

        # ── Daño + crítico ──
        base_dmg = 1 + int(upg.get('upgrade_damage', 0))
        crit_chance = int(upg.get('upgrade_crit', 0)) * 6
        is_crit = crit_chance > 0 and (random.random() * 100 < crit_chance)
        dmg = base_dmg * (4 if is_crit else 1)
        res['crit'] = is_crit

        cell['h'] += 1
        cell['hp'] -= dmg
        broke = cell['hp'] <= 0

        bag = _bag_slots(upg.get('upgrade_bag', 0))
        combo = int(sess['combo_count'])
        cf = ms.get('cf', 0)
        if cf and now > cf:
            combo = 0; cf = 0
        pick = int(sess['pickaxe_hp'])

        # acumuladores para escribir una sola vez
        d_minerals = 0
        d_diamonds = 0
        d_treasures = 0
        treasure_gem = 0.0
        xp_gain = 1
        bump = {'blocks': 0, 'rares': 0, 'treasures': 0, 'level': 0}

        if broke:
            sp = cell.get('s', SP_NONE)

            # mochila llena bloquea solo minerales normales
            if sp == SP_NONE:
                t = cell['t']
                is_mineral = t >= 1
                if is_mineral and len(inv) >= bag:
                    cell['hp'] = 1
                    res.update({'full': True, 'cells': _client_cells(ms),
                                'state': _public_state(uid, sess, upg, now)})
                    cur.execute("UPDATE mine_sessions SET map_state=%s, last_action=NOW() WHERE id=%s",
                                (json.dumps(ms), sess['id']))
                    cur.execute("UPDATE mine_upgrades SET energy=%s, energy_updated=%s WHERE user_id=%s",
                                (energy, eu, uid))
                    upg['energy'] = energy; upg['energy_updated'] = eu
                    res['state'] = _public_state(uid, sess, upg, now)
                    return jsonify(res)

            cell['b'] = 1
            ms['cleared'] = ms.get('cleared', 0) + 1
            bump['blocks'] += 1

            if sp == SP_TREASURE:
                tmin = float(get_config('mine_treasure_min', '250'))
                tmax = float(get_config('mine_treasure_max', '1400'))
                base_t = random.uniform(tmin, tmax)
                gain = base_t * (1 + (int(sess['level']) - 1) * 0.1) * _prestige_mult(int(upg.get('prestige', 0)))
                treasure_gem = round(gain, 2)
                d_treasures += 1
                bump['treasures'] += 1
                xp_gain += 25
                pick -= 1
                res['special'] = 'treasure'
                res['treasure_gem'] = treasure_gem
                res['events'].append({'t': 'treasure', 'gem': treasure_gem})
                # combo: el cofre cuenta como gran golpe
                combo += 1
                cf = now + COMBO_WINDOW

            elif sp == SP_BOMB:
                res['special'] = 'bomb'
                pick -= 6
                # explosión 3x3: limpia escombro alrededor (sin minerales)
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        nx, ny = x + dx, y + dy
                        if not (0 <= nx < COLS and 0 <= ny < ROWS):
                            continue
                        nc = ms['cells'][ny * COLS + nx]
                        if not nc['b']:
                            nc['b'] = 1; nc['hp'] = 0; nc['h'] = nc['mh']
                            ms['cleared'] = ms.get('cleared', 0) + 1
                            bump['blocks'] += 1
                combo = 0; cf = 0
                res['events'].append({'t': 'bomb'})

            elif sp == SP_BEDROCK:
                res['special'] = 'bedrock'
                pick -= 1
                combo = 0; cf = 0   # romper roca madre corta el combo

            else:
                t = cell['t']
                is_mineral = t >= 1
                if is_mineral:
                    if t >= COMBO_MIN_IDX:
                        combo += 1
                        cf = now + COMBO_WINDOW
                    cmult = _combo_mult(combo)
                    item_m = round(_level_mult(int(sess['level'])) * cmult, 4)
                    inv.append({'k': t, 'm': item_m})
                    d_minerals += 1
                    xp_gain += MINERALS[t][3] // 5 + 1
                    if t >= RARE_FIND_IDX:
                        bump['rares'] += 1
                    if t == DIAMOND_IDX:
                        d_diamonds += 1
                    res['mineral'] = {'key': MINERALS[t][0], 'emoji': MINERALS[t][1],
                                      'gem': MINERALS[t][3], 'mult': cmult,
                                      'combo': combo}
                pick -= 2 if t == 0 else 1

            res['broke'] = True
            ms['cf'] = cf

            # mejor combo histórico
            best_combo = max(int(upg.get('best_combo', 0)), combo)

            # ── pico roto -> game over ──
            if pick <= 0:
                pick = 0
                cur.execute(
                    "UPDATE mine_sessions SET status='abandoned', pickaxe_hp=0, "
                    "inventory='[]', map_state=%s, combo_count=0, last_action=NOW() "
                    "WHERE id=%s", (json.dumps(ms), sess['id'])
                )
                # persistir progreso de upgrades (energía/xp/contadores/misiones)
                _apply_xp(upg, xp_gain)
                _write_upg_progress(cur, uid, upg, energy, eu, d_minerals, d_diamonds,
                                    d_treasures, best_combo, treasure_gem, bump, sess)
                sess['status'] = 'abandoned'; sess['pickaxe_hp'] = 0
                sess['inventory'] = '[]'; sess['combo_count'] = 0
                res['pickaxe_broken'] = True
                res['cells'] = _client_cells(ms)
                cur.execute("SELECT * FROM mine_upgrades WHERE user_id=%s", (uid,))
                upg2 = cur.fetchone()
                res['state'] = _public_state(uid, sess, upg2, now)
                return jsonify(res)

            # ── nivel completado -> baja un nivel ──
            if ms['cleared'] >= GRID and int(sess['level']) < MAX_LEVEL:
                new_level = int(sess['level']) + 1
                new_ms = _gen_map(sess['map_seed'], new_level, int(upg.get('upgrade_luck', 0)))
                xp_gain += 20
                bump['level'] = new_level
                cur.execute(
                    "UPDATE mine_sessions SET level=%s, map_state=%s, combo_count=0, "
                    "pickaxe_hp=%s, inventory=%s, last_action=NOW() WHERE id=%s",
                    (new_level, json.dumps(new_ms), pick, json.dumps(inv), sess['id'])
                )
                cur.execute(
                    "UPDATE mine_upgrades SET deepest_level=GREATEST(deepest_level,%s) WHERE user_id=%s",
                    (new_level, uid)
                )
                levels, lbonus = _apply_xp(upg, xp_gain)
                res['levelups'] = levels; res['level_bonus'] = lbonus
                if lbonus:
                    upg['gem_balance'] = float(upg.get('gem_balance', 0)) + lbonus
                    upg['gem_total_earned'] = float(upg.get('gem_total_earned', 0)) + lbonus
                _write_upg_progress(cur, uid, upg, energy, eu, d_minerals, d_diamonds,
                                    d_treasures, best_combo, treasure_gem, bump, sess,
                                    deepest=new_level)
                sess['level'] = new_level; sess['map_state'] = json.dumps(new_ms)
                sess['combo_count'] = 0; sess['pickaxe_hp'] = pick
                sess['inventory'] = json.dumps(inv)
                res['level_cleared'] = True
                res['cells'] = _client_cells(new_ms)
                cur.execute("SELECT * FROM mine_upgrades WHERE user_id=%s", (uid,))
                upg2 = cur.fetchone()
                res['state'] = _public_state(uid, sess, upg2, now)
                return jsonify(res)

        # ── persistencia normal ──
        levels, lbonus = _apply_xp(upg, xp_gain)
        res['levelups'] = levels; res['level_bonus'] = lbonus
        if lbonus:
            upg['gem_balance'] = float(upg.get('gem_balance', 0)) + lbonus
            upg['gem_total_earned'] = float(upg.get('gem_total_earned', 0)) + lbonus
        best_combo = max(int(upg.get('best_combo', 0)), combo)
        cur.execute(
            "UPDATE mine_sessions SET map_state=%s, inventory=%s, pickaxe_hp=%s, "
            "combo_count=%s, last_action=NOW() WHERE id=%s",
            (json.dumps(ms), json.dumps(inv), pick, combo, sess['id'])
        )
        _write_upg_progress(cur, uid, upg, energy, eu, d_minerals, d_diamonds,
                            d_treasures, best_combo, treasure_gem, bump, sess)
        sess['map_state'] = json.dumps(ms); sess['inventory'] = json.dumps(inv)
        sess['pickaxe_hp'] = pick; sess['combo_count'] = combo
        res['cells'] = _client_cells(ms)
        cur.execute("SELECT * FROM mine_upgrades WHERE user_id=%s", (uid,))
        upg2 = cur.fetchone()
        res['state'] = _public_state(uid, sess, upg2, now)

    return jsonify(res)


def _write_upg_progress(cur, uid, upg, energy, eu, d_min, d_dia, d_tre,
                        best_combo, treasure_gem, bump, sess, deepest=None):
    """Escribe en una sola sentencia el progreso de mine_upgrades + misiones."""
    ds, missions = _daily_state(upg, uid)
    c = ds['c']
    c['blocks'] = c.get('blocks', 0) + bump.get('blocks', 0)
    c['rares'] = c.get('rares', 0) + bump.get('rares', 0)
    c['treasures'] = c.get('treasures', 0) + bump.get('treasures', 0)
    if bump.get('level', 0):
        c['level'] = max(c.get('level', 0), bump['level'])
    cur.execute(
        "UPDATE mine_upgrades SET energy=%s, energy_updated=%s, xp=%s, miner_level=%s, "
        "gem_balance=%s, gem_total_earned=%s, total_minerals=total_minerals+%s, "
        "diamonds_total=diamonds_total+%s, treasures_total=treasures_total+%s, "
        "best_combo=GREATEST(best_combo,%s), daily_state=%s "
        + ("" if deepest is None else ", deepest_level=GREATEST(deepest_level,%d)" % int(deepest)) +
        " WHERE user_id=%s",
        (energy, eu, int(upg.get('xp', 0)), int(upg.get('miner_level', 1)),
         float(upg.get('gem_balance', 0)) + float(treasure_gem),
         float(upg.get('gem_total_earned', 0)) + float(treasure_gem),
         d_min, d_dia, d_tre, best_combo, json.dumps(ds), uid)
    )


# ════════════════════════════════════════════════════════════════
#  API: DINAMITA
# ════════════════════════════════════════════════════════════════

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
    now = int(time.time())

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

        emax = _energy_max(int(upg.get('upgrade_energy', 0)), int(upg.get('miner_level', 1)))
        energy, eu = _live_energy(upg.get('energy', emax), upg.get('energy_updated', 0),
                                  emax, _energy_regen_sec(), now)
        if energy < DYNAMITE_ENERGY:
            return jsonify({'success': False, 'error': 'no_energy',
                            'state': _public_state(uid, sess, upg, now)})
        energy -= DYNAMITE_ENERGY
        eu = now if eu == 0 else eu

        ms = _loads(sess['map_state'], None)
        inv = _loads(sess['inventory'], [])
        if not ms:
            return jsonify({'success': False, 'error': 'state'})
        bag = _bag_slots(upg.get('upgrade_bag', 0))
        combo = int(sess['combo_count'])
        cf = ms.get('cf', 0)
        if cf and now > cf:
            combo = 0; cf = 0
        cmult = _combo_mult(combo)
        gained = []
        d_min = d_dia = d_tre = 0
        treasure_gem = 0.0
        bump = {'blocks': 0, 'rares': 0, 'treasures': 0, 'level': 0}

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
                bump['blocks'] += 1
                sp = c.get('s', SP_NONE)
                if sp == SP_TREASURE:
                    tmin = float(get_config('mine_treasure_min', '250'))
                    tmax = float(get_config('mine_treasure_max', '1400'))
                    gain = random.uniform(tmin, tmax) * (1 + (int(sess['level']) - 1) * 0.1) \
                        * _prestige_mult(int(upg.get('prestige', 0)))
                    treasure_gem += round(gain, 2)
                    d_tre += 1; bump['treasures'] += 1
                    gained.append('🎁')
                elif sp in (SP_BOMB, SP_BEDROCK):
                    gained.append('💥' if sp == SP_BOMB else '⬛')
                else:
                    t = c['t']
                    if t >= 1 and len(inv) < bag:
                        item_m = round(_level_mult(int(sess['level'])) * cmult, 4)
                        inv.append({'k': t, 'm': item_m})
                        d_min += 1
                        if t >= RARE_FIND_IDX:
                            bump['rares'] += 1
                        if t == DIAMOND_IDX:
                            d_dia += 1
                        gained.append(MINERALS[t][1])

        cur.execute(
            "UPDATE mine_sessions SET map_state=%s, inventory=%s, dynamite_count=dynamite_count-1, "
            "last_action=NOW() WHERE id=%s", (json.dumps(ms), json.dumps(inv), sess['id'])
        )
        _write_upg_progress(cur, uid, upg, energy, eu, d_min, d_dia, d_tre,
                            max(int(upg.get('best_combo', 0)), combo), treasure_gem, bump, sess)
        cur.execute("SELECT * FROM mine_sessions WHERE id=%s", (sess['id'],))
        sess = cur.fetchone()
        cur.execute("SELECT * FROM mine_upgrades WHERE user_id=%s", (uid,))
        upg = cur.fetchone()
        st = _public_state(uid, sess, upg, now)

    return jsonify({'success': True, 'gained': gained, 'treasure_gem': round(treasure_gem, 2),
                    'cells': _client_cells(ms), 'state': st})


# ════════════════════════════════════════════════════════════════
#  API: VENDER
# ════════════════════════════════════════════════════════════════

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
            return jsonify({'success': True, 'sold': 0, 'gem_gained': 0,
                            'state': _public_state(uid, sess, upg)})

        prestige_mult = _prestige_mult(int(upg.get('prestige', 0)))
        miner_mult = _miner_mult(int(upg.get('miner_level', 1)))
        cur_level = int(sess['level'])
        total = 0.0
        for it in inv:
            k = int(it.get('k', 0))
            base = MINERALS[k][3]
            # compat: ítems viejos guardaban x2 (bool); nuevos guardan m (mult)
            if 'm' in it:
                m = float(it['m'])
            else:
                m = _level_mult(cur_level) * (2.0 if it.get('x2') else 1.0)
            total += base * m
        total = round(total * prestige_mult * miner_mult, 2)
        count = len(inv)

        cur.execute(
            "UPDATE mine_upgrades SET gem_balance=gem_balance+%s, "
            "gem_total_earned=gem_total_earned+%s WHERE user_id=%s",
            (total, total, uid)
        )
        cur.execute("UPDATE mine_sessions SET inventory='[]', last_action=NOW() WHERE id=%s",
                    (sess['id'],))
        # misión "gem"
        ds, _m = _daily_state(upg, uid)
        ds['c']['gem'] = ds['c'].get('gem', 0) + int(total)
        cur.execute("UPDATE mine_upgrades SET daily_state=%s WHERE user_id=%s",
                    (json.dumps(ds), uid))
        sess['inventory'] = '[]'
        cur.execute("SELECT * FROM mine_upgrades WHERE user_id=%s", (uid,))
        upg = cur.fetchone()
        st = _public_state(uid, sess, upg)

    return jsonify({'success': True, 'sold': count, 'gem_gained': total, 'state': st})


# ════════════════════════════════════════════════════════════════
#  API: UPGRADE
# ════════════════════════════════════════════════════════════════

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
        query = (
            "UPDATE mine_upgrades SET gem_balance=gem_balance-%s, "
            + col + "=" + col + "+1 WHERE user_id=%s AND gem_balance>=%s"
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

    return jsonify({'success': True, 'new_level': cur_level + 1,
                    'next_cost': (spec['costs'][cur_level + 1] if cur_level + 1 < spec['max'] else None),
                    'state': st})


# ════════════════════════════════════════════════════════════════
#  API: REPARAR / COMPRAR DINAMITA
# ════════════════════════════════════════════════════════════════

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
        cur.execute("UPDATE mine_upgrades SET gem_balance=gem_balance-%s "
                    "WHERE user_id=%s AND gem_balance>=%s", (cost, uid, cost))
        if cur.rowcount == 0:
            return jsonify({'success': False, 'error': 'insufficient'})
        cur.execute("UPDATE mine_sessions SET pickaxe_hp=%s WHERE id=%s", (PICKAXE_MAX, sess['id']))
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
        cur.execute("UPDATE mine_upgrades SET gem_balance=gem_balance-%s "
                    "WHERE user_id=%s AND gem_balance>=%s", (cost, uid, cost))
        if cur.rowcount == 0:
            return jsonify({'success': False, 'error': 'insufficient'})
        cur.execute("UPDATE mine_sessions SET dynamite_count=dynamite_count+1 WHERE id=%s", (sess['id'],))
        cur.execute("SELECT * FROM mine_sessions WHERE id=%s", (sess['id'],))
        sess = cur.fetchone()
        cur.execute("SELECT * FROM mine_upgrades WHERE user_id=%s", (uid,))
        upg = cur.fetchone()
        st = _public_state(uid, sess, upg)
    return jsonify({'success': True, 'state': st})


# ════════════════════════════════════════════════════════════════
#  API: PRESTIGIO / RENACIMIENTO
# ════════════════════════════════════════════════════════════════

@crystal_rush_bp.route('/api/mine/prestige', methods=['POST'])
@_require_user
def api_prestige(user):
    uid = str(user['user_id'])
    with _tx() as (conn, cur):
        upg = _upgrades_row(cur, uid)
        prestige = int(upg.get('prestige', 0))
        req = _prestige_req(prestige)
        if int(upg.get('deepest_level', 0)) < req:
            return jsonify({'success': False, 'error': 'req_not_met', 'req': req})
        bonus = 1000 * (prestige + 1)
        # cierra sesión activa
        cur.execute("UPDATE mine_sessions SET status='abandoned' "
                    "WHERE user_id=%s AND status='active'", (uid,))
        # reset de upgrades y profundidad; conserva GEM, TON, logros, totales de vida
        cur.execute(
            "UPDATE mine_upgrades SET upgrade_speed=0, upgrade_damage=0, upgrade_luck=0, "
            "upgrade_bag=0, upgrade_crit=0, upgrade_energy=0, deepest_level=0, "
            "prestige=prestige+1, gem_balance=gem_balance+%s, gem_total_earned=gem_total_earned+%s, "
            "energy=%s, energy_updated=%s WHERE user_id=%s",
            (bonus, bonus, _energy_max(0, int(upg.get('miner_level', 1))), int(time.time()), uid)
        )
        cur.execute("SELECT * FROM mine_upgrades WHERE user_id=%s", (uid,))
        upg = cur.fetchone()
        st = _public_state(uid, None, upg)
    return jsonify({'success': True, 'new_prestige': prestige + 1, 'bonus': bonus, 'state': st})


# ════════════════════════════════════════════════════════════════
#  API: RECLAMAR MISIÓN / LOGRO
# ════════════════════════════════════════════════════════════════

@crystal_rush_bp.route('/api/mine/claim-mission', methods=['POST'])
@_require_user
def api_claim_mission(user):
    uid = str(user['user_id'])
    data = request.get_json(silent=True) or {}
    mid = data.get('id')
    with _tx() as (conn, cur):
        upg = _upgrades_row(cur, uid)
        ds, missions = _daily_state(upg, uid)
        meta = next((m for m in missions if m['id'] == mid), None)
        if not meta:
            return jsonify({'success': False, 'error': 'bad_mission'})
        prog = int(ds['c'].get(meta['key'], 0))
        if prog < meta['target']:
            return jsonify({'success': False, 'error': 'not_done'})
        if mid in ds.get('claimed', []):
            return jsonify({'success': False, 'error': 'claimed'})
        ds.setdefault('claimed', []).append(mid)
        reward = int(meta['reward'])
        cur.execute(
            "UPDATE mine_upgrades SET gem_balance=gem_balance+%s, "
            "gem_total_earned=gem_total_earned+%s, daily_state=%s WHERE user_id=%s",
            (reward, reward, json.dumps(ds), uid)
        )
        cur.execute("SELECT * FROM mine_upgrades WHERE user_id=%s", (uid,))
        upg = cur.fetchone()
        sess = execute_query(
            "SELECT * FROM mine_sessions WHERE user_id=%s AND status='active' "
            "ORDER BY id DESC LIMIT 1", (uid,), fetch_one=True
        )
        st = _public_state(uid, sess, upg)
        view = _missions_view(ds, missions)
    return jsonify({'success': True, 'reward': reward, 'missions': view, 'state': st})


@crystal_rush_bp.route('/api/mine/claim-ach', methods=['POST'])
@_require_user
def api_claim_ach(user):
    uid = str(user['user_id'])
    data = request.get_json(silent=True) or {}
    aid = data.get('id')
    adef = next((a for a in ACHIEVEMENTS if a[0] == aid), None)
    if not adef:
        return jsonify({'success': False, 'error': 'bad_ach'})
    with _tx() as (conn, cur):
        upg = _upgrades_row(cur, uid)
        stats = _life_stats(upg)
        if not adef[5](stats):
            return jsonify({'success': False, 'error': 'not_done'})
        claimed = _loads(upg.get('claimed_ach'), []) or []
        if aid in claimed:
            return jsonify({'success': False, 'error': 'claimed'})
        claimed.append(aid)
        reward = int(adef[3])
        cur.execute(
            "UPDATE mine_upgrades SET gem_balance=gem_balance+%s, "
            "gem_total_earned=gem_total_earned+%s, claimed_ach=%s WHERE user_id=%s",
            (reward, reward, json.dumps(claimed), uid)
        )
        cur.execute("SELECT * FROM mine_upgrades WHERE user_id=%s", (uid,))
        upg = cur.fetchone()
        sess = execute_query(
            "SELECT * FROM mine_sessions WHERE user_id=%s AND status='active' "
            "ORDER BY id DESC LIMIT 1", (uid,), fetch_one=True
        )
        st = _public_state(uid, sess, upg)
        view = _ach_view(upg)
    return jsonify({'success': True, 'reward': reward, 'achievements': view, 'state': st})


# ════════════════════════════════════════════════════════════════
#  API: STATS / LEADERBOARD
# ════════════════════════════════════════════════════════════════

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
    ds, missions = _daily_state(upg, uid)
    st = _public_state(uid, sess, upg)
    st['today_converted'] = float((today or {}).get('s', 0) or 0)
    st['daily_limit'] = float(get_config('mine_daily_convert_limit', '500'))
    return jsonify({'success': True, 'state': st,
                    'missions': _missions_view(ds, missions),
                    'achievements': _ach_view(upg)})


@crystal_rush_bp.route('/api/mine/leaderboard')
@_require_user
def api_leaderboard(user):
    uid = str(user['user_id'])
    rich = execute_query(
        "SELECT u.user_id, u.gem_total_earned, u.deepest_level, u.prestige, "
        "x.first_name, x.username FROM mine_upgrades u "
        "LEFT JOIN users x ON x.user_id=u.user_id "
        "ORDER BY u.gem_total_earned DESC LIMIT 20", fetch_all=True
    ) or []
    deep = execute_query(
        "SELECT u.user_id, u.deepest_level, u.prestige, x.first_name, x.username "
        "FROM mine_upgrades u LEFT JOIN users x ON x.user_id=u.user_id "
        "ORDER BY u.deepest_level DESC, u.gem_total_earned DESC LIMIT 20", fetch_all=True
    ) or []

    def _fmt(rows, val_key):
        out = []
        for i, r in enumerate(rows):
            out.append({
                'rank': i + 1,
                'name': (r.get('first_name') or 'Anónimo'),
                'me': str(r.get('user_id')) == uid,
                'prestige': int(r.get('prestige', 0) or 0),
                'value': float(r.get(val_key, 0) or 0),
            })
        return out

    return jsonify({'success': True,
                    'rich': _fmt(rich, 'gem_total_earned'),
                    'deep': _fmt(deep, 'deepest_level')})


# ════════════════════════════════════════════════════════════════
#  API: CONVERSIÓN GEM -> TON
# ════════════════════════════════════════════════════════════════

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

        cur.execute("UPDATE mine_upgrades SET gem_balance=gem_balance-%s "
                    "WHERE user_id=%s AND gem_balance>=%s", (amount, uid, amount))
        if cur.rowcount == 0:
            return jsonify({'success': False, 'error': 'insufficient'})

        cur.execute("SELECT doge_balance FROM users WHERE user_id=%s FOR UPDATE", (uid,))
        urow = cur.fetchone()
        before = Decimal(str(urow['doge_balance'] or 0))
        after = before + Decimal(str(ton))
        cur.execute("UPDATE users SET doge_balance=%s, total_earned=total_earned+%s WHERE user_id=%s",
                    (float(after), float(ton), uid))
        try:
            cur.execute(
                "INSERT INTO balance_history (user_id, action, amount, balance_before, "
                "balance_after, description) VALUES (%s,'mine_convert',%s,%s,%s,%s)",
                (uid, float(ton), float(before), float(after),
                 'Crystal Rush: %s GEM -> %s TON' % (amount, ton))
            )
        except Exception:
            pass
        cur.execute("INSERT INTO mine_conversions (user_id, gem_amount, ton_amount, rate) "
                    "VALUES (%s,%s,%s,%s)", (uid, amount, ton, rate))
        cur.execute("SELECT * FROM mine_upgrades WHERE user_id=%s", (uid,))
        upg = cur.fetchone()
        sess = execute_query(
            "SELECT * FROM mine_sessions WHERE user_id=%s AND status='active' "
            "ORDER BY id DESC LIMIT 1", (uid,), fetch_one=True
        )
        st = _public_state(uid, sess, upg)

    return jsonify({'success': True, 'ton': ton, 'gem_spent': amount, 'state': st})


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
        "COALESCE(SUM(total_runs),0) AS runs, COALESCE(MAX(deepest_level),0) AS deepest, "
        "COALESCE(MAX(prestige),0) AS max_prestige FROM mine_upgrades", fetch_one=True
    ) or {}
    conv = execute_query(
        "SELECT COUNT(*) AS n, COALESCE(SUM(gem_amount),0) AS gem, "
        "COALESCE(SUM(ton_amount),0) AS ton FROM mine_conversions", fetch_one=True
    ) or {}
    top = execute_query(
        "SELECT u.user_id, u.gem_balance, u.gem_total_earned, u.deepest_level, "
        "u.total_minerals, u.prestige, u.miner_level, x.first_name, x.username "
        "FROM mine_upgrades u LEFT JOIN users x ON x.user_id=u.user_id "
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
        'mine_energy_regen_sec': get_config('mine_energy_regen_sec', '18'),
        'mine_treasure_min': get_config('mine_treasure_min', '250'),
        'mine_treasure_max': get_config('mine_treasure_max', '1400'),
        'mine_prestige_req': get_config('mine_prestige_req', '15'),
    }
    return render_template(
        'admin_mine.html', active_page='mine',
        stats=stats, conv=conv, top=top, recent=recent, cfg=cfg
    )


@crystal_rush_bp.route('/admin/mine/config', methods=['POST'])
@_require_admin
def admin_mine_config():
    fields = ['mine_gem_to_ton_rate', 'mine_daily_convert_limit',
              'mine_pickaxe_repair_cost', 'mine_dynamite_cost',
              'mine_energy_regen_sec', 'mine_treasure_min',
              'mine_treasure_max', 'mine_prestige_req']
    for f in fields:
        v = request.form.get(f)
        if v is not None and v != '':
            set_config(f, v)
    set_config('mine_enabled', '1' if request.form.get('mine_enabled') == 'on' else '0')
    return redirect(url_for('crystal_rush.admin_mine'))
