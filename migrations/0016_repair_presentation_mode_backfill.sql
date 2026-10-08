-- Repair migration for 0014 (review R5-006).
--
-- 0014 added presentation_mode as NOT NULL DEFAULT 'full_frame' and then tried
-- to backfill reveal for Mask-enabled projects with
-- `WHERE presentation_mode IS NULL OR presentation_mode = ''`. Under NOT NULL
-- DEFAULT that predicate never matches, so every pre-0014 row kept
-- 'full_frame' and old Mask-enabled projects lost their reveal presentation.
--
-- presentation_mode was introduced by 0014 in the same release as its only
-- writer, so no explicit user choice can exist in the affected window: rows
-- with mask_enabled = 1 AND presentation_mode = 'full_frame' are determinable
-- backfill victims and are repaired here. Rows with mask_enabled = 0 are
-- correct as full_frame and are left untouched. Idempotent by construction.
UPDATE projects
SET presentation_mode = 'reveal'
WHERE mask_enabled = 1 AND presentation_mode = 'full_frame';
