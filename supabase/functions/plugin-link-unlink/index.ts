import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

async function hashInstallationSecret(secret: string) {
  const bytes = new TextEncoder().encode(secret);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });

  const supabase = createClient(
    Deno.env.get("SUPABASE_URL")!,
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
  );

  try {
    const { installationId, installationSecret } = await req.json();
    if (!installationId || typeof installationId !== "string") {
      return Response.json({ error: "installationId is required" }, { status: 400, headers: corsHeaders });
    }
    if (!installationSecret || typeof installationSecret !== "string") {
      return Response.json({ error: "installationSecret is required" }, { status: 400, headers: corsHeaders });
    }

    const installationSecretHash = await hashInstallationSecret(installationSecret);
    const { data, error } = await supabase
      .from("plugin_links")
      .select("installation_id, installation_secret_hash")
      .eq("installation_id", installationId)
      .maybeSingle();
    if (error) throw error;
    if (!data) {
      return Response.json({ error: "Installation not found" }, { status: 404, headers: corsHeaders });
    }
    if (data.installation_secret_hash && data.installation_secret_hash !== installationSecretHash) {
      return Response.json({ error: "Installation proof mismatch" }, { status: 403, headers: corsHeaders });
    }

    const { error: updateError } = await supabase
      .from("plugin_links")
      .update({
        linked_user_id: null,
        linked_at: null,
        last_seen_at: new Date().toISOString(),
        link_code: null,
        link_code_expires_at: null,
        installation_secret_hash: data.installation_secret_hash ?? installationSecretHash,
      })
      .eq("installation_id", installationId);
    if (updateError) throw updateError;

    return Response.json({
      installationId,
      linked: false,
      linkedUserId: null,
      linkedAt: null,
      linkCode: null,
      linkCodeExpiresAt: null,
    }, { headers: corsHeaders });
  } catch (error) {
    return Response.json({
      error: error instanceof Error ? error.message : String(error),
    }, { status: 500, headers: corsHeaders });
  }
});
