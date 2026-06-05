-- Add role column to admins. super_admin can manage other admins; moderator can moderate content.
ALTER TABLE public.admins
  ADD COLUMN IF NOT EXISTS role text NOT NULL DEFAULT 'moderator'
  CHECK (role IN ('super_admin', 'moderator'));

-- Seed owner as super_admin.
UPDATE public.admins
  SET role = 'super_admin'
  WHERE proton_pulse_user_id = 'b66fa63b-e86e-4460-b595-1199c4330445';

-- Super admins can INSERT new admins.
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='public' AND tablename='admins' AND policyname='super admins insert admins') THEN
    CREATE POLICY "super admins insert admins" ON public.admins FOR INSERT TO authenticated
      WITH CHECK (EXISTS (SELECT 1 FROM public.admins WHERE proton_pulse_user_id = auth.uid() AND role = 'super_admin'));
  END IF;
END $$;

-- Super admins can UPDATE any admin row (e.g. change role).
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='public' AND tablename='admins' AND policyname='super admins update admins') THEN
    CREATE POLICY "super admins update admins" ON public.admins FOR UPDATE TO authenticated
      USING (EXISTS (SELECT 1 FROM public.admins WHERE proton_pulse_user_id = auth.uid() AND role = 'super_admin'));
  END IF;
END $$;

-- Super admins can DELETE any admin row (cannot delete themselves).
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='public' AND tablename='admins' AND policyname='super admins delete admins') THEN
    CREATE POLICY "super admins delete admins" ON public.admins FOR DELETE TO authenticated
      USING (
        proton_pulse_user_id <> auth.uid()
        AND EXISTS (SELECT 1 FROM public.admins WHERE proton_pulse_user_id = auth.uid() AND role = 'super_admin')
      );
  END IF;
END $$;

-- Allow all admins to read all admin rows (not just own row) for the roster view.
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='public' AND tablename='admins' AND policyname='admins read all admins') THEN
    CREATE POLICY "admins read all admins" ON public.admins FOR SELECT TO authenticated
      USING (EXISTS (SELECT 1 FROM public.admins WHERE proton_pulse_user_id = auth.uid()));
  END IF;
END $$;
