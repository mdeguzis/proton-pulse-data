-- Edit history for user_configs. Snapshots old values before each UPDATE.
-- Global 50 MB cap: oldest rows are pruned when the table exceeds the limit.

create table if not exists public.user_configs_history (
  id            bigint generated always as identity primary key,
  config_id     bigint not null references public.user_configs(id) on delete cascade,
  app_id        bigint,
  rating        text,
  proton_version text,
  os            text,
  notes         text,
  config_key    text,
  recorded_at   timestamptz not null default now()
);

create index if not exists user_configs_history_config_id_idx
  on public.user_configs_history (config_id, recorded_at desc);

alter table public.user_configs_history enable row level security;

-- Users can only read history for their own reports
do $$ begin
  if not exists (
    select 1 from pg_policies
    where tablename = 'user_configs_history' and policyname = 'owner read history'
  ) then
    create policy "owner read history"
      on public.user_configs_history for select
      using (
        exists (
          select 1 from public.user_configs uc
          where uc.id = user_configs_history.config_id
            and uc.proton_pulse_user_id = auth.uid()
        )
      );
  end if;
end $$;

-- Trigger: snapshot old row before update, then prune if table > 50 MB
create or replace function public.snapshot_user_configs_before_update()
returns trigger language plpgsql as $$
declare
  table_size_mb float;
begin
  insert into public.user_configs_history
    (config_id, app_id, rating, proton_version, os, notes, config_key, recorded_at)
  values
    (old.id, old.app_id, old.rating, old.proton_version, old.os, old.notes, old.config_key, now());

  -- Prune oldest rows when table exceeds 50 MB
  select pg_total_relation_size('public.user_configs_history') / 1048576.0 into table_size_mb;
  if table_size_mb > 50 then
    delete from public.user_configs_history
    where id in (
      select id from public.user_configs_history
      order by recorded_at asc
      limit 200
    );
  end if;

  return new;
end;
$$;

drop trigger if exists user_configs_history_trigger on public.user_configs;
create trigger user_configs_history_trigger
  before update on public.user_configs
  for each row execute function public.snapshot_user_configs_before_update();
