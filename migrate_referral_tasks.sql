-- ============================================================
-- Migración: Tareas de bono de referido
-- Cuando un referido compra un plan, aparece una tarea
-- en el centro de tareas con recompensa = precio_plan / 5
-- ============================================================

-- No se requieren cambios de schema: las tareas usan la tabla
-- tasks existente con task_id formato: ref_bonus_{referrer_id}_{referred_id}
-- y task_type = 'special', max_completions = 1

-- Verificar que la columna max_completions existe (ya estaba en schema original):
-- ALTER TABLE tasks ADD COLUMN IF NOT EXISTS max_completions INT DEFAULT NULL;

SELECT 'Migración de tareas de referido aplicada correctamente.' AS status;
