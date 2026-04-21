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

    const { installationId } = await req.json();
    if (!installationId || typeof installationId !== "string") {
      return Response.json({ error: "installationId is required" }, { status: 400, headers: corsHeaders });
    }

    const { error } = await supabase
      .from("plugin_links")
      .delete()
      .eq("installation_id", installationId)
      .eq("linked_user_id", user.id);
    if (error) throw error;

    return Response.json({ ok: true }, { headers: corsHeaders });
  } catch (error) {
    return Response.json({
      error: error instanceof Error ? error.message : String(error),
    }, { status: 500, headers: corsHeaders });
  }
});
