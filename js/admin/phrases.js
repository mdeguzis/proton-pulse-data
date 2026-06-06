import { SUPABASE_URL } from './config.js';
import { supabaseHeaders, escapeHtml, fmtDate } from './utils.js';
import { loadWordlist, checkAgainstWordlist } from './wordlist.js';

export async function fetchBannedPhrases(session) {
  const url = `${SUPABASE_URL}/rest/v1/banned_phrases?select=*&order=created_at.desc`;
  const res = await fetch(url, { headers: supabaseHeaders(session) });
  if (!res.ok) throw new Error(`Fetch phrases failed: ${res.status}`);
  return res.json();
}

export async function addBannedPhrase(session, { pattern, is_regex, description }) {
  const res = await fetch(`${SUPABASE_URL}/rest/v1/banned_phrases`, {
    method: 'POST',
    headers: supabaseHeaders(session, { Prefer: 'return=minimal' }),
    body: JSON.stringify({ pattern, is_regex: !!is_regex, description: description || null, created_by: session.user.id }),
  });
  if (!res.ok) throw new Error(`Add phrase failed: ${res.status} ${await res.text()}`);
}

export async function removeBannedPhrase(session, id) {
  const res = await fetch(`${SUPABASE_URL}/rest/v1/banned_phrases?id=eq.${id}`, {
    method: 'DELETE',
    headers: supabaseHeaders(session, { Prefer: 'return=minimal' }),
  });
  if (!res.ok) throw new Error(`Remove phrase failed: ${res.status}`);
}

export async function toggleBannedPhrase(session, id, enabled) {
  const res = await fetch(`${SUPABASE_URL}/rest/v1/banned_phrases?id=eq.${id}`, {
    method: 'PATCH',
    headers: supabaseHeaders(session, { Prefer: 'return=minimal' }),
    body: JSON.stringify({ enabled }),
  });
  if (!res.ok) throw new Error(`Toggle phrase failed: ${res.status}`);
}

export function renderPhrases(rows) {
  const loading = document.getElementById('phrases-loading');
  const empty   = document.getElementById('phrases-empty');
  const table   = document.getElementById('phrases-table');
  const tbody   = document.getElementById('phrases-tbody');
  const err     = document.getElementById('phrases-error');

  loading.hidden = true;
  err.hidden = true;

  if (!rows.length) {
    empty.hidden = false;
    table.hidden = true;
    return;
  }

  empty.hidden = true;
  table.hidden = false;

  tbody.innerHTML = rows.map(r => {
    const id      = escapeHtml(String(r.id));
    const pattern = escapeHtml(r.pattern);
    const typeTag = r.is_regex
      ? '<span class="admin-badge admin-badge--regex">Regex</span>'
      : '<span class="admin-badge">Literal</span>';
    const desc    = escapeHtml(r.description || '—');
    const added   = escapeHtml(fmtDate(r.created_at));
    const toggleLabel = r.enabled ? 'Disable' : 'Enable';
    const toggleClass = r.enabled ? 'admin-btn--warn' : 'admin-btn--ok';
    return `<tr data-phrase-id="${id}"${r.enabled ? '' : ' class="admin-row--disabled"'}>
      <td><code class="admin-pattern">${pattern}</code></td>
      <td>${typeTag}</td>
      <td>${desc}</td>
      <td>${added}</td>
      <td>
        <div class="admin-actions">
          <button class="admin-btn admin-btn--sm ${toggleClass}" data-action="toggle-phrase" data-id="${id}" data-enabled="${r.enabled}">${toggleLabel}</button>
          <button class="admin-btn admin-btn--sm admin-btn--danger" data-action="remove-phrase" data-id="${id}">Remove</button>
        </div>
      </td>
    </tr>`;
  }).join('');
}

