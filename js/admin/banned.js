import { SUPABASE_URL } from './config.js';
import { supabaseHeaders, escapeHtml, fmtDate } from './utils.js';

export async function fetchBannedUsers(session, { search } = {}) {
  const url = `${SUPABASE_URL}/rest/v1/banned_users?select=id,proton_pulse_user_id,client_id,steam_username,banned_reason,banned_at&order=banned_at.desc`;
  const res = await fetch(url, { headers: supabaseHeaders(session) });
  if (!res.ok) throw new Error(`Fetch banned failed: ${res.status}`);
  let rows = await res.json();
  if (search) {
    const q = search.toLowerCase();
    rows = rows.filter(r => (r.steam_username || '').toLowerCase().includes(q));
  }
  return rows;
}

export function renderBanned(rows) {
  const loading = document.getElementById('banned-loading');
  const empty   = document.getElementById('banned-empty');
  const table   = document.getElementById('banned-table');
  const tbody   = document.getElementById('banned-tbody');

  loading.hidden = true;

  if (!rows.length) {
    empty.hidden = false;
    table.hidden = true;
    return;
  }

  empty.hidden = true;
  table.hidden = false;

  tbody.innerHTML = rows.map(r => {
    const name = escapeHtml(r.steam_username || r.client_id?.slice(0, 8) || 'unknown');
    const reason = escapeHtml(r.banned_reason || '—');
    const bannedAt = escapeHtml(fmtDate(r.banned_at));
    const banId = escapeHtml(String(r.id));
    const userId = escapeHtml(r.proton_pulse_user_id || '');
    const clientId = escapeHtml(r.client_id || '');

    return `<tr data-ban-id="${banId}">
      <td>${name}</td>
      <td>${reason}</td>
      <td>${bannedAt}</td>
      <td>
        <button class="admin-btn admin-btn--sm admin-btn--ok" data-action="unban" data-ban-id="${banId}" data-user-id="${userId}" data-client-id="${clientId}">Unban</button>
      </td>
    </tr>`;
  }).join('');
}

export async function banUser(session, { protonPulseUserId, clientId, steamUsername, reason }) {
  // Insert ban record.
  const banUrl = `${SUPABASE_URL}/rest/v1/banned_users`;
  const banRes = await fetch(banUrl, {
    method: 'POST',
    headers: supabaseHeaders(session, { Prefer: 'return=minimal' }),
    body: JSON.stringify({
      proton_pulse_user_id: protonPulseUserId || null,
      client_id: clientId || null,
      steam_username: steamUsername || null,
      banned_reason: reason || null,
      banned_by: session.user.id,
    }),
  });
  if (!banRes.ok) throw new Error(`Ban insert failed: ${banRes.status}`);

  // Hide all their reports.
  const filters = [];
  if (protonPulseUserId) filters.push(`proton_pulse_user_id=eq.${encodeURIComponent(protonPulseUserId)}`);
  else if (clientId) filters.push(`client_id=eq.${encodeURIComponent(clientId)}`);
  if (!filters.length) return;

  const hideUrl = `${SUPABASE_URL}/rest/v1/user_configs?${filters.join('&')}`;
  const hideRes = await fetch(hideUrl, {
    method: 'PATCH',
    headers: supabaseHeaders(session, { Prefer: 'return=minimal' }),
    body: JSON.stringify({ is_hidden: true, is_flagged: true, flagged_reason: 'admin:banned' }),
  });
  if (!hideRes.ok) throw new Error(`Hide reports failed: ${hideRes.status}`);
}

export async function unbanUser(session, banId, { protonPulseUserId, clientId } = {}) {
  const url = `${SUPABASE_URL}/rest/v1/banned_users?id=eq.${banId}`;
  const res = await fetch(url, {
    method: 'DELETE',
    headers: supabaseHeaders(session, { Prefer: 'return=minimal' }),
  });
  if (!res.ok) throw new Error(`Unban failed: ${res.status}`);

  // Restore reports that were hidden solely due to the ban.
  const filters = [];
  if (protonPulseUserId) filters.push(`proton_pulse_user_id=eq.${encodeURIComponent(protonPulseUserId)}`);
  else if (clientId) filters.push(`client_id=eq.${encodeURIComponent(clientId)}`);
  if (!filters.length) return;

  const restoreUrl = `${SUPABASE_URL}/rest/v1/user_configs?${filters.join('&')}&flagged_reason=eq.admin%3Abanned`;
  const restoreRes = await fetch(restoreUrl, {
    method: 'PATCH',
    headers: supabaseHeaders(session, { Prefer: 'return=minimal' }),
    body: JSON.stringify({ is_hidden: false, is_flagged: false, flagged_reason: null, flagged_at: null }),
  });
  if (!restoreRes.ok) throw new Error(`Restore reports failed: ${restoreRes.status}`);
}
