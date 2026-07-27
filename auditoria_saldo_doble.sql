-- ============================================================
-- AUDITORIA: detectar pagos duplicados de mineria
-- Ejecutar ANTES de desplegar el parche para medir el dano.
-- ============================================================

-- 1) DOBLE TAP: dos claims identicos al mismo usuario en < 60s.
--    Es la firma exacta del bug de claim_mining_rewards.
SELECT a.user_id, a.amount, a.created_at AS primero, b.created_at AS duplicado,
       TIMESTAMPDIFF(SECOND, a.created_at, b.created_at) AS segundos
FROM balance_history a
JOIN balance_history b
  ON  a.user_id = b.user_id
  AND a.action  = 'mining_reward'
  AND b.action  = 'mining_reward'
  AND a.id      < b.id
  AND a.amount  = b.amount
  AND a.amount  > 0
  AND b.created_at <= a.created_at + INTERVAL 60 SECOND
ORDER BY b.created_at DESC;


-- 2) CARRERA claim vs settler: liquidacion y claim del mismo importe
--    con pocos minutos de diferencia.
SELECT s.user_id, s.amount, s.created_at AS liquidacion, c.created_at AS claim,
       TIMESTAMPDIFF(SECOND, s.created_at, c.created_at) AS segundos
FROM balance_history s
JOIN balance_history c
  ON  s.user_id = c.user_id
  AND s.action  = 'mining_expiry_settlement'
  AND c.action  = 'mining_reward'
  AND ABS(s.amount - c.amount) < 0.0000001
  AND ABS(TIMESTAMPDIFF(SECOND, s.created_at, c.created_at)) <= 600
ORDER BY s.created_at DESC;


-- 3) Maquinas incoherentes: liquidadas pero con last_claim_at ANTERIOR
--    a expires_at -> el claim piso al settler (sintoma directo del bug).
SELECT id, user_id, plan_name, last_claim_at, expires_at, total_mined
FROM user_mining_machines
WHERE settled = 1 AND last_claim_at < expires_at
ORDER BY expires_at DESC;


-- 4) Maquinas que pagaron MAS de lo que el plan permite.
--    total_mined no deberia superar hourly_rate * duracion_del_plan.
SELECT id, user_id, plan_name, hourly_rate, purchased_at, expires_at, total_mined,
       ROUND(hourly_rate * TIMESTAMPDIFF(SECOND, purchased_at, expires_at)/3600, 8) AS maximo_teorico,
       ROUND(total_mined - hourly_rate * TIMESTAMPDIFF(SECOND, purchased_at, expires_at)/3600, 8) AS exceso
FROM user_mining_machines
WHERE total_mined > hourly_rate * TIMESTAMPDIFF(SECOND, purchased_at, expires_at)/3600 * 1.001
ORDER BY exceso DESC;


-- 5) DESCUADRE por update_balance no atomico:
--    saldo actual vs saldo reconstruido desde el historial.
SELECT u.user_id, u.doge_balance AS saldo_actual,
       ROUND(COALESCE(SUM(h.amount), 0), 8) AS saldo_segun_historial,
       ROUND(u.doge_balance - COALESCE(SUM(h.amount), 0), 8) AS diferencia
FROM users u
LEFT JOIN balance_history h ON h.user_id = u.user_id
GROUP BY u.user_id, u.doge_balance
HAVING ABS(diferencia) > 0.00000001
ORDER BY ABS(diferencia) DESC
LIMIT 100;
