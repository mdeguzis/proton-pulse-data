-- Add updated_at to user_configs for report edit tracking
ALTER TABLE user_configs ADD COLUMN IF NOT EXISTS updated_at timestamptz;

CREATE OR REPLACE FUNCTION set_user_configs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS user_configs_updated_at_trigger ON user_configs;
CREATE TRIGGER user_configs_updated_at_trigger
  BEFORE UPDATE ON user_configs
  FOR EACH ROW EXECUTE FUNCTION set_user_configs_updated_at();
