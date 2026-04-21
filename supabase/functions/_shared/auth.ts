import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

function requireEnv(name: string): string {
  const value = Deno.env.get(name);
  if (!value) throw new Error(`Missing required env: ${name}`);
  return value;
}

export function createServiceClient() {
  return createClient(
    requireEnv("SUPABASE_URL"),
    requireEnv("SUPABASE_SERVICE_ROLE_KEY"),
  );
}

export function createRequestAuthClient(req: Request) {
  const authHeader = req.headers.get("Authorization") ?? "";
  return createClient(
    requireEnv("SUPABASE_URL"),
    requireEnv("SUPABASE_ANON_KEY"),
    {
      global: {
        headers: {
          Authorization: authHeader,
          apikey: requireEnv("SUPABASE_ANON_KEY"),
        },
      },
    },
  );
}

export async function requireRequestUser(req: Request) {
  const authClient = createRequestAuthClient(req);
  const { data, error } = await authClient.auth.getUser();
  if (error || !data.user) {
    return { user: null, error: error?.message || "Authentication required" };
  }
  return { user: data.user, error: null };
}
