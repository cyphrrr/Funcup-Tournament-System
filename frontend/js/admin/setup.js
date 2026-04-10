// admin/setup.js — Saison-Setup Wizard (3 Tabs: Saisons / Teilnehmer / Spielplan)

const setupState = {
  participants: [],
  manualTeamSelected: null,
  createdSeasonId: null,
  seededTeams: { A: null, B: null, C: null },
};

function showSetupTab(tabId) {
  document.querySelectorAll('.setup-tab').forEach(t => t.style.display = 'none');
  document.querySelectorAll('.tab[data-tab]').forEach(t => t.classList.remove('active'));
  document.getElementById(tabId).style.display = 'block';
  document.querySelector(`.tab[data-tab="${tabId}"]`).classList.add('active');
}

let allSetupSeasons = [];

async function initSaisonSetup() {
  try {
    const seasons = await authFetch(`${API_URL}/api/seasons`).then(r => r.json());
    allSetupSeasons = seasons;

    renderSetupSeasonsList(seasons);

    const activePlanned = seasons.filter(s => s.status !== 'archived').sort((a, b) => b.id - a.id);

    // Spielplan-Tab Dropdown
    const scheduleSel = document.getElementById('schedule-season-select');
    if (scheduleSel) {
      scheduleSel.innerHTML = '<option value="">Wählen...</option>';
      activePlanned.forEach(s => {
        scheduleSel.innerHTML += `<option value="${s.id}">${escapeHtml(s.name)} (${s.status})</option>`;
      });
    }

    // Teilnehmer-Tab Saison-Dropdown
    const participantSel = document.getElementById('participants-season-select');
    if (participantSel) {
      const current = participantSel.value;
      participantSel.innerHTML = '<option value="">Saison wählen...</option>';
      activePlanned.forEach(s => {
        const gidLabel = s.sheet_tab_gid ? ' ✅' : ' ⚠️ keine GID';
        participantSel.innerHTML += `<option value="${s.id}">${escapeHtml(s.name)} (${s.status})${gidLabel}</option>`;
      });
      // Bisherige Auswahl oder Auto-Select wenn nur eine Saison
      if (current && activePlanned.some(s => String(s.id) === current)) {
        participantSel.value = current;
      } else if (activePlanned.length === 1) {
        participantSel.value = activePlanned[0].id;
      }
    }

    showSetupTab('tab-seasons');
  } catch (e) {
    console.error('Fehler beim Laden der Saisons:', e);
  }
}

async function createNewSeason() {
  const name = document.getElementById('new-season-name').value.trim();
  const gid = document.getElementById('new-season-gid').value.trim() || null;

  if (!name) { toast('Saison-Name erforderlich', 'error'); return; }

  try {
    const res = await authFetch(`${API_URL}/api/seasons`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, participant_count: 0, sheet_tab_gid: gid }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Saison konnte nicht erstellt werden');
    }
    const season = await res.json();
    toast(`Saison "${name}" erstellt`);
    document.getElementById('new-season-name').value = '';
    document.getElementById('new-season-gid').value = '';
    await initSaisonSetup();
  } catch (e) {
    toast(`Fehler: ${e.message}`, 'error');
  }
}

// ---- Tab: Saisons ----

function renderSetupSeasonsList(seasons) {
  const tbody = document.getElementById('setup-seasons-list');
  if (!seasons.length) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted)">Keine Saisons vorhanden</td></tr>';
    return;
  }

  const statusLabel = { planned: 'Geplant', active: 'Aktiv', archived: 'Archiviert' };
  const statusColor = { planned: 'var(--warning)', active: 'var(--success)', archived: 'var(--text-muted)' };

  tbody.innerHTML = seasons.map(s => {
    const gidBadge = s.sheet_tab_gid ? '📋' : '⚠️';
    const gidColor = s.sheet_tab_gid ? '#4caf50' : '#ff9800';
    const gidTitle = s.sheet_tab_gid ? 'Sheet-GID hinterlegt' : 'Keine Sheet-GID';
    return `<tr>
    <td style="color:var(--text-muted)">${s.id}</td>
    <td><strong>${escapeHtml(s.name)}</strong> <span style="color:${gidColor};font-size:.75rem;margin-left:.5rem" title="${gidTitle}">${gidBadge}</span></td>
    <td style="text-align:center;color:var(--text-muted)">${s.participant_count ?? '–'}</td>
    <td><span style="color:${statusColor[s.status] || 'inherit'};font-weight:600">${statusLabel[s.status] || s.status}</span></td>
    <td style="text-align:right">
      <button class="btn btn-small btn-secondary" onclick="editSetupSeason(${s.id})">✏️ Bearbeiten</button>
      <button class="btn btn-small btn-danger" onclick="deleteSetupSeason(${s.id})" style="margin-left:.25rem">🗑️</button>
    </td>
  </tr>`;
  }).join('');
}

function editSetupSeason(id) {
  const s = allSetupSeasons.find(x => x.id === id);
  if (!s) return;
  document.getElementById('setup-edit-season-id').value = s.id;
  document.getElementById('setup-edit-season-name').value = s.name;
  document.getElementById('setup-edit-season-status').value = s.status;
  document.getElementById('setup-edit-season-gid').value = s.sheet_tab_gid || '';
  document.getElementById('setup-edit-season-modal').style.display = 'flex';
}

function closeSetupEditSeasonModal() {
  document.getElementById('setup-edit-season-modal').style.display = 'none';
}

async function saveSetupSeasonEdit() {
  const id = document.getElementById('setup-edit-season-id').value;
  const name = document.getElementById('setup-edit-season-name').value.trim();
  const status = document.getElementById('setup-edit-season-status').value;
  const gid = document.getElementById('setup-edit-season-gid').value.trim() || null;

  if (!name) { toast('Bitte einen Namen eingeben', 'error'); return; }

  try {
    const res = await authFetch(`${API_URL}/api/seasons/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, status, sheet_tab_gid: gid }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Speichern fehlgeschlagen');
    }
    toast('Saison gespeichert');
    closeSetupEditSeasonModal();
    const seasons = await authFetch(`${API_URL}/api/seasons`).then(r => r.json());
    allSetupSeasons = seasons;
    renderSetupSeasonsList(seasons);

    const activePlanned = seasons.filter(s => s.status !== 'archived').sort((a, b) => b.id - a.id);
    const sel = document.getElementById('schedule-season-select');
    if (sel) {
      sel.innerHTML = '<option value="">Wählen...</option>';
      activePlanned.forEach(s => {
        sel.innerHTML += `<option value="${s.id}">${escapeHtml(s.name)} (${s.status})</option>`;
      });
    }
  } catch (e) {
    toast(`Fehler: ${e.message}`, 'error');
  }
}

async function deleteSetupSeason(id) {
  const s = allSetupSeasons.find(x => x.id === id);
  if (!s) return;
  if (!confirm(`Saison "${s.name}" wirklich löschen? Alle zugehörigen Daten gehen verloren.`)) return;

  try {
    const res = await authFetch(`${API_URL}/api/seasons/${id}`, { method: 'DELETE' });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Löschen fehlgeschlagen');
    }
    toast(`Saison "${s.name}" gelöscht`);
    const seasons = await authFetch(`${API_URL}/api/seasons`).then(r => r.json());
    allSetupSeasons = seasons;
    renderSetupSeasonsList(seasons);
  } catch (e) {
    toast(`Fehler: ${e.message}`, 'error');
  }
}

// ---- Tab: Teilnehmer ----

let allParticipantTeams = [];
let lastSyncSourceMap = null;

async function loadParticipants() {
  const tbody = document.getElementById('participants-list');
  const countEl = document.getElementById('participant-count');
  tbody.innerHTML = '<tr><td colspan="6" style="text-align:center">Lade...</td></tr>';

  try {
    const res = await fetch(`${API_URL}/api/teams?participating=true`);
    allParticipantTeams = await res.json();

    const selectedIds = new Set(setupState.participants.map(p => p.team_id));
    if (selectedIds.size === 0) {
      allParticipantTeams.forEach(t => {
        selectedIds.add(t.id);
        setupState.participants.push({ team_id: t.id, team_name: t.name });
      });
    }

    if (!allParticipantTeams.length) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:var(--text-muted);padding:2rem 1rem">
        Keine Teams als "Dabei" markiert.<br>
        <span style="font-size:.85rem">Nutze <strong>🔄 Teams laden &amp; Sheet abgleichen</strong> oder <strong>👥 Teams verwalten</strong>.</span>
      </td></tr>`;
      if (countEl) countEl.textContent = '0 Teams';
      return;
    }

    renderParticipantsList(allParticipantTeams, selectedIds);
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="6" style="color:var(--danger)">Fehler: ${e.message}</td></tr>`;
  }
}

function renderParticipantsList(teams, selectedIds) {
  const tbody = document.getElementById('participants-list');
  const countEl = document.getElementById('participant-count');

  if (!selectedIds) {
    selectedIds = getSelectedParticipantIds();
  }

  const selected = teams.filter(t => selectedIds.has(t.id)).length;
  if (countEl) countEl.textContent = `${selected} von ${teams.length} Teams ausgewählt`;

  if (!teams.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted)">Keine Teams gefunden</td></tr>';
    return;
  }

  const seededValues = Object.entries(setupState.seededTeams)
    .filter(([, tid]) => tid !== null)
    .map(([key, tid]) => ({ key, tid }));

  tbody.innerHTML = teams.map(t => {
    const checked = selectedIds.has(t.id) ? 'checked' : '';
    const discord = t.discord_user
      ? t.discord_user.discord_username || t.discord_user.discord_id
      : '<span style="color:var(--text-muted)">–</span>';

    let status, statusStyle;
    if (t.discord_user && selectedIds.has(t.id)) {
      status = 'Ready';
      statusStyle = 'color:var(--success);font-weight:600';
    } else if (!t.discord_user && selectedIds.has(t.id)) {
      status = 'Kein Discord';
      statusStyle = 'color:var(--warning);font-weight:600';
    } else {
      status = '–';
      statusStyle = 'color:var(--text-muted)';
    }

    // Quelle badge
    let sourceLabel = '<span style="color:var(--text-muted)">–</span>';
    if (lastSyncSourceMap) {
      const src = lastSyncSourceMap[t.id];
      if (src === 'both') sourceLabel = '<span style="background:#dcfce7;color:#166534;padding:.15rem .5rem;border-radius:4px;font-size:.8rem">Beide</span>';
      else if (src === 'discord') sourceLabel = '<span style="background:#fff3cd;color:#856404;padding:.15rem .5rem;border-radius:4px;font-size:.8rem">Nur Discord</span>';
      else if (src === 'sheet') sourceLabel = '<span style="background:#dbeafe;color:#1e40af;padding:.15rem .5rem;border-radius:4px;font-size:.8rem">Sheet</span>';
    }

    // Setzplatz-Dropdown
    const currentSeed = Object.entries(setupState.seededTeams).find(([, tid]) => tid === t.id);
    const currentSeedKey = currentSeed ? currentSeed[0] : '';
    const isChecked = selectedIds.has(t.id);
    const seedOptions = [
      { value: '', label: '–' },
      { value: 'A', label: 'Gr. A (Pokalsieger)' },
      { value: 'B', label: 'Gr. B (Lucky Loser)' },
      { value: 'C', label: 'Gr. C (Loser Sieger)' },
    ];
    const seedSelect = `<select class="seed-select" data-team-id="${t.id}" onchange="updateSeedSelection(this)" ${!isChecked ? 'disabled' : ''} style="padding:.25rem .4rem;font-size:.8rem;min-width:140px">
      ${seedOptions.map(o => {
        const taken = o.value && setupState.seededTeams[o.value] !== null && setupState.seededTeams[o.value] !== t.id;
        return `<option value="${o.value}" ${o.value === currentSeedKey ? 'selected' : ''} ${taken ? 'disabled' : ''}>${o.label}</option>`;
      }).join('')}
    </select>`;

    return `<tr>
      <td><input type="checkbox" class="participant-check" data-team-id="${t.id}" data-team-name="${escapeHtml(t.name)}" ${checked} onchange="updateParticipantSelection()"></td>
      <td><strong>${escapeHtml(t.name)}</strong></td>
      <td>${sourceLabel}</td>
      <td>${seedSelect}</td>
      <td>${discord}</td>
      <td><span style="${statusStyle}">${status}</span></td>
    </tr>`;
  }).join('');
}

function filterParticipantsList() {
  const q = (document.getElementById('participants-search').value || '').toLowerCase().trim();
  const selectedIds = getSelectedParticipantIds();
  const filtered = q ? allParticipantTeams.filter(t => t.name.toLowerCase().includes(q)) : allParticipantTeams;
  renderParticipantsList(filtered, selectedIds);
}

function getSelectedParticipantIds() {
  const ids = new Set();
  document.querySelectorAll('.participant-check:checked').forEach(cb => {
    ids.add(parseInt(cb.dataset.teamId));
  });
  return ids;
}

function updateParticipantSelection() {
  const selectedIds = getSelectedParticipantIds();
  setupState.participants = [];
  document.querySelectorAll('.participant-check:checked').forEach(cb => {
    setupState.participants.push({
      team_id: parseInt(cb.dataset.teamId),
      team_name: cb.dataset.teamName,
    });
  });

  for (const key of Object.keys(setupState.seededTeams)) {
    if (setupState.seededTeams[key] !== null && !selectedIds.has(setupState.seededTeams[key])) {
      setupState.seededTeams[key] = null;
    }
  }

  const countEl = document.getElementById('participant-count');
  if (countEl) countEl.textContent = `${selectedIds.size} von ${allParticipantTeams.length} Teams ausgewählt`;

  renderParticipantsList(allParticipantTeams, selectedIds);
}

function toggleAllParticipants(checked) {
  document.querySelectorAll('.participant-check').forEach(cb => { cb.checked = checked; });
  updateParticipantSelection();
}

function updateSeedSelection(selectEl) {
  const teamId = parseInt(selectEl.dataset.teamId);
  const value = selectEl.value;

  for (const key of Object.keys(setupState.seededTeams)) {
    if (setupState.seededTeams[key] === teamId) setupState.seededTeams[key] = null;
  }
  if (value && ['A', 'B', 'C'].includes(value)) {
    setupState.seededTeams[value] = teamId;
  }

  const selectedIds = getSelectedParticipantIds();
  renderParticipantsList(allParticipantTeams, selectedIds);
}

// ---- Google Sheet Sync ----

async function syncWithSheet() {
  const seasonId = document.getElementById('participants-season-select').value;
  if (!seasonId) {
    toast('Bitte zuerst eine Saison wählen', 'error');
    return;
  }

  const btn = document.querySelector('button[onclick="syncWithSheet()"]');
  if (btn) { btn.disabled = true; btn.textContent = '⏳ Sync läuft...'; }

  try {
    const res = await authFetch(`${API_URL}/api/admin/sheet-sync?season_id=${seasonId}`, { method: 'POST' });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Sheet-Sync fehlgeschlagen');
    }
    const data = await res.json();

    // Banner anzeigen
    document.getElementById('sheet-sync-result').style.display = 'block';
    document.getElementById('sync-stat-matched').textContent = `✅ ${data.matched.length} Match`;
    document.getElementById('sync-stat-only-discord').textContent = `⚠️ ${data.only_discord.length} Nur Discord`;
    document.getElementById('sync-stat-only-sheet').textContent = `📋 ${data.only_sheet.length} Nur Sheet`;
    document.getElementById('sync-stat-created').textContent = `➕ ${data.created} neu angelegt`;
    document.getElementById('sync-stat-tab').textContent = `Saison: ${data.season_name}`;

    // Quellen-Map aufbauen
    lastSyncSourceMap = {};
    data.matched.forEach(t => { lastSyncSourceMap[t.team_id] = 'both'; });
    data.only_discord.forEach(t => { lastSyncSourceMap[t.team_id] = 'discord'; });
    data.only_sheet.forEach(t => { lastSyncSourceMap[t.team_id] = 'sheet'; });

    setupState.participants = [];
    await loadParticipants();

    toast(`Sheet-Sync: ${data.matched.length} Match, ${data.only_discord.length} Nur Discord, ${data.only_sheet.length} Sheet-only`);
  } catch (e) {
    toast(`Fehler: ${e.message}`, 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '🔄 Teams laden & Sheet abgleichen'; }
  }
}

// ---- Spielplan generieren ----

async function generateSeasonPlan() {
  const seasonId = document.getElementById('participants-season-select').value;
  if (!seasonId) {
    toast('Bitte zuerst eine Saison im Dropdown wählen', 'error');
    return;
  }

  const participants = setupState.participants;
  if (!participants.length) {
    toast('Keine Teilnehmer geladen. Bitte zuerst "Teams laden" klicken.', 'error');
    return;
  }

  const season = allSetupSeasons.find(s => String(s.id) === String(seasonId));
  const seasonName = season ? season.name : `Saison ${seasonId}`;
  const groupCount = Math.ceil(participants.length / 4);

  if (!confirm(`${participants.length} Teams in ${groupCount} Gruppen für "${seasonName}" einteilen und Spielplan generieren?`)) return;

  try {
    const teamIds = participants.map(p => p.team_id);
    const seededTeams = {};
    for (const [key, tid] of Object.entries(setupState.seededTeams)) {
      if (tid !== null && teamIds.includes(tid)) seededTeams[key] = tid;
    }

    const syncRes = await authFetch(`${API_URL}/api/seasons/${seasonId}/teams/sync`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ team_ids: teamIds, seeded_teams: seededTeams, generate_schedule: true }),
    });
    if (!syncRes.ok) {
      const err = await syncRes.json();
      throw new Error(err.detail || 'Spielplan konnte nicht generiert werden');
    }
    const result = await syncRes.json();

    // participant_count aktualisieren
    await authFetch(`${API_URL}/api/seasons/${seasonId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ participant_count: participants.length }),
    });

    toast(`✅ Spielplan generiert: ${result.groups?.length ?? '?'} Gruppen, ${result.added} Teams zugewiesen`);

    setupState.createdSeasonId = parseInt(seasonId);
    await initSaisonSetup();
    showSetupTab('tab-schedule');
    document.getElementById('schedule-season-select').value = seasonId;
    loadScheduleForSeason();
  } catch (e) {
    toast(`Fehler: ${e.message}`, 'error');
  }
}

// ---- Bulk-Import Modal ----

function openBulkImportModal() {
  document.getElementById('bulk-import-textarea').value = '';
  document.getElementById('bulk-import-result').style.display = 'none';
  document.getElementById('bulk-import-btn').disabled = false;
  document.getElementById('bulk-import-modal').style.display = 'flex';
  setTimeout(() => document.getElementById('bulk-import-textarea').focus(), 100);
}

function closeBulkImportModal() {
  document.getElementById('bulk-import-modal').style.display = 'none';
}

async function submitBulkImport() {
  const textarea = document.getElementById('bulk-import-textarea');
  const resultEl = document.getElementById('bulk-import-result');
  const btn = document.getElementById('bulk-import-btn');

  const lines = textarea.value.split('\n').map(l => l.trim()).filter(l => l.length > 0);
  if (!lines.length) { toast('Bitte mindestens einen Teamnamen eingeben', 'error'); return; }

  btn.disabled = true;
  btn.textContent = '⏳ Importiere...';

  try {
    const res = await authFetch(`${API_URL}/api/teams/bulk-register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ teams: lines }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Import fehlgeschlagen');
    }
    const data = await res.json();
    resultEl.style.display = 'block';
    resultEl.innerHTML = `<div style="padding:.75rem;background:var(--bg-elevated);border-radius:6px;font-size:.9rem">
      ✅ <strong>${data.created}</strong> neue Teams angelegt,
      <strong>${data.updated}</strong> bestehende als "Dabei" markiert.
      <br>Gesamt: <strong>${data.total}</strong> Teams verarbeitet.
    </div>`;
    toast(`Bulk-Import: ${data.created} neu, ${data.updated} aktualisiert`);
    setupState.participants = [];
    await loadParticipants();
  } catch (e) {
    resultEl.style.display = 'block';
    resultEl.innerHTML = `<div style="color:var(--danger);font-size:.9rem">❌ ${e.message}</div>`;
  } finally {
    btn.disabled = false;
    btn.textContent = '📥 Importieren';
  }
}

// ---- Teams verwalten Modal ----

let allManageTeams = [];

function openManageTeamsModal() {
  document.getElementById('manage-teams-search').value = '';
  document.getElementById('manage-teams-modal').style.display = 'flex';
  loadManageTeams();
}

function closeManageTeamsModal() {
  document.getElementById('manage-teams-modal').style.display = 'none';
  setupState.participants = [];
  loadParticipants();
}

async function loadManageTeams() {
  const tbody = document.getElementById('manage-teams-list');
  tbody.innerHTML = '<tr><td colspan="3" style="text-align:center">Lade...</td></tr>';

  try {
    const res = await fetch(`${API_URL}/api/teams`);
    allManageTeams = await res.json();
    renderManageTeamsList(allManageTeams);
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="3" style="color:var(--danger)">Fehler: ${e.message}</td></tr>`;
  }
}

function renderManageTeamsList(teams) {
  const tbody = document.getElementById('manage-teams-list');
  if (!teams.length) {
    tbody.innerHTML = '<tr><td colspan="3" style="text-align:center;color:var(--text-muted)">Keine Teams gefunden</td></tr>';
    return;
  }
  tbody.innerHTML = teams.map(t => {
    const discord = t.discord_user
      ? (t.discord_user.discord_username || t.discord_user.discord_id)
      : '<span style="color:var(--text-muted)">–</span>';
    return `<tr>
      <td style="text-align:center"><input type="checkbox" ${t.participating_next ? 'checked' : ''} onchange="toggleTeamParticipation(${t.id}, this.checked)"></td>
      <td>${escapeHtml(t.name)}</td>
      <td>${discord}</td>
    </tr>`;
  }).join('');
}

function filterManageTeamsList() {
  const q = (document.getElementById('manage-teams-search').value || '').toLowerCase().trim();
  const filtered = q ? allManageTeams.filter(t => t.name.toLowerCase().includes(q)) : allManageTeams;
  renderManageTeamsList(filtered);
}

async function toggleTeamParticipation(teamId, value) {
  try {
    const res = await authFetch(`${API_URL}/api/teams/${teamId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ participating_next: value }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Fehler beim Aktualisieren');
    }
    const team = allManageTeams.find(t => t.id === teamId);
    if (team) team.participating_next = value;
  } catch (e) {
    toast(`Fehler: ${e.message}`, 'error');
    loadManageTeams();
  }
}

// ---- Tab: Spielplan ----

async function loadScheduleForSeason() {
  const seasonId = document.getElementById('schedule-season-select').value;
  const container = document.getElementById('schedule-groups-list');
  if (!seasonId) { container.innerHTML = ''; return; }

  container.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:2rem">Lade...</div>';

  try {
    const res = await authFetch(`${API_URL}/api/seasons/${seasonId}/groups-with-teams`);
    const groups = await res.json();

    if (!groups.length) {
      container.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:2rem">Keine Gruppen gefunden</div>';
      return;
    }

    container.innerHTML = groups.map(g => {
      const matches = g.matches || [];
      const matchRows = matches.length
        ? matches.map(m => `
            <tr>
              <td>${m.matchday || '-'}</td>
              <td style="text-align:right">${m.home_team_name || m.home_team_id}</td>
              <td style="text-align:center;font-weight:600;color:var(--primary)">
                ${m.home_goals != null ? `${m.home_goals}:${m.away_goals}` : '–:–'}
              </td>
              <td>${m.away_team_name || m.away_team_id}</td>
              <td><span class="match-status ${m.status}">${m.status === 'played' ? '✅' : '🕐'}</span></td>
            </tr>`).join('')
        : '<tr><td colspan="5" style="color:var(--text-muted)">Kein Spielplan vorhanden</td></tr>';

      return `
        <div class="card">
          <h2>Gruppe ${g.name}</h2>
          <div style="margin-bottom:.75rem;display:flex;gap:.5rem;flex-wrap:wrap">
            ${(g.teams || []).map(t => `<span style="background:var(--bg-elevated);padding:.2rem .6rem;border-radius:4px;font-size:.85rem">${t.name}</span>`).join('')}
          </div>
          <table>
            <thead><tr><th>ST</th><th style="text-align:right">Heim</th><th style="text-align:center">Ergebnis</th><th>Gast</th><th>Status</th></tr></thead>
            <tbody>${matchRows}</tbody>
          </table>
        </div>`;
    }).join('');
  } catch (e) {
    container.innerHTML = `<div style="color:var(--danger);padding:1rem">Fehler: ${e.message}</div>`;
  }
}

async function generateScheduleForSeason() {
  const seasonId = document.getElementById('schedule-season-select').value;
  if (!seasonId) { toast('Bitte Saison wählen', 'error'); return; }
  if (!confirm('Spielplan für alle Gruppen dieser Saison generieren?')) return;

  try {
    const res = await authFetch(`${API_URL}/api/seasons/${seasonId}/groups`);
    const groups = await res.json();

    let ok = 0, fail = 0;
    for (const g of groups) {
      const r = await authFetch(`${API_URL}/api/groups/${g.id}/generate-schedule`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      r.ok ? ok++ : fail++;
    }

    toast(`Spielplan generiert: ${ok} Gruppen OK, ${fail} Fehler`);
    loadScheduleForSeason();
  } catch (e) {
    toast(`Fehler: ${e.message}`, 'error');
  }
}

// Enter-Taste im "Neue Saison"-Formular
document.addEventListener('keydown', function(e) {
  if (e.key === 'Enter') {
    const nameInput = document.getElementById('new-season-name');
    if (nameInput && document.activeElement === nameInput) {
      e.preventDefault();
      createNewSeason();
    }
  }
});
