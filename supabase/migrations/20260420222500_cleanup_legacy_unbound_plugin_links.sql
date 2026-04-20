delete from public.plugin_links
where installation_secret_hash is null
  and linked_user_id is null;
