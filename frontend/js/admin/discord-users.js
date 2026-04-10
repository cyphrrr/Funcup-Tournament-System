// admin/discord-users.js — Discord User Verwaltung (Stammdaten)

let allDiscordUsersData = [];

async function loadDiscordUsersList() {
  const tbody = document.getElementById('discord-users-tbody');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted)">Lade...</td></tr>';

  const search = document.getElementById('discord-users-search')?.value || '';
  const statusFilter = document.getElementById('discord-users-filter-status')?.value || 'active';
  const teamFilter = document.getElementById('discord-users-filter-team')?.value || 'all';

  const includeInactive = statusFilter !== 'active';
  const hasTeam = teamFilter === 'with-team' ? true : teamFilter === 'without-team' ? false : null;

  let url = `${API_URL}/api/discord/users?`;
  const params = [];
  if (search) params.push(`search=${encodeURIComponent(search)}`);
  if (includeInactive) params.push('include_inactive=true');
  if (hasTeam !== null) params.push(`has_team=${hasTeam}`);
  url += params.join('&');

  try {
    const res = await authFetch(url);
    allDiscordUsersData = await res.json();

    let filtered = allDiscordUsersData;
    if (statusFilter === 'active') {
      filtered = filtered.filter(u => u.is_active !== false);
    } else if (statusFilter === 'inactive') {
      filtered = filtered.filter(u => u.is_active === false);
    }

    renderDiscordUsersList(filtered);
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="6" style="color:var(--danger)">Fehler: ${e.message}</td></tr>`;
  }
}

function renderDiscordUsersList(users) {
  const tbody = document.getElementById('discord-users-tbody');
  const countEl = document.getElementById('discord-users-count');

  if (!users.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted)">Keine User gefunden</td></tr>';
    if (countEl) countEl.textContent = '0 User';
    return;
  }

  if (countEl) countEl.textContent = `${users.length} User`;

  tbody.innerHTML = users.map(u => {
    const teamName = u.team_name
      ? escapeHtml(u.team_name)
      : '<span style="color:var(--text-muted)">–</span>';

    const profileUrl = u.profile_url
      ? `<a href="${escapeHtml(u.profile_url)}" target="_blank" rel="noopener" style="color:var(--primary);font-size:.85rem">🔗 Profil</a>`
      : '<span style="color:var(--text-muted)">–</span>';

    const isActive = u.is_active !== false;
    const statusBadge = isActive
      ? '<span style="color:#4caf50;font-size:.85rem">● Aktiv</span>'
      : '<span style="color:#9ca3af;font-size:.85rem">● Inaktiv</span>';

    const createdAt = u.created_at
      ? new Date(u.created_at).toLocaleDateString('de-DE')
      : '–';

    const safeUsername = escapeHtml(u.discord_username || '').replace(/'/g, '&#39;');
    const deactivateBtn = isActive
      ? `<button class="btn btn-sm" onclick="deactivateDiscordUser('${u.discord_id}', '${safeUsername}')" title="Deaktivieren" style="color:var(--danger)">🗑️</button>`
      : `<button class="btn btn-sm" onclick="reactivateDiscordUser('${u.discord_id}', '${safeUsername}')" title="Reaktivieren" style="color:#4caf50">♻️</button>`;

    const rowStyle = isActive ? '' : 'opacity:.5';

    return `<tr style="${rowStyle}">
      <td><strong>${escapeHtml(u.discord_username || u.discord_id)}</strong></td>
      <td>${teamName}</td>
      <td>${profileUrl}</td>
      <td>${statusBadge}</td>
      <td style="font-size:.85rem;color:var(--text-muted)">${createdAt}</td>
      <td style="text-align:right">
        <button class="btn btn-sm btn-secondary" onclick="editDiscordUser('${u.discord_id}')" title="Bearbeiten">✏️</button>
        ${deactivateBtn}
      </td>
    </tr>`;
  }).join('');
}

let discordUserSearchTimeout;
function debounceDiscordUserSearch() {
  clearTimeout(discordUserSearchTimeout);
  discordUserSearchTimeout = setTimeout(loadDiscordUsersList, 300);
}

function editDiscordUser(discordId) {
  const user = allDiscordUsersData.find(u => u.discord_id === discordId);
  if (!user) return;

  document.getElementById('edit-du-discord-id').value = user.discord_id;
  document.getElementById('edit-du-id-display').value = user.discord_id;
  document.getElementById('edit-du-username').value = user.discord_username || '';
  document.getElementById('edit-du-profile-url').value = user.profile_url || '';

  const teamNameEl = document.getElementById('edit-du-team-name');
  const unlinkBtn = document.getElementById('edit-du-unlink-team-btn');
  if (user.team_name) {
    teamNameEl.textContent = user.team_name;
    teamNameEl.style.color = 'var(--text-primary)';
    if (unlinkBtn) unlinkBtn.style.display = '';
  } else {
    teamNameEl.textContent = 'Kein Team verknüpft';
    teamNameEl.style.color = 'var(--text-muted)';
    if (unlinkBtn) unlinkBtn.style.display = 'none';
  }

  document.getElementById('edit-discord-user-modal').style.display = 'flex';
}

function closeEditDiscordUserModal() {
  document.getElementById('edit-discord-user-modal').style.display = 'none';
}

async function saveDiscordUserEdit() {
  const discordId = document.getElementById('edit-du-discord-id').value;
  const username = document.getElementById('edit-du-username').value.trim();
  const profileUrl = document.getElementById('edit-du-profile-url').value.trim() || null;

  if (!username) {
    toast('Username erforderlich', 'error');
    return;
  }

  try {
    await authFetch(`${API_URL}/api/discord/users/${discordId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ discord_username: username, profile_url: profileUrl })
    });
    toast('User aktualisiert!');
    closeEditDiscordUserModal();
    loadDiscordUsersList();
  } catch (e) {
    toast('Fehler: ' + e.message, 'error');
  }
}

async function unlinkTeamFromUser() {
  const discordId = document.getElementById('edit-du-discord-id').value;
  const user = allDiscordUsersData.find(u => u.discord_id === discordId);
  if (!user) return;

  if (!confirm(`Team-Verknüpfung für "${user.discord_username}" lösen?`)) return;

  try {
    await authFetch(`${API_URL}/api/discord/users/${discordId}/team`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ team_id: null })
    });
    toast('Verknüpfung gelöst');
    closeEditDiscordUserModal();
    loadDiscordUsersList();
  } catch (e) {
    toast('Fehler: ' + e.message, 'error');
  }
}

async function deactivateDiscordUser(discordId, username) {
  if (!confirm(`"${username}" deaktivieren?\n\nDie Team-Verknüpfung bleibt bestehen.`)) return;
  try {
    await authFetch(`${API_URL}/api/discord/users/${discordId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_active: false })
    });
    toast(`${username} deaktiviert`);
    loadDiscordUsersList();
  } catch (e) {
    toast('Fehler: ' + e.message, 'error');
  }
}

async function reactivateDiscordUser(discordId, username) {
  if (!confirm(`"${username}" reaktivieren?`)) return;
  try {
    await authFetch(`${API_URL}/api/discord/users/${discordId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_active: true })
    });
    toast(`${username} reaktiviert`);
    loadDiscordUsersList();
  } catch (e) {
    toast('Fehler: ' + e.message, 'error');
  }
}
