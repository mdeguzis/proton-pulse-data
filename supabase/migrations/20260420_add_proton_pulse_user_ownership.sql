alter table public.user_configs
  add column if not exists proton_pulse_user_id uuid,
  add column if not exists installation_id text;

create index if not exists user_configs_proton_pulse_user_id_idx
  on public.user_configs (proton_pulse_user_id);

create index if not exists user_configs_installation_id_idx
  on public.user_configs (installation_id);

create table if not exists public.plugin_links (
  installation_id text primary key,
  installation_secret_hash text,
  link_code text unique,
  link_code_expires_at timestamptz,
  linked_user_id uuid,
  linked_at timestamptz,
  last_seen_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

alter table public.plugin_links
  add column if not exists installation_secret_hash text;

create index if not exists plugin_links_linked_user_id_idx
  on public.plugin_links (linked_user_id);

alter table public.user_systems
  add column if not exists proton_pulse_user_id uuid,
  add column if not exists installation_id text;

create index if not exists user_systems_proton_pulse_user_id_idx
  on public.user_systems (proton_pulse_user_id);

create index if not exists user_systems_installation_id_idx
  on public.user_systems (installation_id);

create unique index if not exists user_systems_proton_pulse_user_device_uidx
  on public.user_systems (proton_pulse_user_id, device_id)
  where proton_pulse_user_id is not null;
