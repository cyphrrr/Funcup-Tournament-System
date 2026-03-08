// admin/ko-phase.js — KO-Bracket Management

const KO_TAB_LABELS = { meister: 'Meisterrunde', lucky_loser: 'Lucky Loser', loser: 'Loser' };
const KO_ROUND_ORDER = ['runde_1', 'runde_2', 'runde_3', 'runde_4', 'viertelfinale', 'halbfinale', 'finale'];
const KO_ROUND_LABELS = { 'finale': '🏆 Finale', 'halbfinale': 'Halbfinale', 'viertelfinale': 'Viertelfinale', 'achtelfinale': 'Achtelfinale' };
let koBracketsCache = null;
let koActiveTab = 'meister';
let koSeasonTeams = [];

async function loadKOSeasons() {
  const seasons = await fetch(`${API_URL}/api/seasons`).then(r => r.json());
  const select = document.getElementById('ko-season');
  select.innerHTML = '<option value="">Wählen...</option>' +
    seasons.map(s => `<option value="${s.id}">${s.name}</option>`).join('');
}

async function loadKOStatus() {
  const seasonId = document.getElementById('ko-season').value;
  const statusArea = document.getElementById('ko-status-area');
  const manualArea = document.getElementById('ko-manual-area');
  const bracketsArea = document.getElementById('ko-brackets-area');

  manualArea.style.display = 'none';
  manualArea.innerHTML = '';
  bracketsArea.innerHTML = '';

  if (!seasonId) {
    statusArea.innerHTML = '';
    return;
  }

  const groups = await fetch(`${API_URL}/api/seasons/${seasonId}/groups-with-teams`).then(r => r.json());
  koSeasonTeams = [];
  groups.forEach(g => g.teams.forEach(t => {
    teamCache[t.id] = t.name;
    koSeasonTeams.push({ id: t.id, name: t.name });
  }));

  try {
    const status = await fetch(`${API_URL}/api/seasons/${seasonId}/ko-brackets/status`).then(r => r.json());

    let html = '<div style="display:flex;gap:1rem;margin-bottom:1rem;flex-wrap:wrap">';
    html += `<div class="stat" style="flex:1;min-width:150px">
      <div class="stat-value" style="font-size:1.2rem;color:${status.all_groups_completed ? 'var(--success)' : 'var(--warning)'}">
        ${status.all_groups_completed ? 'Ja' : 'Nein'}
      </div>
      <div class="stat-label">Gruppen abgeschlossen</div>
    </div>`;
    html += `<div class="stat" style="flex:1;min-width:150px">
      <div class="stat-value" style="font-size:1.2rem;color:${status.brackets_generated ? 'var(--success)' : 'var(--text-muted)'}">
        ${status.brackets_generated ? 'Ja' : 'Nein'}
      </div>
      <div class="stat-label">Brackets generiert</div>
    </div>`;
    html += '</div>';

    html += '<div style="display:flex;gap:.5rem;flex-wrap:wrap;margin-bottom:1.5rem">';
    if (!status.brackets_generated) {
      html += `<button class="btn btn-primary" onclick="previewKOBrackets()">👁️ Vorschau</button>`;
      html += `<button class="btn btn-primary" onclick="generateKOBrackets()">🤖 Automatisch generieren</button>`;
      html += `<button class="btn btn-secondary" onclick="showManualBuild()">🔧 Manuell aufbauen</button>`;
    } else {
      html += '</div>';
      html += '<div style="display:flex;gap:1rem;margin-bottom:1rem;flex-wrap:wrap">';
      for (const key of ['meister', 'lucky_loser', 'loser']) {
        const bs = status.brackets[key];
        if (!bs) continue;
        html += `<div class="stat" style="flex:1;min-width:150px">
          <div class="stat-value" style="font-size:1rem">${bs.matches_played}/${bs.matches_total}</div>
          <div class="stat-label">${KO_TAB_LABELS[key]} gespielt</div>
        </div>`;
      }
      html += '</div>';
      html += '<div style="display:flex;gap:.5rem;flex-wrap:wrap;margin-bottom:1.5rem">';
      html += `<button class="btn btn-danger" onclick="resetKOBrackets()">⚠️ Brackets zurücksetzen</button>`;
    }
    html += '</div>';

    statusArea.innerHTML = html;

    if (status.brackets_generated) {
      await loadKOBrackets(seasonId);
    }
  } catch (e) {
    statusArea.innerHTML = `<div class="card" style="color:var(--danger)">Fehler: ${e.message}</div>`;
  }
}

function showManualBuild() {
  const seasonId = document.getElementById('ko-season').value;
  const area = document.getElementById('ko-manual-area');
  area.style.display = 'block';

  let html = '<div style="display:flex;gap:1rem;flex-wrap:wrap">';
  for (const type of ['meister', 'lucky_loser', 'loser']) {
    html += `<div class="card" style="flex:1;min-width:200px;text-align:center">
      <h2>${KO_TAB_LABELS[type]}</h2>
      <div class="form-group" style="margin-bottom:.75rem">
        <label>Teamanzahl</label>
        <select id="manual-count-${type}">
          <option value="2">2</option>
          <option value="4">4</option>
          <option value="8" selected>8</option>
          <option value="16">16</option>
          <option value="32">32</option>
        </select>
      </div>
      <button class="btn btn-primary btn-sm" onclick="createEmptyBracket('${type}')">Gerüst erstellen</button>
    </div>`;
  }
  html += '</div>';
  area.innerHTML = html;
}

async function generateKOBrackets() {
  const seasonId = document.getElementById('ko-season').value;
  if (!seasonId) return;
  try {
    const res = await authFetch(`${API_URL}/api/seasons/${seasonId}/ko-brackets/generate`, { method: 'POST' });
    const data = await res.json();
    let msg = 'KO-Brackets generiert!';
    const counts = [];
    if (data.meister?.aufruecker_count > 0) counts.push(`${data.meister.aufruecker_count} Aufrücker (M)`);
    if (data.lucky_loser?.aufruecker_count > 0) counts.push(`${data.lucky_loser.aufruecker_count} Aufrücker (LL)`);
    if (data.loser?.aufruecker_count > 0) counts.push(`${data.loser.aufruecker_count} Aufrücker (L)`);
    if (counts.length > 0) msg += ' — ' + counts.join(', ');
    toast(msg);
    loadKOStatus();
  } catch (e) {
    toast('Fehler: ' + e.message, 'error');
  }
}

async function createEmptyBracket(bracketType) {
  const seasonId = document.getElementById('ko-season').value;
  if (!seasonId) return;
  const teamCount = parseInt(document.getElementById(`manual-count-${bracketType}`).value);
  try {
    await authFetch(`${API_URL}/api/seasons/${seasonId}/ko-brackets/create-empty`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bracket_type: bracketType, team_count: teamCount })
    });
    toast(`${KO_TAB_LABELS[bracketType]} Gerüst erstellt!`);
    loadKOStatus();
  } catch (e) {
    toast('Fehler: ' + e.message, 'error');
  }
}

async function resetKOBrackets() {
  if (!confirm('Alle KO-Brackets und Ergebnisse dieser Saison wirklich löschen?')) return;
  const seasonId = document.getElementById('ko-season').value;
  if (!seasonId) return;
  try {
    await authFetch(`${API_URL}/api/seasons/${seasonId}/ko-brackets/reset`, { method: 'POST' });
    toast('KO-Brackets zurückgesetzt!');
    koBracketsCache = null;
    koActiveTab = 'meister';
    loadKOStatus();
  } catch (e) {
    toast('Fehler: ' + e.message, 'error');
  }
}

async function previewKOBrackets() {
  const seasonId = document.getElementById('ko-season').value;
  const statusArea = document.getElementById('ko-status-area');
  if (!seasonId) return;
  try {
    const res = await authFetch(`${API_URL}/api/seasons/${seasonId}/ko-brackets/preview`);
    const preview = await res.json();
    renderKOPreview(preview, statusArea);
  } catch (e) {
    toast('Fehler: ' + e.message, 'error');
  }
}

function renderKOPreview(preview, container) {
  let html = '<div class="ko-preview-section">';
  html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem">';
  html += '<h2>KO-Bracket Vorschau</h2>';
  html += '<button class="btn btn-secondary btn-sm" onclick="loadKOStatus()">✕ Schließen</button>';
  html += '</div>';

  // Warning Banner wenn Gruppenphase nicht abgeschlossen
  if (preview.warning) {
    html += `<div style="background:color-mix(in srgb, var(--warning) 15%, var(--bg-section));border:1px solid var(--warning);border-radius:8px;padding:.75rem;margin-bottom:1rem;font-size:.85rem;color:var(--warning)">
      ⚠️ ${preview.warning}
    </div>`;
  }

  const teamNames = preview.team_names || {};

  for (const type of ['meister', 'lucky_loser', 'loser']) {
    const bracket = preview[type];
    if (!bracket) continue;

    html += '<div class="ko-preview-bracket">';
    html += `<h3>${KO_TAB_LABELS[type] || type} (${bracket.size} Teams, ${bracket.rounds} Runden)</h3>`;

    // Team pills with promoted badges
    html += '<div class="ko-preview-teams">';
    bracket.teams.forEach((teamId, idx) => {
      const name = teamNames[teamId] || '?';
      const isPromoted = bracket.aufruecker.includes(teamId);
      const badge = isPromoted ? ' <span class="ko-promoted-badge">↑ Aufrücker</span>' : '';
      html += `<div class="ko-team-pill">${name}${badge}</div>`;
    });
    html += '</div>';

    // Pairings
    html += '<div class="ko-preview-pairings">';
    html += '<div style="font-size:.8rem;color:var(--text-muted);margin-bottom:.5rem">Runde 1 Paarungen:</div>';
    bracket.pairings_r1.forEach(pair => {
      const homeName = teamNames[pair.home] || '?';
      const awayName = teamNames[pair.away] || '?';
      html += `<div>${homeName} vs ${awayName}</div>`;
    });
    html += '</div>';

    html += '</div>';
  }

  html += '</div>';
  container.innerHTML = html;
}

async function loadKOBrackets(seasonId) {
  const area = document.getElementById('ko-brackets-area');
  try {
    const res = await fetch(`${API_URL}/api/seasons/${seasonId}/ko-brackets`);
    if (!res.ok) throw new Error('Fehler beim Laden');
    koBracketsCache = await res.json();

    const bracketKeys = Object.keys(koBracketsCache.brackets).filter(k => koBracketsCache.brackets[k]);
    if (bracketKeys.length === 0) {
      area.innerHTML = '<div class="card"><em>Keine Brackets vorhanden</em></div>';
      return;
    }
    if (!koBracketsCache.brackets[koActiveTab]) koActiveTab = bracketKeys[0];

    let html = '<div class="tabs">';
    bracketKeys.forEach(key => {
      html += `<button class="tab ${key === koActiveTab ? 'active' : ''}" onclick="showKOTab('${key}')">${KO_TAB_LABELS[key] || key}</button>`;
    });
    html += '</div>';
    html += '<div id="ko-tab-content"></div>';
    area.innerHTML = html;

    renderKOBracket();
  } catch (e) {
    area.innerHTML = `<div class="card" style="color:var(--danger)">Fehler: ${e.message}</div>`;
  }
}

function showKOTab(type) {
  koActiveTab = type;
  document.querySelectorAll('#ko-brackets-area .tab').forEach(b => b.classList.remove('active'));
  const btn = document.querySelector(`#ko-brackets-area .tab[onclick="showKOTab('${type}')"]`);
  if (btn) btn.classList.add('active');
  renderKOBracket();
}

function koRoundLabel(key) {
  if (KO_ROUND_LABELS[key]) return KO_ROUND_LABELS[key];
  const m = key.match(/^runde_(\d+)$/);
  if (m) return `Runde ${m[1]}`;
  return key;
}

function koSortRounds(keys) {
  return [...keys].sort((a, b) => {
    const idxA = KO_ROUND_ORDER.indexOf(a);
    const idxB = KO_ROUND_ORDER.indexOf(b);
    return (idxA === -1 ? 999 : idxA) - (idxB === -1 ? 999 : idxB);
  });
}

function renderKOBracket() {
  const contentDiv = document.getElementById('ko-tab-content');
  if (!contentDiv || !koBracketsCache) return;

  const bracket = koBracketsCache.brackets[koActiveTab];
  if (!bracket) {
    contentDiv.innerHTML = '<div class="card"><em>Kein Bracket verfügbar</em></div>';
    return;
  }

  const assignedTeamIds = new Set();
  Object.values(bracket.rounds).forEach(matches => {
    matches.forEach(m => {
      if (m.home_team) assignedTeamIds.add(m.home_team.id);
      if (m.away_team) assignedTeamIds.add(m.away_team.id);
    });
  });

  const rounds = bracket.rounds;
  const sortedKeys = koSortRounds(Object.keys(rounds));

  let html = '<div class="ko-admin-bracket">';

  sortedKeys.forEach(roundKey => {
    html += `<div class="ko-admin-round">`;
    html += `<div class="ko-admin-round-header">${koRoundLabel(roundKey)}</div>`;

    rounds[roundKey].forEach(m => {
      if (m.is_bye) {
        const teamName = m.home_team ? m.home_team.name : '?';
        html += `<div class="ko-admin-match bye">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <span>${teamName} – Freilos</span>
            <span style="font-size:.7rem;color:var(--text-muted)">ID: ${m.match_id}</span>
          </div>
        </div>`;
        return;
      }

      const homeName = m.home_team ? m.home_team.name : '?';
      const awayName = m.away_team ? m.away_team.name : '?';
      const hasResult = m.home_goals !== null && m.away_goals !== null;
      const hasBothTeams = m.home_team && m.away_team;
      const statusClass = hasResult ? 'played' : 'pending';

      if (!m.home_team && !m.away_team) {
        html += `<div class="ko-admin-match pending" style="opacity:.5">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <span>? vs ?</span>
            <span style="font-size:.7rem;color:var(--text-muted)">ID: ${m.match_id}</span>
          </div>`;

        const availableTeams = koSeasonTeams.filter(t => !assignedTeamIds.has(t.id));
        const opts = availableTeams.map(t => `<option value="${t.id}">${t.name}</option>`).join('');
        html += `<div style="margin-top:.5rem;font-size:.8rem">
          <div style="display:flex;gap:.25rem;align-items:center;margin-bottom:.25rem">
            <span style="width:35px">Heim:</span>
            <select id="ko-set-home-${m.match_id}" style="flex:1;font-size:.8rem"><option value="">Wählen...</option>${opts}</select>
            <button class="btn btn-sm btn-secondary" onclick="setKOTeam(${m.match_id},'home')">Setzen</button>
          </div>
          <div style="display:flex;gap:.25rem;align-items:center">
            <span style="width:35px">Gast:</span>
            <select id="ko-set-away-${m.match_id}" style="flex:1;font-size:.8rem"><option value="">Wählen...</option>${opts}</select>
            <button class="btn btn-sm btn-secondary" onclick="setKOTeam(${m.match_id},'away')">Setzen</button>
            <button class="btn btn-sm" style="font-size:.7rem" onclick="setKOBye(${m.match_id})">Bye</button>
          </div>
        </div>`;
        html += '</div>';
        return;
      }

      html += `<div class="ko-admin-match ${statusClass}">`;
      html += `<div style="display:flex;justify-content:space-between;align-items:center">
        <div>
          <strong>${homeName}</strong> vs <strong>${awayName}</strong>
          ${hasResult ? `<span style="margin-left:.5rem;font-weight:700">${m.home_goals}:${m.away_goals}</span>` : ''}
          ${m.winner_id ? `<span style="font-size:.7rem;color:var(--success);margin-left:.25rem">✓</span>` : ''}
        </div>
        <div style="display:flex;gap:.25rem;align-items:center">
          <span style="font-size:.7rem;color:var(--text-muted)">ID: ${m.match_id}</span>
          ${hasBothTeams && !hasResult ? `<button class="btn btn-sm btn-secondary" onclick="editKOMatch(${m.match_id})">Bearbeiten</button>` : ''}
        </div>
      </div>`;

      if (!m.home_team || !m.away_team) {
        const availableTeams = koSeasonTeams.filter(t => !assignedTeamIds.has(t.id));
        const opts = availableTeams.map(t => `<option value="${t.id}">${t.name}</option>`).join('');
        const missingSlot = !m.home_team ? 'home' : 'away';
        const label = missingSlot === 'home' ? 'Heim' : 'Gast';
        html += `<div style="margin-top:.5rem;display:flex;gap:.25rem;align-items:center;font-size:.8rem">
          <span>${label}:</span>
          <select id="ko-set-${missingSlot}-${m.match_id}" style="flex:1;font-size:.8rem"><option value="">Wählen...</option>${opts}</select>
          <button class="btn btn-sm btn-secondary" onclick="setKOTeam(${m.match_id},'${missingSlot}')">Setzen</button>
        </div>`;
      }

      html += `<div id="ko-edit-${m.match_id}"></div>`;
      html += '</div>';
    });

    html += '</div>';
  });

  html += '</div>';
  contentDiv.innerHTML = html;
}

function editKOMatch(matchId) {
  const editDiv = document.getElementById(`ko-edit-${matchId}`);
  if (!editDiv) return;

  if (editDiv.innerHTML) {
    editDiv.innerHTML = '';
    return;
  }

  const bracket = koBracketsCache.brackets[koActiveTab];
  let match = null;
  for (const rounds of Object.values(bracket.rounds)) {
    match = rounds.find(m => m.match_id === matchId);
    if (match) break;
  }
  if (!match) return;

  const homeName = match.home_team ? match.home_team.name : '?';
  const awayName = match.away_team ? match.away_team.name : '?';

  editDiv.innerHTML = `<div class="ko-edit-form">
    <div style="display:flex;gap:.5rem;align-items:center;flex-wrap:wrap">
      <div class="form-group" style="flex:0 0 70px">
        <label>Heim</label>
        <input type="number" min="0" id="ko-home-${matchId}" value="${match.home_goals ?? ''}" placeholder="-">
      </div>
      <div class="form-group" style="flex:0 0 70px">
        <label>Gast</label>
        <input type="number" min="0" id="ko-away-${matchId}" value="${match.away_goals ?? ''}" placeholder="-">
      </div>
      <div class="form-group" style="flex:1;min-width:120px">
        <label>Sieger (bei Unentschieden Pflicht)</label>
        <select id="ko-winner-${matchId}">
          <option value="">Automatisch</option>
          ${match.home_team ? `<option value="${match.home_team.id}">${homeName}</option>` : ''}
          ${match.away_team ? `<option value="${match.away_team.id}">${awayName}</option>` : ''}
        </select>
      </div>
      <button class="btn btn-success btn-sm" onclick="saveKOMatch(${matchId})" style="align-self:flex-end;margin-bottom:2px">Speichern</button>
    </div>
  </div>`;
}

async function saveKOMatch(matchId) {
  const homeEl = document.getElementById(`ko-home-${matchId}`);
  const awayEl = document.getElementById(`ko-away-${matchId}`);
  const winnerEl = document.getElementById(`ko-winner-${matchId}`);

  const home = homeEl.value;
  const away = awayEl.value;

  if (home === '' || away === '') {
    toast('Bitte beide Ergebnisse eingeben', 'error');
    return;
  }

  const body = {
    home_goals: parseInt(home),
    away_goals: parseInt(away)
  };

  if (winnerEl && winnerEl.value) {
    body.winner_id = parseInt(winnerEl.value);
  } else if (home === away) {
    toast('Bei Unentschieden muss ein Sieger gewählt werden', 'error');
    return;
  }

  try {
    await authFetch(`${API_URL}/api/ko-matches/${matchId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    toast('Ergebnis gespeichert');
    loadKOStatus();
  } catch (e) {
    toast('Fehler: ' + e.message, 'error');
  }
}

async function setKOTeam(matchId, slot) {
  const select = document.getElementById(`ko-set-${slot}-${matchId}`);
  const teamId = select ? parseInt(select.value) : null;
  if (!teamId) { toast('Bitte Team wählen', 'error'); return; }
  try {
    await authFetch(`${API_URL}/api/ko-matches/${matchId}/set-team`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ slot, team_id: teamId })
    });
    toast('Team gesetzt!');
    loadKOStatus();
  } catch (e) {
    toast('Fehler: ' + e.message, 'error');
  }
}

async function setKOBye(matchId) {
  const homeSelect = document.getElementById(`ko-set-home-${matchId}`);
  const teamId = homeSelect ? parseInt(homeSelect.value) : null;
  if (!teamId) { toast('Bitte erst Heim-Team wählen', 'error'); return; }

  try {
    await authFetch(`${API_URL}/api/ko-matches/${matchId}/set-bye`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ team_id: teamId })
    });
    toast('Freilos gesetzt!');
    loadKOStatus();
  } catch (e) {
    toast('Fehler: ' + e.message, 'error');
  }
}
