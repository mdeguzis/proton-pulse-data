alter table public.plugin_links
  add column if not exists installation_secret_hash text;
