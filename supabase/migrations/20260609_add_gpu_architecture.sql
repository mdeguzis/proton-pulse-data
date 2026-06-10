-- Add gpu_architecture to user_configs.
-- Nullable text; populated by the submit form via client-side detection.
-- Existing rows left NULL so old reports are grouped as "unknown" by the UI.
ALTER TABLE public.user_configs
  ADD COLUMN IF NOT EXISTS gpu_architecture text DEFAULT NULL;
