// admin/discord.js — Legacy Discord User Modals

let currentTeamModalDiscordId = null;

function loadDiscordUsers() { loadAlleDiscordUser(); }

async function deleteDiscordUser(discordId, username) {
  if (!confirm(`User "${username}" wirklich löschen?\n\nDieser Vorgang kann nicht rückgängig gemacht werden.`)) {
    return;
  }

  try {
    await authFetch(`${API_URL}/api/discord/users/${discordId}`, {
      method: 'DELETE'
    });
    toast(`User "${username}" gelöscht`, 'success');
    loadDiscordUsers();
  } catch (e) {
    toast('Fehler beim Löschen: ' + e.message, 'error');
  }
}

function openTeamModal(discordId, username) {
  currentTeamModalDiscordId = discordId;
  document.getElementById('team-modal-title').textContent = `Team für ${username} zuweisen`;
  document.getElementById('team-search-input').value = '';
  document.getElementById('team-search-results').innerHTML = '';
  document.getElementById('team-modal').style.display = 'flex';
}

function closeTeamModal() {
  document.getElementById('team-modal').style.display = 'none';
  currentTeamModalDiscordId = null;
}

async function searchTeamsForModal() {
  const query = document.getElementById('team-search-input').value.trim();
  const resultsDiv = document.getElementById('team-search-results');

  if (query.length < 2) {
    resultsDiv.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:1rem">Mindestens 2 Zeichen eingeben...</p>';
    return;
  }

  try {
    const teams = await authFetch(`${API_URL}/api/teams/search?name=${encodeURIComponent(query)}`).then(r => r.json());

    if (teams.length === 0) {
      resultsDiv.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:1rem">Keine Teams gefunden</p>';
      return;
    }

    resultsDiv.innerHTML = teams.map(team => `
      <div style="padding:.75rem;border:1px solid var(--border-dark);border-radius:6px;margin-bottom:.5rem;cursor:pointer;background:var(--bg-section)"
           data-team-id="${team.id}" data-team-name="${escapeHtml(team.name)}"
           onclick="assignTeamLegacy(+this.dataset.teamId, this.dataset.teamName)">
        <strong>${escapeHtml(team.name)}</strong>
        <small style="color:var(--text-muted);display:block">ID: ${team.id}</small>
      </div>
    `).join('');
  } catch (e) {
    resultsDiv.innerHTML = `<p style="color:var(--danger);text-align:center;padding:1rem">Fehler: ${e.message}</p>`;
  }
}

async function assignTeamLegacy(teamId, teamName) {
  if (!currentTeamModalDiscordId) return;

  try {
    await authFetch(`${API_URL}/api/discord/users/${currentTeamModalDiscordId}/admin-set-team`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ team_id: teamId })
    });

    toast(`Team "${teamName}" zugewiesen`, 'success');
    closeTeamModal();
    loadDiscordUsers();
  } catch (e) {
    toast('Fehler beim Zuweisen: ' + e.message, 'error');
  }
}

async function removeTeamAssignment() {
  if (!currentTeamModalDiscordId) return;

  if (!confirm('Team-Verknüpfung wirklich entfernen?')) {
    return;
  }

  try {
    await authFetch(`${API_URL}/api/discord/users/${currentTeamModalDiscordId}/admin-set-team`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ team_id: null })
    });

    toast('Team-Verknüpfung entfernt', 'success');
    closeTeamModal();
    loadDiscordUsers();
  } catch (e) {
    toast('Fehler: ' + e.message, 'error');
  }
}
