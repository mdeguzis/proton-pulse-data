import { createServiceClient, requireRequestUser } from "../_shared/auth.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });

  const supabase = createServiceClient();

  try {
    const { user, error: authError } = await requireRequestUser(req);
    if (authError || !user) {
      return Response.json({ error: "Authentication required" }, { status: 401, headers: corsHeaders });
    }

    const { data, error } = await supabase
      .from("plugin_links")
      .select("installation_id, linked_at, last_seen_at")
      .eq("linked_user_id", user.id)
      .order("linked_at", { ascending: false });
    if (error) throw error;

    return Response.json((data ?? []).map((row) => ({
      installationId: row.installation_id,
      linkedAt: row.linked_at,
      lastSeenAt: row.last_seen_at,
    })), { headers: corsHeaders });
  } catch (error) {
    return Response.json({
      error: error instanceof Error ? error.message : String(error),
    }, { status: 500, headers: corsHeaders });
  }
});
