// admin/teams.js — Globales Team-Register mit Soft-Delete, Dabei-Toggle und Filter

let allTeamsData = [];

async function loadAllTeams() {
  const tbody = document.getElementById('teams-list');
  tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text-muted)">Lade...</td></tr>';

  try {
    // Immer ALLE Teams laden (inkl. inaktive), Filter passiert client-side
    const res = await fetch(`${API_URL}/api/teams?include_inactive=true`);
    allTeamsData = await res.json();
    filterTeamsList();
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="7" style="color:var(--danger)">Fehler: ${e.message}</td></tr>`;
  }
}

function filterTeamsList() {
  const q = (document.getElementById('teams-search').value || '').toLowerCase().trim();
  const statusFilter = document.getElementById('teams-filter-status')?.value || 'active';
  const dabeiFilter = document.getElementById('teams-filter-dabei')?.value || 'all';

  let filtered = allTeamsData;

  if (statusFilter === 'active') {
    filtered = filtered.filter(t => t.is_active !== false);
  } else if (statusFilter === 'inactive') {
    filtered = filtered.filter(t => t.is_active === false);
  }

  if (dabeiFilter === 'dabei') {
    filtered = filtered.filter(t => t.participating_next);
  } else if (dabeiFilter === 'nicht-dabei') {
    filtered = filtered.filter(t => !t.participating_next);
  }

  if (q) {
    filtered = filtered.filter(t => t.name.toLowerCase().includes(q));
  }

  renderTeamsList(filtered);
}

function renderTeamsList(teams) {
  const tbody = document.getElementById('teams-list');
  const countEl = document.getElementById('teams-count');

  if (!teams.length) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text-muted)">Keine Teams gefunden</td></tr>';
    if (countEl) countEl.textContent = '';
    return;
  }

  if (countEl) countEl.textContent = `${teams.length} Team${teams.length !== 1 ? 's' : ''}`;

  tbody.innerHTML = teams.map(t => {
    const discord = t.discord_user
      ? escapeHtml(t.discord_user.discord_username || t.discord_user.discord_id)
      : '<span style="color:var(--text-muted)">–</span>';

    const onlineliga = t.onlineliga_url
      ? `<a href="${escapeHtml(t.onlineliga_url)}" target="_blank" rel="noopener" style="color:var(--primary);font-size:.85rem">🔗 Link</a>`
      : '<span style="color:var(--text-muted)">–</span>';

    const dabeiBtn = `<button class="toggle-participation-btn ${t.participating_next ? 'is-dabei' : ''}"
      onclick="toggleTeamDabei(${t.id}, ${!t.participating_next})"
      title="${t.participating_next ? 'Als Nicht-Dabei markieren' : 'Als Dabei markieren'}">
      ${t.participating_next ? '✅ Dabei' : '❌ Nicht dabei'}
    </button>`;

    const isActive = t.is_active !== false;
    const statusBadge = isActive
      ? '<span style="color:#4caf50;font-size:.85rem">● Aktiv</span>'
      : '<span style="color:#9ca3af;font-size:.85rem">● Inaktiv</span>';

    const seasonCount = t.seasons ? t.seasons.length : 0;
    const seasonBadge = seasonCount > 0
      ? `<span class="clickable-badge" style="background:var(--primary);color:#fff;padding:.15rem .5rem;border-radius:10px;font-size:.8rem;cursor:pointer" onclick="toggleSeasonDetails(${t.id})">${seasonCount} Saison${seasonCount !== 1 ? 's' : ''}</span>`
      : '<span style="color:var(--text-muted);font-size:.85rem">–</span>';

    const safeName = escapeHtml(t.name).replace(/'/g, '&#39;');
    const deactivateBtn = isActive
      ? `<button class="btn btn-sm" onclick="deactivateTeam(${t.id}, '${safeName}')" title="Deaktivieren" style="color:var(--danger)">🗑️</button>`
      : `<button class="btn btn-sm" onclick="reactivateTeam(${t.id}, '${safeName}')" title="Reaktivieren" style="color:#4caf50">♻️</button>`;

    const rowStyle = isActive ? '' : 'opacity:.5';

    const seasonDetails = t.seasons && t.seasons.length ? `
      <tr id="team-seasons-${t.id}" style="display:none">
        <td colspan="7" style="padding:.5rem 1rem;background:var(--bg-elevated)">
          <div style="display:flex;flex-wrap:wrap;gap:.5rem">
            ${t.seasons.map(s => {
              const statusColors = { planned: '#1e40af', active: '#166534', archived: '#888' };
              const color = statusColors[s.status] || '#888';
              return `<span style="font-size:.8rem;padding:.2rem .5rem;border-radius:4px;border:1px solid ${color};color:${color}">${escapeHtml(s.season_name)}${s.group_name ? ' / Gruppe ' + escapeHtml(s.group_name) : ''} (${s.status})</span>`;
            }).join('')}
          </div>
        </td>
      </tr>` : '';

    return `
      <tr style="${rowStyle}">
        <td><strong>${escapeHtml(t.name)}</strong>${t.logo_url ? ' 🖼️' : ''}</td>
        <td>${discord}</td>
        <td>${onlineliga}</td>
        <td>${dabeiBtn}</td>
        <td>${statusBadge}</td>
        <td>${seasonBadge}</td>
        <td style="text-align:right">
          <button class="btn btn-sm btn-secondary" onclick="editTeam(${t.id})" title="Bearbeiten">✏️</button>
          ${deactivateBtn}
        </td>
      </tr>${seasonDetails}`;
  }).join('');
}

function toggleSeasonDetails(teamId) {
  const row = document.getElementById(`team-seasons-${teamId}`);
  if (row) {
    row.style.display = row.style.display === 'none' ? '' : 'none';
  }
}

async function editTeam(teamId) {
  const team = allTeamsData.find(t => t.id === teamId);
  if (!team) {
    toast('Team nicht gefunden', 'error');
    return;
  }

  document.getElementById('edit-team-id').value = team.id;
  document.getElementById('edit-team-name').value = team.name;
  document.getElementById('edit-team-logo').value = team.logo_url || '';
  document.getElementById('edit-team-onlineliga').value = team.onlineliga_url || '';

  const discordNameEl = document.getElementById('edit-team-discord-name');
  const unlinkBtn = document.getElementById('edit-team-unlink-btn');
  if (discordNameEl) {
    if (team.discord_user) {
      discordNameEl.textContent = team.discord_user.discord_username || team.discord_user.discord_id;
      discordNameEl.style.color = 'var(--text-primary)';
      if (unlinkBtn) unlinkBtn.style.display = '';
    } else {
      discordNameEl.textContent = 'Kein Discord-User verknüpft';
      discordNameEl.style.color = 'var(--text-muted)';
      if (unlinkBtn) unlinkBtn.style.display = 'none';
    }
  }

  document.getElementById('edit-team-modal').style.display = 'flex';
}

function closeEditTeamModal() {
  document.getElementById('edit-team-modal').style.display = 'none';
}

async function saveTeamEdit() {
  const teamId = document.getElementById('edit-team-id').value;
  const name = document.getElementById('edit-team-name').value.trim();
  const logo_url = document.getElementById('edit-team-logo').value.trim() || null;
  const onlineliga_url = document.getElementById('edit-team-onlineliga').value.trim() || null;

  if (!name) {
    toast('Name erforderlich', 'error');
    return;
  }

  try {
    await authFetch(`${API_URL}/api/teams/${teamId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, logo_url, onlineliga_url })
    });

    toast('Team aktualisiert!');
    closeEditTeamModal();
    loadAllTeams();
  } catch (e) {
    toast('Fehler: ' + e.message, 'error');
  }
}

async function toggleTeamDabei(teamId, newStatus) {
  try {
    await authFetch(`${API_URL}/api/teams/${teamId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ participating_next: newStatus })
    });
    toast(newStatus ? 'Team als Dabei markiert' : 'Team als Nicht-Dabei markiert');
    loadAllTeams();
  } catch (e) {
    toast('Fehler: ' + e.message, 'error');
  }
}

async function deactivateTeam(teamId, teamName) {
  if (!confirm(`"${teamName}" deaktivieren?\n\nDas Team wird aus zukünftigen Saisons ausgeblendet und als "Nicht Dabei" markiert. Historische Daten (Matches, Standings) bleiben erhalten.`)) return;
  try {
    await authFetch(`${API_URL}/api/teams/${teamId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_active: false })
    });
    toast(`${teamName} deaktiviert`);
    loadAllTeams();
  } catch (e) {
    toast('Fehler: ' + e.message, 'error');
  }
}

async function reactivateTeam(teamId, teamName) {
  if (!confirm(`"${teamName}" reaktivieren?`)) return;
  try {
    await authFetch(`${API_URL}/api/teams/${teamId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_active: true })
    });
    toast(`${teamName} reaktiviert`);
    loadAllTeams();
  } catch (e) {
    toast('Fehler: ' + e.message, 'error');
  }
}

async function unlinkDiscordFromTeam() {
  const teamId = document.getElementById('edit-team-id').value;
  const team = allTeamsData.find(t => t.id === parseInt(teamId));
  if (!team || !team.discord_user) return;

  if (!confirm(`Discord-Verknüpfung für "${team.name}" lösen?\n\nDer User "${team.discord_user.discord_username}" wird von diesem Team getrennt.`)) return;

  try {
    await authFetch(`${API_URL}/api/discord/users/${team.discord_user.discord_id}/team`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ team_id: null })
    });
    toast('Verknüpfung gelöst');
    closeEditTeamModal();
    loadAllTeams();
  } catch (e) {
    toast('Fehler: ' + e.message, 'error');
  }
}
