-- ─────────────────────────────────────────────────────────────
-- RECUPERACION: reconstruye las filas de `referrals` perdidas.
--
-- ⚠ NO LO CORRAS hasta haber revisado DIAGNOSTICO_referidos.sql
-- ⚠ HAZ COPIA DE SEGURIDAD ANTES:
--     mysqldump -u aeroflex -p aeroflex referrals users > backup_ref.sql
--
-- Inserta los referidos como NO VALIDADOS (validated=0), que es lo
-- correcto: la validacion sigue exigiendo que compren un plan.
-- NO paga bonos retroactivos.
-- INSERT IGNORE + UNIQUE(referrer_id,referred_id) => no duplica.
-- ─────────────────────────────────────────────────────────────

INSERT IGNORE INTO referrals
    (referrer_id, referred_id, referred_username, referred_first_name,
     validated, bonus_paid, created_at)
SELECT u.referred_by,
       u.user_id,
       u.username,
       COALESCE(u.first_name, 'Player'),
       0,
       0,
       u.created_at
FROM users u
JOIN users ref ON ref.user_id = u.referred_by   -- el invitador debe existir
WHERE u.referred_by IS NOT NULL
  AND u.referred_by <> ''
  AND u.referred_by <> u.user_id                -- nadie se refiere a si mismo
  AND NOT EXISTS (
        SELECT 1 FROM referrals r
        WHERE r.referrer_id = u.referred_by
          AND r.referred_id = u.user_id
  );

-- Recalcular referral_count desde la tabla real (fuente de verdad)
UPDATE users u
SET u.referral_count = (
    SELECT COUNT(*) FROM referrals r WHERE r.referrer_id = u.user_id
);

-- Comprobacion final: debe dar 0
SELECT COUNT(*) AS deberia_ser_cero
FROM users u
WHERE u.referred_by IS NOT NULL AND u.referred_by <> ''
  AND NOT EXISTS (SELECT 1 FROM referrals r
                  WHERE r.referrer_id=u.referred_by AND r.referred_id=u.user_id);
