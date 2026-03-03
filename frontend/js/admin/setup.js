// admin/setup.js — Saison-Setup Wizard (Tabs 1-4)

const setupState = {
  participants: [],
  manualTeamSelected: null,
  drawGroups: null,
  createdSeasonId: null,
  seededTeams: { A: null, B: null, C: null },
};

function showSetupTab(tabId) {
  document.querySelectorAll('.setup-tab').forEach(t => t.style.display = 'none');
  document.querySelectorAll('.tab[data-tab]').forEach(t => t.classList.remove('active'));
  document.getElementById(tabId).style.display = 'block';
  document.querySelector(`.tab[data-tab="${tabId}"]`).classList.add('active');
}

async function initSaisonSetup() {
  try {
    const seasons = await authFetch(`${API_URL}/api/seasons`).then(r => r.json());
    const activePlanned = seasons.filter(s => s.status !== 'archived').sort((a, b) => b.id - a.id);

    ['schedule-season-select', 'import-season-select'].forEach(id => {
      const sel = document.getElementById(id);
      sel.innerHTML = '<option value="">Wählen...</option>';
      activePlanned.forEach(s => {
        sel.innerHTML += `<option value="${s.id}">${s.name} (${s.status})</option>`;
      });
    });
  } catch (e) {
    console.error('Fehler beim Laden der Saisons:', e);
  }
}

// ---- Tab 1: Teilnehmer ----

let allParticipantTeams = [];

async function loadParticipants() {
  const tbody = document.getElementById('participants-list');
  const countEl = document.getElementById('participant-count');
  tbody.innerHTML = '<tr><td colspan="5" style="text-align:center">Lade...</td></tr>';

  try {
    const res = await fetch(`${API_URL}/api/teams`);
    allParticipantTeams = await res.json();

    // Vorauswahl: Teams mit participating_next ODER in geplanter Saison
    const selectedIds = new Set(setupState.participants.map(p => p.team_id));
    if (selectedIds.size === 0) {
      allParticipantTeams.forEach(t => {
        const inPlanned = (t.seasons || []).some(s => s.status === 'planned');
        if (t.participating_next || inPlanned) {
          selectedIds.add(t.id);
        }
      });
      // setupState synchron befüllen
      allParticipantTeams.forEach(t => {
        if (selectedIds.has(t.id)) {
          setupState.participants.push({ team_id: t.id, team_name: t.name });
        }
      });
    }

    renderParticipantsList(allParticipantTeams, selectedIds);
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="5" style="color:var(--danger)">Fehler: ${e.message}</td></tr>`;
  }
}

function renderParticipantsList(teams, selectedIds) {
  const tbody = document.getElementById('participants-list');
  const countEl = document.getElementById('participant-count');

  if (!selectedIds) {
    selectedIds = getSelectedParticipantIds();
  }

  const selected = teams.filter(t => selectedIds.has(t.id)).length;
  countEl.textContent = `${selected} von ${teams.length} Teams ausgewählt`;

  if (!teams.length) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--muted)">Keine Teams gefunden</td></tr>';
    return;
  }

  // Bestimme welche Setzplätze vergeben sind
  const seededValues = Object.entries(setupState.seededTeams)
    .filter(([, tid]) => tid !== null)
    .map(([key, tid]) => ({ key, tid }));

  tbody.innerHTML = teams.map(t => {
    const checked = selectedIds.has(t.id) ? 'checked' : '';
    const discord = t.discord_user
      ? t.discord_user.discord_username || t.discord_user.discord_id
      : '<span style="color:var(--muted)">–</span>';

    let status, statusStyle;
    if (t.discord_user && selectedIds.has(t.id)) {
      status = 'Ready';
      statusStyle = 'color:var(--success);font-weight:600';
    } else if (!t.discord_user && selectedIds.has(t.id)) {
      status = 'Kein Discord';
      statusStyle = 'color:var(--warning);font-weight:600';
    } else {
      status = '–';
      statusStyle = 'color:var(--muted)';
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

  // Setzplätze für abgewählte Teams entfernen
  for (const key of Object.keys(setupState.seededTeams)) {
    if (setupState.seededTeams[key] !== null && !selectedIds.has(setupState.seededTeams[key])) {
      setupState.seededTeams[key] = null;
    }
  }

  const countEl = document.getElementById('participant-count');
  countEl.textContent = `${selectedIds.size} von ${allParticipantTeams.length} Teams ausgewählt`;

  // Seed-Dropdowns aktualisieren (disabled-Status)
  renderParticipantsList(allParticipantTeams, selectedIds);
}

function toggleAllParticipants(checked) {
  document.querySelectorAll('.participant-check').forEach(cb => {
    cb.checked = checked;
  });
  updateParticipantSelection();
}

function updateSeedSelection(selectEl) {
  const teamId = parseInt(selectEl.dataset.teamId);
  const value = selectEl.value;

  // Alten Setzplatz für dieses Team entfernen
  for (const key of Object.keys(setupState.seededTeams)) {
    if (setupState.seededTeams[key] === teamId) {
      setupState.seededTeams[key] = null;
    }
  }

  // Neuen Setzplatz setzen
  if (value && ['A', 'B', 'C'].includes(value)) {
    setupState.seededTeams[value] = teamId;
  }

  // Dropdowns neu rendern um disabled-Status zu aktualisieren
  const selectedIds = getSelectedParticipantIds();
  renderParticipantsList(allParticipantTeams, selectedIds);
}


async function finalizeTeams() {
  if (!setupState.participants.length) {
    toast('Bitte zuerst Teams laden und auswählen (Tab 1)', 'error');
    return;
  }

  try {
    // 1. Geplante Saison suchen
    const seasonsRes = await authFetch(`${API_URL}/api/seasons`);
    const seasons = await seasonsRes.json();
    let season = seasons.find(s => s.status === 'planned');

    // 2. Falls keine planned-Saison: neue erstellen
    if (!season) {
      const name = prompt('Wie soll die neue Saison heißen?');
      if (!name) return;

      const createRes = await authFetch(`${API_URL}/api/seasons`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          participant_count: setupState.participants.length,
          group_count: Math.ceil(setupState.participants.length / 4)
        })
      });
      if (!createRes.ok) {
        const err = await createRes.json();
        throw new Error(err.detail || 'Saison konnte nicht erstellt werden');
      }
      season = await createRes.json();
    }

    // 3. Confirm
    const teamCount = setupState.participants.length;
    if (!confirm(`${teamCount} Teams in Saison "${season.name}" synchronisieren und Spielplan generieren?`)) return;

    // 4. Sync aufrufen
    const teamIds = setupState.participants.map(p => p.team_id);
    const seededTeams = {};
    for (const [key, tid] of Object.entries(setupState.seededTeams)) {
      if (tid !== null && teamIds.includes(tid)) {
        seededTeams[key] = tid;
      }
    }

    const syncRes = await authFetch(`${API_URL}/api/seasons/${season.id}/teams/sync`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        team_ids: teamIds,
        seeded_teams: seededTeams,
        generate_schedule: true
      })
    });

    if (!syncRes.ok) {
      const err = await syncRes.json();
      throw new Error(err.detail || 'Sync fehlgeschlagen');
    }

    const result = await syncRes.json();
    toast(`Saison "${season.name}" — ${result.groups.length} Gruppen, +${result.added} / -${result.removed} Teams`);

    // 5. Wechsel zu Tab 3
    setupState.createdSeasonId = season.id;
    await initSaisonSetup();
    showSetupTab('tab-schedule');
    document.getElementById('schedule-season-select').value = season.id;
    loadScheduleForSeason();

  } catch (e) {
    toast(`Fehler: ${e.message}`, 'error');
  }
}


// ---- Tab 2: Auslosung ----

function updateDrawPreview() {
  const groups = parseInt(document.getElementById('draw-group-count').value) || 0;
  const tpg = parseInt(document.getElementById('draw-teams-per-group').value) || 0;
  const total = groups * tpg;
  const participants = setupState.participants.filter(p => p.team_id);
  const previewEl = document.getElementById('draw-preview');

  previewEl.innerHTML = `
    <strong>Konfiguration:</strong> ${groups} Gruppen × ${tpg} Teams = <strong>${total} Plätze</strong><br>
    <strong>Teilnehmer mit Team:</strong> ${participants.length}<br>
    ${participants.length > total ? `<span style="color:var(--danger)">⚠️ Zu viele Teilnehmer für diese Konfiguration!</span>` : ''}
    ${participants.length < total ? `<span style="color:var(--warning)">ℹ️ ${total - participants.length} Platz/Plätze bleiben leer</span>` : ''}
    ${participants.length === total ? `<span style="color:var(--success)">✅ Passt genau!</span>` : ''}
  `;
}

function previewDraw() {
  const groups = parseInt(document.getElementById('draw-group-count').value);
  const tpg = parseInt(document.getElementById('draw-teams-per-group').value);
  const participants = setupState.participants.filter(p => p.team_id);

  if (!participants.length) {
    toast('Bitte zuerst Teilnehmer laden (Tab 1)', 'error');
    return;
  }

  const shuffled = [...participants].sort(() => Math.random() - 0.5);
  const groupNames = 'ABCDEFGHIJKLMNOP'.split('');

  setupState.drawGroups = Array.from({ length: groups }, (_, i) => ({
    name: groupNames[i],
    teams: shuffled.slice(i * tpg, (i + 1) * tpg),
  }));

  renderDrawResult();
  document.getElementById('draw-result').style.display = 'block';
}

function renderDrawResult() {
  const grid = document.getElementById('draw-result-grid');
  grid.innerHTML = setupState.drawGroups.map(g => `
    <div style="background:var(--accent);border-radius:8px;padding:.75rem;border:1px solid var(--border)">
      <strong style="font-size:1rem;color:var(--primary)">Gruppe ${g.name}</strong>
      <div style="margin-top:.5rem">
        ${g.teams.map(t => `<div style="padding:.25rem 0;font-size:.85rem;border-bottom:1px solid var(--border)">${t.team_name}</div>`).join('')}
        ${g.teams.length === 0 ? '<em style="color:var(--muted);font-size:.8rem">Leer</em>' : ''}
      </div>
    </div>
  `).join('');
}

async function executeDraw() {
  const name = document.getElementById('draw-season-name').value.trim();
  if (!name) { toast('Bitte Saison-Name eingeben', 'error'); return; }

  if (!setupState.drawGroups) {
    previewDraw();
    if (!setupState.drawGroups) return;
  }

  if (!confirm(`Saison "${name}" mit ${setupState.drawGroups.length} Gruppen erstellen und Spielplan generieren?`)) return;

  try {
    const totalTeams = setupState.drawGroups.reduce((acc, g) => acc + g.teams.length, 0);
    const seasonRes = await authFetch(`${API_URL}/api/seasons`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name,
        participant_count: totalTeams,
        status: 'planned',
        group_count: setupState.drawGroups.length,
      })
    });

    if (!seasonRes.ok) {
      const err = await seasonRes.json();
      throw new Error(err.detail || 'Saison konnte nicht erstellt werden');
    }

    const season = await seasonRes.json();
    setupState.createdSeasonId = season.id;

    const groupsRes = await authFetch(`${API_URL}/api/seasons/${season.id}/groups`);
    const groups = await groupsRes.json();

    const groupMap = {};
    groups.forEach(g => { groupMap[g.name] = g.id; });

    let assignErrors = 0;
    for (const drawGroup of setupState.drawGroups) {
      const groupId = groupMap[drawGroup.name];
      if (!groupId) { console.warn(`Gruppe ${drawGroup.name} nicht gefunden`); continue; }

      for (const participant of drawGroup.teams) {
        const assignRes = await authFetch(`${API_URL}/api/seasons/${season.id}/teams`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            team_id: participant.team_id,
            group_id: groupId,
          })
        });
        if (!assignRes.ok) {
          console.warn(`Team ${participant.team_name} konnte nicht zugewiesen werden`);
          assignErrors++;
        }
      }

      await authFetch(`${API_URL}/api/groups/${groupId}/generate-schedule`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
    }

    if (assignErrors > 0) {
      toast(`Saison erstellt, aber ${assignErrors} Teams konnten nicht zugewiesen werden`, 'error');
    } else {
      toast(`✅ Saison "${name}" erfolgreich erstellt!`);
    }

    await initSaisonSetup();
    showSetupTab('tab-schedule');
    document.getElementById('schedule-season-select').value = season.id;
    loadScheduleForSeason();

  } catch (e) {
    toast(`Fehler: ${e.message}`, 'error');
  }
}

// ---- Tab 3: Spielplan ----

async function loadScheduleForSeason() {
  const seasonId = document.getElementById('schedule-season-select').value;
  const container = document.getElementById('schedule-groups-list');
  if (!seasonId) { container.innerHTML = ''; return; }

  container.innerHTML = '<div style="text-align:center;color:var(--muted);padding:2rem">Lade...</div>';

  try {
    const res = await authFetch(`${API_URL}/api/seasons/${seasonId}/groups-with-teams`);
    const groups = await res.json();

    if (!groups.length) {
      container.innerHTML = '<div style="text-align:center;color:var(--muted);padding:2rem">Keine Gruppen gefunden</div>';
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
        : '<tr><td colspan="5" style="color:var(--muted)">Kein Spielplan vorhanden</td></tr>';

      return `
        <div class="card">
          <h2>Gruppe ${g.name}</h2>
          <div style="margin-bottom:.75rem;display:flex;gap:.5rem;flex-wrap:wrap">
            ${(g.teams || []).map(t => `<span style="background:var(--accent);padding:.2rem .6rem;border-radius:4px;font-size:.85rem">${t.name}</span>`).join('')}
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
        body: JSON.stringify({})
      });
      r.ok ? ok++ : fail++;
    }

    toast(`Spielplan generiert: ${ok} Gruppen OK, ${fail} Fehler`);
    loadScheduleForSeason();
  } catch (e) {
    toast(`Fehler: ${e.message}`, 'error');
  }
}

// ---- Tab 4: Ergebnis-Import ----

function validateImportJson() {
  const input = document.getElementById('import-json-input').value.trim();
  const resultEl = document.getElementById('import-validation-result');

  try {
    const data = JSON.parse(input);
    if (!Array.isArray(data)) throw new Error('Muss ein JSON-Array sein');
    if (!data.length) throw new Error('Array ist leer');

    const required = ['Heim', 'Gast', 'Heimtore', 'Gasttore'];
    const missing = required.filter(k => !(k in data[0]));
    if (missing.length) throw new Error(`Fehlende Felder: ${missing.join(', ')}`);

    resultEl.innerHTML = `
      <div style="background:#dcfce7;padding:.75rem;border-radius:6px;color:#166534">
        ✅ JSON valide – <strong>${data.length} Spiele</strong> gefunden<br>
        Saison: ${data[0].Saison || 'nicht angegeben'} | Spieltag: ${data[0].Spieltag || 'nicht angegeben'}
      </div>`;
    return data;
  } catch (e) {
    resultEl.innerHTML = `<div style="background:#fee2e2;padding:.75rem;border-radius:6px;color:#991b1b">❌ ${e.message}</div>`;
    return null;
  }
}

async function executeImport() {
  const seasonId = document.getElementById('import-season-select').value;
  const matchday = document.getElementById('import-matchday-select').value;

  if (!seasonId) { toast('Bitte Saison wählen', 'error'); return; }

  const data = validateImportJson();
  if (!data) return;

  const resultCard = document.getElementById('import-result-card');
  const resultDetail = document.getElementById('import-result-detail');
  resultCard.style.display = 'none';

  try {
    const groupsRes = await authFetch(`${API_URL}/api/seasons/${seasonId}/groups-with-teams`);
    const groups = await groupsRes.json();

    const matchIndex = {};
    for (const g of groups) {
      for (const m of (g.matches || [])) {
        const home = (m.home_team_name || '').toLowerCase().trim();
        const away = (m.away_team_name || '').toLowerCase().trim();
        if (home && away) {
          matchIndex[`${home}|${away}`] = m.id;
          matchIndex[`${away}|${home}`] = { id: m.id, swapped: true };
        }
      }
    }

    let ok = 0, notFound = [];

    for (const spiel of data) {
      const heimNorm = (spiel.Heim || '').toLowerCase().trim();
      const gastNorm = (spiel.Gast || '').toLowerCase().trim();
      const heimTore = parseInt(spiel.Heimtore);
      const gastTore = parseInt(spiel.Gasttore);

      const key = `${heimNorm}|${gastNorm}`;
      const match = matchIndex[key];

      if (!match) {
        notFound.push(`${spiel.Heim} vs ${spiel.Gast}`);
        continue;
      }

      const matchId = typeof match === 'object' ? match.id : match;
      const swapped = typeof match === 'object' && match.swapped;

      const payload = swapped
        ? { home_goals: gastTore, away_goals: heimTore }
        : { home_goals: heimTore, away_goals: gastTore };

      const res = await authFetch(`${API_URL}/api/matches/${matchId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...payload, status: 'played' })
      });

      if (res.ok) ok++;
      else notFound.push(`${spiel.Heim} vs ${spiel.Gast} (API-Fehler)`);
    }

    resultCard.style.display = 'block';
    resultDetail.innerHTML = `
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;margin-bottom:1rem">
        <div class="stat"><div class="stat-value" style="color:var(--success)">${ok}</div><div class="stat-label">Importiert</div></div>
        <div class="stat"><div class="stat-value" style="color:var(--danger)">${notFound.length}</div><div class="stat-label">Nicht gefunden</div></div>
        <div class="stat"><div class="stat-value">${data.length}</div><div class="stat-label">Gesamt</div></div>
      </div>
      ${notFound.length ? `
        <div style="background:#fee2e2;border-radius:6px;padding:.75rem">
          <strong style="color:#991b1b">Nicht gefundene Spiele:</strong>
          <ul style="margin:.5rem 0 0;padding-left:1.25rem;font-size:.85rem">
            ${notFound.map(n => `<li>${n}</li>`).join('')}
          </ul>
        </div>` : ''}
    `;

    toast(`Import: ${ok}/${data.length} Ergebnisse eingetragen`);
    loadScheduleForSeason();

  } catch (e) {
    toast(`Fehler: ${e.message}`, 'error');
  }
}
