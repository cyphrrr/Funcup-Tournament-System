// admin/saisons.js — Saison CRUD, editSeason Modal

async function loadSeasons() {
  try {
    const seasons = await fetch(`${API_URL}/api/seasons`).then(r => r.json());

    const allGroups = await Promise.allSettled(
      seasons.map(s => fetch(`${API_URL}/api/seasons/${s.id}/groups-with-teams`).then(r => r.json()))
    );

    let html = '';
    seasons.forEach((s, i) => {
      const result = allGroups[i];
      const groups = result.status === 'fulfilled' ? result.value : [];
      const teamCount = groups.reduce((sum, g) => sum + (g.teams ? g.teams.length : 0), 0);
      const teamDisplay = result.status === 'fulfilled' ? `${teamCount} / ${s.participant_count}` : `? / ${s.participant_count}`;

      const statusColors = {
        'planned': 'color:#1e40af;background:#dbeafe',
        'active': 'color:#166534;background:#dcfce7',
        'archived': 'color:#aaaabc;background:#2a2a3d'
      };
      const statusStyle = statusColors[s.status] || '';

      html += `
        <tr>
          <td>${s.id}</td>
          <td><strong>${s.name}</strong></td>
          <td>${teamDisplay}</td>
          <td><span style="padding:.2rem .5rem;border-radius:4px;font-size:.8rem;${statusStyle}">${s.status}</span></td>
          <td>
            <button class="btn btn-sm btn-secondary" onclick="generateSchedule(${s.id})" title="Spielplan generieren">📅</button>
            <button class="btn btn-sm btn-primary" onclick="editSeason(${s.id})" title="Bearbeiten">✏️</button>
            <button class="btn btn-sm btn-danger" onclick="deleteSeason(${s.id})" title="Löschen">🗑️</button>
          </td>
        </tr>`;
    });

    document.getElementById('seasons-list').innerHTML = html || '<tr><td colspan="5"><em>Keine Saisons</em></td></tr>';
  } catch (e) {
    console.error('loadSeasons error:', e);
    document.getElementById('seasons-list').innerHTML = '<tr><td colspan="5"><em>Fehler beim Laden der Saisons</em></td></tr>';
  }
}

async function editSeason(seasonId) {
  try {
    const season = await fetch(`${API_URL}/api/seasons/${seasonId}`).then(r => r.json());

    document.getElementById('edit-season-id').value = season.id;
    document.getElementById('edit-season-name').value = season.name;
    document.getElementById('edit-season-status').value = season.status;

    document.getElementById('edit-season-modal').style.display = 'flex';
  } catch (e) {
    toast('Fehler beim Laden: ' + e.message, 'error');
  }
}

function closeEditSeasonModal() {
  document.getElementById('edit-season-modal').style.display = 'none';
  document.getElementById('edit-season-id').value = '';
  document.getElementById('edit-season-name').value = '';
}

async function saveSeasonEdit() {
  const seasonId = document.getElementById('edit-season-id').value;
  const name = document.getElementById('edit-season-name').value.trim();
  const status = document.getElementById('edit-season-status').value;

  if (!name) {
    toast('Name erforderlich', 'error');
    return;
  }

  try {
    await authFetch(`${API_URL}/api/seasons/${seasonId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, status })
    });

    toast('Saison aktualisiert!');
    closeEditSeasonModal();
    loadSeasons();
  } catch (e) {
    toast('Fehler: ' + e.message, 'error');
  }
}

async function deleteSeason(seasonId) {
  const season = await fetch(`${API_URL}/api/seasons/${seasonId}`).then(r => r.json());

  const confirmed = confirm(
    `Saison "${season.name}" wirklich löschen?\n\n` +
    `⚠️ Dies löscht ALLE zugehörigen Daten:\n` +
    `- Gruppen\n` +
    `- Teams\n` +
    `- Matches\n` +
    `- KO-Bracket\n\n` +
    `Diese Aktion kann nicht rückgängig gemacht werden!`
  );

  if (!confirmed) return;

  try {
    await authFetch(`${API_URL}/api/seasons/${seasonId}`, {
      method: 'DELETE'
    });

    toast('Saison gelöscht');
    loadSeasons();

    if (document.getElementById('dashboard').classList.contains('active')) {
      loadDashboard();
    }
  } catch (e) {
    toast('Fehler: ' + e.message, 'error');
  }
}

async function createSeason() {
  const name = document.getElementById('season-name').value.trim();
  const count = parseInt(document.getElementById('season-count').value);

  if (!name || !count) {
    toast('Name und Anzahl erforderlich', 'error');
    return;
  }

  try {
    await authFetch(`${API_URL}/api/seasons`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, participant_count: count })
    });
    toast('Saison erstellt!');
    document.getElementById('season-name').value = '';
    loadSeasons();
  } catch (e) {
    toast('Fehler: ' + e.message, 'error');
  }
}

async function generateSchedule(seasonId) {
  const groups = await fetch(`${API_URL}/api/seasons/${seasonId}/groups-with-teams`).then(r => r.json());

  let generated = 0;
  for (const g of groups) {
    if (g.matches.length > 0) continue;
    try {
      await authFetch(`${API_URL}/api/groups/${g.group.id}/generate-schedule`, { method: 'POST' });
      generated++;
    } catch (e) {}
  }

  toast(`Spielplan für ${generated} Gruppen generiert!`);
  loadSeasons();
}
