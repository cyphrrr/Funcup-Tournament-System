// admin/teams.js — Team CRUD, editTeam Modal

async function loadTeamSeasons() {
  const seasons = await fetch(`${API_URL}/api/seasons`).then(r => r.json());
  const select = document.getElementById('team-season');
  select.innerHTML = '<option value="">Wählen...</option>' +
    seasons.map(s => `<option value="${s.id}">${s.name}</option>`).join('');
  select.onchange = loadTeamsForSeason;
}

async function loadTeamsForSeason() {
  const seasonId = document.getElementById('team-season').value;
  if (!seasonId) {
    document.getElementById('teams-list').innerHTML = '';
    return;
  }

  const groups = await fetch(`${API_URL}/api/seasons/${seasonId}/groups-with-teams`).then(r => r.json());

  let html = '<table><thead><tr><th>Team</th><th>Gruppe</th><th>Aktionen</th></tr></thead><tbody>';
  groups.forEach(g => {
    g.teams.forEach(t => {
      const logoIndicator = t.logo_url ? '🖼️' : '';
      const linkIndicator = t.onlineliga_url ? '🔗' : '';
      html += `
        <tr>
          <td>${t.name} ${logoIndicator} ${linkIndicator}</td>
          <td>Gruppe ${g.group.name}</td>
          <td>
            <button class="btn btn-sm btn-secondary" onclick="editTeam(${t.id})" title="Bearbeiten">✏️</button>
          </td>
        </tr>`;
    });
  });
  html += '</tbody></table>';

  document.getElementById('teams-list').innerHTML = html;
}

async function addTeam() {
  const seasonId = document.getElementById('team-season').value;
  const name = document.getElementById('team-name').value.trim();

  if (!seasonId || !name) {
    toast('Saison und Name erforderlich', 'error');
    return;
  }

  try {
    await authFetch(`${API_URL}/api/seasons/${seasonId}/teams`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    });
    toast('Team hinzugefügt!');
    document.getElementById('team-name').value = '';
    loadTeamsForSeason();
  } catch (e) {
    toast('Fehler: ' + e.message, 'error');
  }
}

async function bulkAddTeams() {
  const seasonId = document.getElementById('team-season').value;
  const text = document.getElementById('team-bulk').value.trim();

  if (!seasonId || !text) {
    toast('Saison und Teams erforderlich', 'error');
    return;
  }

  const teams = text.split('\n').map(t => t.trim()).filter(t => t);

  try {
    const res = await authFetch(`${API_URL}/api/seasons/${seasonId}/teams/bulk`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ teams })
    });
    const data = await res.json();
    toast(`${data.count} Teams importiert!`);
    document.getElementById('team-bulk').value = '';
    loadTeamsForSeason();
  } catch (e) {
    toast('Fehler: ' + e.message, 'error');
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
  document.getElementById('edit-team-id').value = '';
  document.getElementById('edit-team-name').value = '';
  document.getElementById('edit-team-logo').value = '';
  document.getElementById('edit-team-onlineliga').value = '';
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
    loadTeamsForSeason();
  } catch (e) {
    toast('Fehler: ' + e.message, 'error');
  }
}
