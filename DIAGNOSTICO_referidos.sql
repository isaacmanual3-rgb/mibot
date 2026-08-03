-- ─────────────────────────────────────────────────────────────
-- 1) CUANTOS REFERIDOS SE PERDIERON
-- Usuarios que SI tienen invitador (users.referred_by) pero que
-- NUNCA se registraron en la tabla `referrals`. Ese es el bug.
-- SOLO LECTURA: no cambia nada.
-- ─────────────────────────────────────────────────────────────
SELECT COUNT(*) AS referidos_perdidos
FROM users u
WHERE u.referred_by IS NOT NULL
  AND u.referred_by <> ''
  AND NOT EXISTS (
        SELECT 1 FROM referrals r
        WHERE r.referrer_id = u.referred_by
          AND r.referred_id = u.user_id
  );

-- 2) QUIENES SON (los 50 mas recientes, para revisarlos a mano)
SELECT u.user_id      AS referido,
       u.username     AS referido_username,
       u.referred_by  AS invitador,
       u.created_at
FROM users u
WHERE u.referred_by IS NOT NULL
  AND u.referred_by <> ''
  AND NOT EXISTS (
        SELECT 1 FROM referrals r
        WHERE r.referrer_id = u.referred_by
          AND r.referred_id = u.user_id
  )
ORDER BY u.created_at DESC
LIMIT 50;

-- 3) A QUE INVITADORES LES FALTAN MAS (para avisarles si quieres)
SELECT u.referred_by AS invitador,
       COUNT(*)      AS referidos_que_le_faltan
FROM users u
WHERE u.referred_by IS NOT NULL
  AND u.referred_by <> ''
  AND NOT EXISTS (
        SELECT 1 FROM referrals r
        WHERE r.referrer_id = u.referred_by
          AND r.referred_id = u.user_id
  )
GROUP BY u.referred_by
ORDER BY referidos_que_le_faltan DESC
LIMIT 30;
