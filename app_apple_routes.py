"""
══════════════════════════════════════════════════════════
 APPLE FARM — Flask routes to ADD to your existing app.py
══════════════════════════════════════════════════════════

INSTRUCCIONES:
1. Copia estas rutas e imports en tu app.py existente.
2. Ejecuta apple_farm_schema.sql en tu base de datos MySQL.
3. Copia el webp de tavukaltlik a static/img/tavukaltlik.webp
"""

# ── Imports a añadir (si no existen ya) ─────────────────
from datetime import datetime, timedelta
import math

# ════════════════════════════════════════════
#  HELPERS internos
# ════════════════════════════════════════════

def _get_db():
    """Wrapper to get a DB connection using your existing pool."""
    from database import get_connection  # usa tu función existente
    return get_connection()


def _apple_trees_config():
    """
    Definición estática de árboles.
    También se pueden guardar en DB; aquí las tenemos hardcoded para simplicidad.
    """
    return [
        {
            "id": 1, "name": "Manzano Silvestre", "emoji": "🌱",
            "level_required": 1, "cost": 0,
            "apples_per_hour": 10, "description": "Tu primer árbol. ¡Gratis!"
        },
        {
            "id": 2, "name": "Manzano Dorado", "emoji": "🌳",
            "level_required": 1, "cost": 100,
            "apples_per_hour": 30, "description": "Produce manzanas doradas"
        },
        {
            "id": 3, "name": "Manzano Rojo Fuji", "emoji": "🍎",
            "level_required": 3, "cost": 500,
            "apples_per_hour": 80, "description": "Variedades selectas"
        },
        {
            "id": 4, "name": "Manzano Gigante", "emoji": "🌲",
            "level_required": 5, "cost": 2000,
            "apples_per_hour": 250, "description": "El más productivo"
        },
        {
            "id": 5, "name": "Manzano Legendario", "emoji": "✨",
            "level_required": 10, "cost": 10000,
            "apples_per_hour": 1500, "description": "Solo para los más grandes"
        },
    ]


def _calc_level(apples_total: int) -> int:
    """Nivel basado en manzanas acumuladas históricamente."""
    thresholds = [0, 50, 200, 500, 1500, 5000, 15000, 50000, 150000, 500000]
    for i, t in enumerate(reversed(thresholds)):
        if apples_total >= t:
            return len(thresholds) - i
    return 1


def _calc_offline_production(user_id: int) -> float:
    """
    Calcula manzanas producidas offline desde last_claim.
    Retorna la cantidad a añadir.
    """
    conn = _get_db()
    cur  = conn.cursor(dictionary=True)

    # Obtener last_claim y árboles comprados
    cur.execute("SELECT last_claim FROM apple_users WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    if not row or not row['last_claim']:
        cur.close(); conn.close()
        return 0.0

    last_claim = row['last_claim']
    if isinstance(last_claim, str):
        last_claim = datetime.fromisoformat(last_claim)

    elapsed_seconds = (datetime.utcnow() - last_claim).total_seconds()
    # Cap offline en 8 horas
    elapsed_seconds = min(elapsed_seconds, 8 * 3600)

    # Manzanas por hora total
    cur.execute("""
        SELECT SUM(t.apples_per_hour * ut.quantity) as total_ph
        FROM apple_user_trees ut
        JOIN apple_trees t ON t.id = ut.tree_id
        WHERE ut.user_id = %s
    """, (user_id,))
    row2 = cur.fetchone()
    cur.close(); conn.close()

    total_per_hour = float(row2['total_ph'] or 0)
    produced = total_per_hour * (elapsed_seconds / 3600)
    return produced


def _get_apples_per_hour(user_id: int) -> float:
    conn = _get_db()
    cur  = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT COALESCE(SUM(t.apples_per_hour * ut.quantity), 0) as total
        FROM apple_user_trees ut
        JOIN apple_trees t ON t.id = ut.tree_id
        WHERE ut.user_id = %s
    """, (user_id,))
    row = cur.fetchone()
    cur.close(); conn.close()
    return float(row['total'] if row else 0)


def _get_user_trees_map(user_id: int) -> dict:
    """Retorna {tree_id: quantity}"""
    conn = _get_db()
    cur  = conn.cursor(dictionary=True)
    cur.execute("SELECT tree_id, quantity FROM apple_user_trees WHERE user_id = %s", (user_id,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return {r['tree_id']: r['quantity'] for r in rows}


def _ensure_apple_user(user_id: int):
    """Crea registro en apple_users si no existe. Da árbol 1 gratis."""
    conn = _get_db()
    cur  = conn.cursor(dictionary=True)
    cur.execute("SELECT user_id FROM apple_users WHERE user_id = %s", (user_id,))
    existing = cur.fetchone()
    if not existing:
        cur.execute("""
            INSERT INTO apple_users (user_id, apples, level, last_claim, total_earned)
            VALUES (%s, 0, 1, %s, 0)
        """, (user_id, datetime.utcnow()))
        # Dar árbol 1 gratis
        cur.execute("""
            INSERT INTO apple_user_trees (user_id, tree_id, quantity)
            VALUES (%s, 1, 1)
        """, (user_id,))
        conn.commit()
    cur.close(); conn.close()


# ════════════════════════════════════════════
#  RUTA PRINCIPAL (reemplaza la existente)
# ════════════════════════════════════════════

@app.route('/')
def index():
    """Apple Farm — página principal"""
    user_id = get_user_id()

    ref = request.args.get('ref') or request.args.get('start') or request.args.get('referral')
    if ref:
        session['pending_ref'] = str(ref)

    if not user_id:
        return render_template('telegram_required.html')

    user = ensure_user(user_id)
    if user.get('banned'):
        return render_template('banned.html', reason=user.get('ban_reason'))

    record_user_ip(user_id, get_client_ip())
    _ensure_apple_user(user_id)

    # Añadir campo apples/level al user dict para el template
    conn = _get_db()
    cur  = conn.cursor(dictionary=True)
    cur.execute("SELECT apples, level FROM apple_users WHERE user_id = %s", (user_id,))
    apple_row = cur.fetchone()
    cur.close(); conn.close()

    if apple_row:
        user['apples'] = int(apple_row['apples'])
        user['level']  = int(apple_row['level'])

    return render_template('index.html',
        user=user,
        format_doge=format_doge
    )


# ════════════════════════════════════════════
#  API: /api/update_apples
# ════════════════════════════════════════════

@app.route('/api/update_apples', methods=['POST'])
@require_user
def api_update_apples(user):
    user_id = user['user_id']
    _ensure_apple_user(user_id)

    # Calcular producción offline
    produced = _calc_offline_production(user_id)

    conn = _get_db()
    cur  = conn.cursor(dictionary=True)

    if produced > 0:
        cur.execute("""
            UPDATE apple_users
            SET apples       = apples + %s,
                total_earned = total_earned + %s,
                last_claim   = %s
            WHERE user_id = %s
        """, (produced, produced, datetime.utcnow(), user_id))
        conn.commit()

    cur.execute("SELECT apples, level FROM apple_users WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    cur.close(); conn.close()

    current_apples = float(row['apples'])
    # Recalcular nivel
    new_level = _calc_level(int(current_apples))
    if new_level != row['level']:
        conn2 = _get_db()
        c2 = conn2.cursor()
        c2.execute("UPDATE apple_users SET level = %s WHERE user_id = %s", (new_level, user_id))
        conn2.commit()
        c2.close(); conn2.close()

    apples_per_hour = _get_apples_per_hour(user_id)
    user_trees = _get_user_trees_map(user_id)

    return jsonify({
        "success": True,
        "apples": int(current_apples),
        "level": new_level,
        "apples_per_hour": apples_per_hour,
        "trees": _apple_trees_config(),
        "user_trees": user_trees,
    })


# ════════════════════════════════════════════
#  API: /api/buy_tree
# ════════════════════════════════════════════

@app.route('/api/buy_tree', methods=['POST'])
@require_user
def api_buy_tree(user):
    user_id = user['user_id']
    data    = request.get_json(silent=True) or {}
    tree_id = int(data.get('tree_id', 0))

    # Buscar árbol en config
    tree_config = next((t for t in _apple_trees_config() if t['id'] == tree_id), None)
    if not tree_config:
        return jsonify({"success": False, "error": "Árbol no encontrado"}), 400

    _ensure_apple_user(user_id)

    conn = _get_db()
    cur  = conn.cursor(dictionary=True)

    cur.execute("SELECT apples, level FROM apple_users WHERE user_id = %s FOR UPDATE", (user_id,))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        return jsonify({"success": False, "error": "Usuario no encontrado"}), 404

    current_apples = float(row['apples'])
    current_level  = int(row['level'])

    # Verificar nivel
    if current_level < tree_config['level_required']:
        cur.close(); conn.close()
        return jsonify({"success": False, "error": f"Necesitas nivel {tree_config['level_required']}"}), 403

    # Árbol gratuito (id=1, costo 0) — solo comprable si aún no tiene ninguno
    cost = tree_config['cost']
    if cost > 0 and current_apples < cost:
        cur.close(); conn.close()
        return jsonify({"success": False, "error": "Manzanas insuficientes"}), 400

    # Descontar y comprar
    new_apples = current_apples - cost
    cur.execute("UPDATE apple_users SET apples = %s WHERE user_id = %s", (new_apples, user_id))

    # Insertar o incrementar en user_trees
    cur.execute("""
        INSERT INTO apple_user_trees (user_id, tree_id, quantity)
        VALUES (%s, %s, 1)
        ON DUPLICATE KEY UPDATE quantity = quantity + 1
    """, (user_id, tree_id))

    conn.commit()
    cur.close(); conn.close()

    apples_per_hour = _get_apples_per_hour(user_id)
    new_level = _calc_level(int(new_apples))

    return jsonify({
        "success": True,
        "apples": int(new_apples),
        "level": new_level,
        "apples_per_hour": apples_per_hour,
    })
