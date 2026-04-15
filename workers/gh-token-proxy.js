/**
 * workers/gh-token-proxy.js — Cloudflare Worker CORS proxy for GitHub OAuth token exchange
 *
 * Why this exists:
 *   GitHub's /login/oauth/access_token endpoint does not set CORS headers,
 *   so browsers can't call it directly. This tiny worker proxies the request
 *   server-side (where CORS doesn't apply) and adds the correct headers.
 *
 * Deployment:
 *   1. Install Wrangler: npm install -g wrangler
 *   2. wrangler login
 *   3. wrangler secret put GH_CLIENT_SECRET
 *      (paste your GitHub OAuth App Client Secret when prompted)
 *   4. Deploy:
 *      wrangler deploy --name pp-gh-auth workers/gh-token-proxy.js
 *   5. Copy the deployed worker URL (e.g. https://pp-gh-auth.YOUR_SUBDOMAIN.workers.dev)
 *      into TOKEN_PROXY in gh-auth.js
 *
 * Security:
 *   - Only POST requests are accepted.
 *   - The client secret is kept in a Cloudflare secret env var — never in source.
 *   - CORS is restricted to the GitHub Pages origin.
 *   - The worker only forwards calls to https://github.com/login/oauth/access_token.
 */

const ALLOWED_ORIGIN = 'https://mdeguzis.github.io';
const GH_TOKEN_URL   = 'https://github.com/login/oauth/access_token';

function corsHeaders(origin) {
  const allowed = origin === ALLOWED_ORIGIN ? origin : ALLOWED_ORIGIN;
  return {
    'Access-Control-Allow-Origin':  allowed,
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Accept',
    'Access-Control-Max-Age':       '86400',
  };
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get('Origin') || '';

    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: corsHeaders(origin) });
    }

    if (request.method !== 'POST') {
      return new Response('Method Not Allowed', { status: 405, headers: corsHeaders(origin) });
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return new Response(JSON.stringify({ error: 'invalid_request', error_description: 'Request body must be JSON' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) }
      });
    }

    // Forward to GitHub with the client secret added
    const ghRes = await fetch(GH_TOKEN_URL, {
      method: 'POST',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...body, client_secret: env.GH_CLIENT_SECRET })
    });

    const data = await ghRes.json();

    return new Response(JSON.stringify(data), {
      status: ghRes.status,
      headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) }
    });
  }
};
