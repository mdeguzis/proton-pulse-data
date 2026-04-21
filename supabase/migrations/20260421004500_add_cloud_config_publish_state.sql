alter table public.user_proton_configs
  add column if not exists is_published boolean not null default false;

create index if not exists user_proton_configs_published_idx
  on public.user_proton_configs (is_published, updated_at desc);
