CREATE OR REPLACE FUNCTION public.is_current_user_admin()
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public
AS $$ SELECT EXISTS (SELECT 1 FROM public.admins WHERE proton_pulse_user_id = auth.uid()); $$;

CREATE OR REPLACE FUNCTION public.is_current_user_super_admin()
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public
AS $$ SELECT EXISTS (SELECT 1 FROM public.admins WHERE proton_pulse_user_id = auth.uid() AND role = 'super_admin'); $$;

DROP POLICY IF EXISTS "admins read all admins" ON public.admins;
CREATE POLICY "admins read all admins" ON public.admins FOR SELECT
  USING (public.is_current_user_admin());

DROP POLICY IF EXISTS "super admins update admins" ON public.admins;
CREATE POLICY "super admins update admins" ON public.admins FOR UPDATE
  USING (public.is_current_user_super_admin());

DROP POLICY IF EXISTS "super admins delete admins" ON public.admins;
CREATE POLICY "super admins delete admins" ON public.admins FOR DELETE
  USING (proton_pulse_user_id <> auth.uid() AND public.is_current_user_super_admin());

DROP POLICY IF EXISTS "admins manage banned users" ON public.banned_users;
CREATE POLICY "admins manage banned users" ON public.banned_users FOR ALL
  USING (public.is_current_user_admin());

DROP POLICY IF EXISTS "admins_read_banned_phrases" ON public.banned_phrases;
CREATE POLICY "admins_read_banned_phrases" ON public.banned_phrases FOR ALL
  USING (public.is_current_user_admin());
