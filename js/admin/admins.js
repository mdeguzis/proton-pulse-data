import { SUPABASE_URL } from './config.js';
import { supabaseHeaders, escapeHtml, fmtDate } from './utils.js';

export async function fetchAdmins(session) {
  const url = `${SUPABASE_URL}/rest/v1/admins?select=proton_pulse_user_id,steam_username,role,added_at&order=added_at.asc`;
  const res = await fetch(url, { headers: supabaseHeaders(session) });
  if (!res.ok) throw new Error(`Fetch admins failed: ${res.status}`);
  return res.json();
}

export async function addAdmin(session, { uuid, username, role }) {
  const res = await fetch(`${SUPABASE_URL}/rest/v1/admins`, {
    method: 'POST',
    headers: supabaseHeaders(session, { Prefer: 'return=minimal' }),
    body: JSON.stringify({ proton_pulse_user_id: uuid, steam_username: username, role }),
  });
  if (!res.ok) throw new Error(`Add admin failed: ${res.status} ${await res.text()}`);
}

export async function removeAdmin(session, uuid) {
  const res = await fetch(`${SUPABASE_URL}/rest/v1/admins?proton_pulse_user_id=eq.${uuid}`, {
    method: 'DELETE',
    headers: supabaseHeaders(session, { Prefer: 'return=minimal' }),
  });
  if (!res.ok) throw new Error(`Remove admin failed: ${res.status}`);
}

export async function updateAdminRole(session, uuid, role) {
  const res = await fetch(`${SUPABASE_URL}/rest/v1/admins?proton_pulse_user_id=eq.${uuid}`, {
    method: 'PATCH',
    headers: supabaseHeaders(session, { Prefer: 'return=minimal' }),
    body: JSON.stringify({ role }),
  });
  if (!res.ok) throw new Error(`Update role failed: ${res.status}`);
}

export function renderAdmins(rows) {
  const loading = document.getElementById('admins-loading');
  const empty   = document.getElementById('admins-empty');
  const table   = document.getElementById('admins-table');
  const tbody   = document.getElementById('admins-tbody');

  loading.hidden = true;

  if (!rows.length) {
    empty.hidden = false;
    table.hidden = true;
    return;
  }

  empty.hidden = true;
  table.hidden = false;

  tbody.innerHTML = rows.map(r => {
    const uid = escapeHtml(r.proton_pulse_user_id);
    const name = escapeHtml(r.steam_username);
    const isSuperAdmin = r.role === 'super_admin';
    const roleSelect = `
      <select class="admin-select admin-select--sm" data-action="change-role" data-uuid="${uid}">
        <option value="moderator" ${r.role === 'moderator' ? 'selected' : ''}>Moderator</option>
        <option value="super_admin" ${isSuperAdmin ? 'selected' : ''}>Super Admin</option>
      </select>`;
    const removeBtn = `<button class="admin-btn admin-btn--danger admin-btn--sm" data-action="remove-admin" data-uuid="${uid}" data-name="${name}">Remove</button>`;
    return `<tr>
      <td>${name}</td>
      <td>${roleSelect}</td>
      <td>${escapeHtml(fmtDate(r.added_at))}</td>
      <td>${removeBtn}</td>
    </tr>`;
  }).join('');
}
