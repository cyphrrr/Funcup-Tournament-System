// admin/teams.js — Globales Team-Register mit aufklappbarer Saison-Historie

let allTeamsData = [];

async function loadAllTeams() {
  const tbody = document.getElementById('teams-list');
  tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--muted)">Lade...</td></tr>';

  try {
    const res = await fetch(`${API_URL}/api/teams`);
    allTeamsData = await res.json();
    renderTeamsList(allTeamsData);
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="4" style="color:var(--danger)">Fehler: ${e.message}</td></tr>`;
  }
}

function filterTeamsList() {
  const q = (document.getElementById('teams-search').value || '').toLowerCase().trim();
  if (!q) {
    renderTeamsList(allTeamsData);
    return;
  }
  renderTeamsList(allTeamsData.filter(t => t.name.toLowerCase().includes(q)));
}

function renderTeamsList(teams) {
  const tbody = document.getElementById('teams-list');

  if (!teams.length) {
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--muted)">Keine Teams gefunden</td></tr>';
    return;
  }

  tbody.innerHTML = teams.map(t => {
    const discord = t.discord_user
      ? t.discord_user.discord_username || t.discord_user.discord_id
      : '<span style="color:var(--muted)">–</span>';

    const seasonCount = t.seasons.length;
    const seasonBadge = seasonCount > 0
      ? `<span class="clickable-badge" style="background:var(--primary);color:#fff;padding:.15rem .5rem;border-radius:10px;font-size:.8rem;cursor:pointer" onclick="toggleSeasonDetails(${t.id})">${seasonCount} Saison${seasonCount !== 1 ? 's' : ''}</span>`
      : '<span style="color:var(--warning);font-size:.85rem">Keine Saison</span>';

    const seasonDetails = t.seasons.length ? `
      <tr id="team-seasons-${t.id}" style="display:none">
        <td colspan="4" style="padding:.5rem 1rem;background:var(--accent)">
          <div style="display:flex;flex-wrap:wrap;gap:.5rem">
            ${t.seasons.map(s => {
              const statusColors = { planned: '#1e40af', active: '#166534', archived: '#888' };
              const color = statusColors[s.status] || '#888';
              return `<span style="font-size:.8rem;padding:.2rem .5rem;border-radius:4px;border:1px solid ${color};color:${color}">${s.season_name}${s.group_name ? ' / Gruppe ' + s.group_name : ''} (${s.status})</span>`;
            }).join('')}
          </div>
        </td>
      </tr>` : '';

    const noSeasonStyle = seasonCount === 0 ? 'opacity:.6' : '';

    return `
      <tr style="${noSeasonStyle}">
        <td><strong>${escapeHtml(t.name)}</strong>${t.logo_url ? ' 🖼️' : ''}${t.onlineliga_url ? ' 🔗' : ''}</td>
        <td>${discord}</td>
        <td>${seasonBadge}</td>
        <td>
          <button class="btn btn-sm btn-secondary" onclick="editTeam(${t.id})" title="Bearbeiten">✏️</button>
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
  try {
    const team = await fetch(`${API_URL}/api/teams/${teamId}`).then(r => r.json());

    document.getElementById('edit-team-id').value = team.id;
    document.getElementById('edit-team-name').value = team.name;
    document.getElementById('edit-team-logo').value = team.logo_url || '';
    document.getElementById('edit-team-onlineliga').value = team.onlineliga_url || '';

    document.getElementById('edit-team-modal').style.display = 'flex';
  } catch (e) {
    toast('Fehler beim Laden: ' + e.message, 'error');
  }
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
