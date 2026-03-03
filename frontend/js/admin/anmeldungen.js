// admin/anmeldungen.js — Anmeldungen + Alle Discord User

let anmeldungenData = [];

async function loadAnmeldungen() {
  try {
    anmeldungenData = await fetchAPI('/admin/anmeldungen');
  } catch (e) {
    console.error('Fehler beim Laden der Anmeldungen:', e);
    anmeldungenData = [];
  }

  const total = anmeldungenData.length;
  const dabei = anmeldungenData.filter(u => u.participating_next).length;
  const incomplete = anmeldungenData.filter(u => u.participating_next && !u.is_complete).length;
  document.getElementById('anm-stat-total').textContent = total;
  document.getElementById('anm-stat-dabei').textContent = dabei;
  document.getElementById('anm-stat-incomplete').textContent = incomplete;

  renderAnmeldungenTable(anmeldungenData.filter(u => u.participating_next));
}

function renderAnmeldungenTable(users) {
  const tbody = document.getElementById('anm-aktive-saison-tbody');
  if (!users.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted)">Keine Teilnehmer mit aktivem Dabei-Status</td></tr>';
    return;
  }

  tbody.innerHTML = '';
  users.forEach(user => {
    const rowClass = user.is_complete ? 'row-complete' : 'row-incomplete';
    const statusBadge = user.is_complete
      ? '<span class="badge-ready">✅ Ready</span>'
      : '<span class="badge-warn">⚠️ Unvollständig</span>';

    const tr = document.createElement('tr');
    tr.className = rowClass;
    tr.dataset.complete = user.is_complete ? '1' : '0';
    tr.innerHTML = `
      <td><strong>${escapeHtml(user.discord_username)}</strong></td>
      <td>${user.team_name ? escapeHtml(user.team_name) : '<span class="missing">—</span>'}</td>
      <td>${user.has_profile ? '✅' : '❌'}</td>
      <td>
        <button class="toggle-participation-btn is-dabei" onclick="toggleDabei('${user.discord_id}', false)">
          ✅ Ja
        </button>
      </td>
      <td>${statusBadge}</td>
      <td style="text-align:right">
        <button class="btn btn-sm" onclick="openTeamAssignModal('${user.discord_id}')" title="Team zuweisen" style="margin-right:4px">🔗 Team</button>
        <button class="btn btn-sm btn-danger" onclick="removeFromSeason('${user.discord_id}', '${escapeHtml(user.discord_username)}')" title="Aus Saison entfernen">✕</button>
      </td>
    `;
    tbody.appendChild(tr);
  });

  applyAnmFilter();
}

function applyAnmFilter() {
  const activeBtn = document.querySelector('.anm-filter-btn.active');
  const filter = activeBtn ? activeBtn.dataset.filter : 'all';
  document.querySelectorAll('#anm-aktive-saison-tbody tr').forEach(tr => {
    if (filter === 'all') {
      tr.style.display = '';
    } else if (filter === 'ready') {
      tr.style.display = tr.dataset.complete === '1' ? '' : 'none';
    } else if (filter === 'incomplete') {
      tr.style.display = tr.dataset.complete === '0' ? '' : 'none';
    }
  });
}

async function toggleDabei(discordId, newStatus) {
  try {
    await fetchAPI(`/discord/users/${discordId}/participation`, {
      method: 'PATCH',
      body: JSON.stringify({ participating: newStatus })
    });
    loadAnmeldungen();
  } catch (e) {
    alert('Fehler: ' + (e.message || e));
  }
}

async function removeFromSeason(discordId, username) {
  if (!confirm(`${username} wirklich aus der aktiven Saison entfernen?`)) return;
  try {
    await fetchAPI(`/admin/anmeldungen/${discordId}/season`, { method: 'DELETE' });
    loadAnmeldungen();
  } catch (e) {
    alert('Fehler: ' + (e.message || e));
  }
}

function openTeamAssignModal(discordId) {
  document.getElementById('team-assign-discord-id').value = discordId;
  document.getElementById('team-assign-search').value = '';
  document.getElementById('team-assign-results').innerHTML = '';
  const modal = document.getElementById('team-assign-modal');
  modal.style.display = 'flex';
}

function closeTeamAssignModal() {
  document.getElementById('team-assign-modal').style.display = 'none';
}

async function searchTeamsForAssign() {
  const q = document.getElementById('team-assign-search').value.trim();
  if (q.length < 2) {
    document.getElementById('team-assign-results').innerHTML = '';
    return;
  }
  try {
    const teams = await fetchAPI(`/teams/search?name=${encodeURIComponent(q)}`);
    const results = document.getElementById('team-assign-results');
    results.innerHTML = '';
    teams.forEach(t => {
      const btn = document.createElement('div');
      btn.style.cssText = 'padding:8px;cursor:pointer;border-bottom:1px solid #e5e7eb';
      btn.textContent = t.name;
      btn.onclick = () => assignTeam(t.id, t.name);
      results.appendChild(btn);
    });
    if (!teams.length) results.innerHTML = '<div style="padding:8px;color:#aaaabc">Keine Teams gefunden</div>';
  } catch (e) {
    console.error(e);
  }
}

async function assignTeam(teamId, teamName) {
  const discordId = document.getElementById('team-assign-discord-id').value;
  try {
    await fetchAPI(`/discord/users/${discordId}/team`, {
      method: 'PATCH',
      body: JSON.stringify({ team_id: teamId })
    });
    closeTeamAssignModal();
    loadAnmeldungen();
  } catch (e) {
    alert('Fehler: ' + (e.message || e));
  }
}

async function loadAlleDiscordUser() {
  const search = document.getElementById('anm-user-search')?.value || '';
  const noTeam = document.getElementById('anm-filter-no-team')?.checked || false;

  let url = '/discord/users';
  const params = [];
  if (search) params.push(`search=${encodeURIComponent(search)}`);
  if (noTeam) params.push('has_team=false');
  if (params.length) url += '?' + params.join('&');

  try {
    const users = await fetchAPI(url);
    const tbody = document.getElementById('anm-alle-user-tbody');
    tbody.innerHTML = '';

    if (!users.length) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted)">Keine User</td></tr>';
      return;
    }

    users.forEach(user => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td data-discord="${escapeHtml(user.discord_username)}">${escapeHtml(user.discord_username)}</td>
        <td data-team="${escapeHtml(user.team_name || '')}">${user.team_name ? escapeHtml(user.team_name) : '<span class="missing">—</span>'}</td>
        <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis">${user.profile_url ? `<a href="${escapeHtml(user.profile_url)}" target="_blank" style="color:var(--primary)">${escapeHtml(user.profile_url)}</a>` : '<span class="missing">—</span>'}</td>
        <td>
          <input type="checkbox" class="participation-checkbox" ${user.participating_next ? 'checked' : ''} onchange="toggleParticipation('${user.discord_id}', this.checked)">
        </td>
        <td style="color:var(--text-muted);font-size:.85rem">${user.created_at ? new Date(user.created_at).toLocaleDateString('de-DE') : '—'}</td>
        <td style="text-align:right">
          <button class="btn btn-sm" onclick="openTeamAssignModal('${user.discord_id}')" title="Team zuweisen">🔗 Team</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) {
    console.error('Fehler beim Laden der User:', e);
  }
}

let anmUserSearchTimeout;
function debounceAnmUserSearch() {
  clearTimeout(anmUserSearchTimeout);
  const term = document.getElementById('anm-user-search')?.value?.toLowerCase()?.trim() || '';
  const noTeam = document.getElementById('anm-filter-no-team')?.checked || false;

  document.querySelectorAll('#anm-alle-user-tbody tr').forEach(tr => {
    const d = tr.querySelector('[data-discord]')?.dataset.discord?.toLowerCase() || '';
    const t = tr.querySelector('[data-team]')?.dataset.team?.toLowerCase() || '';
    const hasTeam = tr.querySelector('[data-team]')?.dataset.team?.trim();

    const matchesSearch = !term || d.includes(term) || t.includes(term);
    const matchesTeamFilter = !noTeam || !hasTeam;
    tr.style.display = (matchesSearch && matchesTeamFilter) ? '' : 'none';
  });
}

async function toggleParticipation(discordId, newStatus) {
  const checkbox = event.target;
  try {
    await fetchAPI(`/discord/users/${discordId}/participation`, {
      method: 'PATCH',
      body: JSON.stringify({ participating: newStatus })
    });
    toast('Teilnahme aktualisiert', 'success');
  } catch (e) {
    toast('Fehler beim Aktualisieren', 'error');
    checkbox.checked = !newStatus;
  }
}

async function searchRegTeams() {
  const q = document.getElementById('reg-team-search').value.trim();
  if (q.length < 2) {
    document.getElementById('reg-team-suggestions').innerHTML = '';
    return;
  }
  try {
    const teams = await fetchAPI(`/teams/search?name=${encodeURIComponent(q)}`);
    const results = document.getElementById('reg-team-suggestions');
    results.innerHTML = '';
    teams.forEach(t => {
      const div = document.createElement('div');
      div.style.cssText = 'padding:8px;cursor:pointer;border-bottom:1px solid #e5e7eb';
      div.textContent = t.name;
      div.onmouseover = () => div.style.background = '#f3f4f6';
      div.onmouseout = () => div.style.background = '';
      div.onclick = () => {
        document.getElementById('reg-team-search').value = t.name;
        document.getElementById('reg-team-id').value = t.id;
        results.innerHTML = '';
      };
      results.appendChild(div);
    });
    if (!teams.length) results.innerHTML = '<div style="padding:8px;color:#aaaabc">Keine Teams gefunden</div>';
  } catch (e) {
    console.error(e);
  }
}

async function searchSetupRegTeams() {
  const q = document.getElementById('setup-reg-team-search').value.trim();
  if (q.length < 2) {
    document.getElementById('setup-reg-team-suggestions').innerHTML = '';
    return;
  }
  try {
    const teams = await fetchAPI(`/teams/search?name=${encodeURIComponent(q)}`);
    const results = document.getElementById('setup-reg-team-suggestions');
    results.innerHTML = '';
    teams.forEach(t => {
      const div = document.createElement('div');
      div.style.cssText = 'padding:8px;cursor:pointer;border-bottom:1px solid #e5e7eb';
      div.textContent = t.name;
      div.onmouseover = () => div.style.background = '#f3f4f6';
      div.onmouseout = () => div.style.background = '';
      div.onclick = () => {
        document.getElementById('setup-reg-team-search').value = t.name;
        document.getElementById('setup-reg-team-id').value = t.id;
        results.innerHTML = '';
      };
      results.appendChild(div);
    });
    if (!teams.length) results.innerHTML = '<div style="padding:8px;color:#aaaabc">Keine Teams gefunden</div>';
  } catch (e) {
    console.error(e);
  }
}

async function submitSetupRegistration() {
  const teamId = document.getElementById('setup-reg-team-id').value;
  if (!teamId) {
    toast('Bitte ein Team auswählen', 'warning');
    return;
  }

  const payload = {
    team_id: parseInt(teamId),
    discord_username: document.getElementById('setup-reg-discord-username').value || null,
    discord_id: document.getElementById('setup-reg-discord-id').value || null,
    profile_url: document.getElementById('setup-reg-profile-url').value || null,
    participating_next: document.getElementById('setup-reg-participating').checked
  };

  try {
    await authFetch(`${API_URL}/api/discord/users/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    toast('Teilnehmer registriert ✅', 'success');
    document.getElementById('setup-register-form').reset();
    document.getElementById('setup-reg-team-id').value = '';
    document.getElementById('setup-reg-team-suggestions').innerHTML = '';
    loadParticipants();
  } catch (e) {
    toast('Fehler: ' + (e.message || e), 'error');
  }
}

async function submitRegistration() {
  const teamId = document.getElementById('reg-team-id').value;
  if (!teamId) {
    toast('Bitte ein Team auswählen', 'warning');
    return;
  }

  const payload = {
    team_id: parseInt(teamId),
    discord_username: document.getElementById('reg-discord-username').value || null,
    discord_id: document.getElementById('reg-discord-id').value || null,
    profile_url: document.getElementById('reg-profile-url').value || null,
    participating_next: document.getElementById('reg-participating').checked
  };

  try {
    await authFetch(`${API_URL}/api/discord/users/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    toast('Teilnehmer registriert ✅', 'success');
    document.getElementById('register-form').reset();
    document.getElementById('reg-team-id').value = '';
    document.getElementById('reg-team-suggestions').innerHTML = '';
    loadAnmeldungen();
  } catch (e) {
    toast('Fehler: ' + (e.message || e), 'error');
  }
}
