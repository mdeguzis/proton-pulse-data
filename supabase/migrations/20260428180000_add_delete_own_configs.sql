-- Allow authenticated users to delete their own cloud configs and reports.
-- user_proton_configs: owned by proton_pulse_user_id = auth.uid()
-- user_configs:        owned by proton_pulse_user_id = auth.uid()

grant delete on table public.user_proton_configs to authenticated;

do $$ begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename  = 'user_proton_configs'
      and policyname = 'owner delete cloud configs'
  ) then
    create policy "owner delete cloud configs"
      on public.user_proton_configs for delete
      to authenticated
      using (proton_pulse_user_id = auth.uid());
  end if;
end $$;

grant delete on table public.user_configs to authenticated;

do $$ begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename  = 'user_configs'
      and policyname = 'owner delete configs'
  ) then
    create policy "owner delete configs"
      on public.user_configs for delete
      to authenticated
      using (proton_pulse_user_id = auth.uid());
  end if;
end $$;
