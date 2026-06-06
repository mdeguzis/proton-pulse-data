-- Drop the broken "hide banned user configs" SELECT policy on user_configs.
-- It caused HTTP 500 for authenticated users due to a 3-level nested RLS
-- evaluation chain: user_configs -> banned_users -> admins -> admins (self-ref).
-- The policy was also ineffective: non-admins always saw through it because
-- banned_users returns no rows under RLS, making NOT(EXISTS) always true.
--
-- The correct approach: set is_hidden = true on user_configs rows when a user
-- is banned. The existing "public read non-hidden configs" policy already hides
-- is_hidden rows from non-owners, so no new policy is needed.

DROP POLICY IF EXISTS "hide banned user configs" ON public.user_configs;

-- Trigger: when a row is inserted into banned_users, hide all that user's
-- user_configs rows so they are removed from public view immediately.
CREATE OR REPLACE FUNCTION public.hide_configs_on_ban()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  UPDATE public.user_configs
  SET is_hidden = true
  WHERE
    (NEW.proton_pulse_user_id IS NOT NULL AND proton_pulse_user_id = NEW.proton_pulse_user_id)
    OR
    (NEW.client_id IS NOT NULL AND client_id = NEW.client_id);
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_hide_configs_on_ban ON public.banned_users;

CREATE TRIGGER trg_hide_configs_on_ban
  AFTER INSERT ON public.banned_users
  FOR EACH ROW EXECUTE FUNCTION public.hide_configs_on_ban();
