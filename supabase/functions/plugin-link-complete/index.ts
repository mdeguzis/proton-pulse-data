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

    const { linkCode } = await req.json();
    if (!linkCode || typeof linkCode !== "string") {
      return Response.json({ error: "linkCode is required" }, { status: 400, headers: corsHeaders });
    }

    const { data: row, error: readError } = await supabase
      .from("plugin_links")
      .select("installation_id, link_code_expires_at")
      .eq("link_code", linkCode.toUpperCase())
      .maybeSingle();
    if (readError) throw readError;
    if (!row) {
      return Response.json({ error: "Invalid link code" }, { status: 404, headers: corsHeaders });
    }
    if (!row.link_code_expires_at || new Date(row.link_code_expires_at).getTime() <= Date.now()) {
      return Response.json({ error: "Link code expired" }, { status: 410, headers: corsHeaders });
    }

    const now = new Date().toISOString();
    const { error: updateError } = await supabase
      .from("plugin_links")
      .update({
        linked_user_id: user.id,
        linked_at: now,
        last_seen_at: now,
        link_code: null,
        link_code_expires_at: null,
      })
      .eq("installation_id", row.installation_id);
    if (updateError) throw updateError;

    return Response.json({
      installationId: row.installation_id,
      linkedUserId: user.id,
      linkedAt: now,
    }, { headers: corsHeaders });
  } catch (error) {
    return Response.json({
      error: error instanceof Error ? error.message : String(error),
    }, { status: 500, headers: corsHeaders });
  }
});
