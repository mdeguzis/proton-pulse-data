alter table public.user_proton_configs
  add column if not exists proton_pulse_user_id uuid,
  add column if not exists installation_id text;

create index if not exists user_proton_configs_proton_pulse_user_id_idx
  on public.user_proton_configs (proton_pulse_user_id);

create index if not exists user_proton_configs_installation_id_idx
  on public.user_proton_configs (installation_id);
