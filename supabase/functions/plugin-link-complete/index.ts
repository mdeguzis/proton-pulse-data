import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });

  const supabase = createClient(
    Deno.env.get("SUPABASE_URL")!,
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
  );

  try {
    const authHeader = req.headers.get("Authorization") ?? "";
    const token = authHeader.replace(/^Bearer\s+/i, "");
    const { data: authData, error: authError } = await supabase.auth.getUser(token);
    if (authError || !authData.user) {
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
        linked_user_id: authData.user.id,
        linked_at: now,
        last_seen_at: now,
        link_code: null,
        link_code_expires_at: null,
      })
      .eq("installation_id", row.installation_id);
    if (updateError) throw updateError;

    return Response.json({
      installationId: row.installation_id,
      linkedUserId: authData.user.id,
      linkedAt: now,
    }, { headers: corsHeaders });
  } catch (error) {
    return Response.json({
      error: error instanceof Error ? error.message : String(error),
    }, { status: 500, headers: corsHeaders });
  }
});
