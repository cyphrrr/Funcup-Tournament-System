// admin/ergebnisse.js — Match-Laden/Speichern, Match Inserter

let teamCache = {};
let groupsCache = null;
let currentSeason = null;

async function loadMatchSeasons() {
  const seasons = await fetch(`${API_URL}/api/seasons`).then(r => r.json());
  const select = document.getElementById('match-season');
  select.innerHTML = '<option value="">Wählen...</option>' +
    seasons.map(s => `<option value="${s.id}">${s.name}</option>`).join('');
}

async function loadMatchesForSeason() {
  const seasonId = document.getElementById('match-season').value;
  if (!seasonId) {
    document.getElementById('matches-list').innerHTML = '';
    return;
  }
  currentSeason = seasonId;

  const groups = await fetch(`${API_URL}/api/seasons/${seasonId}/groups-with-teams`).then(r => r.json());
  groups.forEach(g => g.teams.forEach(t => teamCache[t.id] = t.name));
  groupsCache = { seasonId, groups };

  loadMatchesForPhase();
}

async function loadMatchesForPhase() {
  const seasonId = document.getElementById('match-season').value;
  const phase = document.getElementById('match-phase').value;
  if (!seasonId) return;

  const container = document.getElementById('matches-list');
  container.innerHTML = '<em>Lade...</em>';

  if (phase === 'group') {
    await loadGroupMatches(seasonId, container);
  }
}

async function loadGroupMatches(seasonId, container) {
  const groups = (groupsCache && groupsCache.seasonId === seasonId)
    ? groupsCache.groups
    : await fetch(`${API_URL}/api/seasons/${seasonId}/groups-with-teams`).then(r => r.json());

  let html = '';
  for (const g of groups) {
    if (g.matches.length === 0) continue;
    html += `<div class="card"><h2>Gruppe ${g.group.name}</h2>`;

    for (const m of g.matches) {
      const homeName = teamCache[m.home_team_id] || `Team ${m.home_team_id}`;
      const awayName = teamCache[m.away_team_id] || `Team ${m.away_team_id}`;
      const homeGoals = m.home_goals ?? '';
      const awayGoals = m.away_goals ?? '';

      const matchdayLabel = m.matchday ? `ST ${m.matchday}` : '';
      const ingameWeek = m.ingame_week || '';

      html += `
        <div class="match-card">
          <div class="match-header">
            <div class="match-teams">
              <span class="match-team">${homeName}</span>
              <span class="match-vs">vs</span>
              <span class="match-team">${awayName}</span>
            </div>
            <div style="display:flex;gap:.5rem;align-items:center">
              ${matchdayLabel ? `<span style="font-size:.75rem;color:var(--primary);font-weight:600" title="Spieltag">${matchdayLabel}</span>` : ''}
              <span style="font-size:.75rem;color:var(--text-muted)" title="Match-ID für News">ID: ${m.id}</span>
              <span class="match-status ${m.status}">${m.status}</span>
            </div>
          </div>
          <div class="match-score">
            <input type="number" min="0" id="home-${m.id}" value="${homeGoals}" placeholder="-" style="width:50px">
            <span>:</span>
            <input type="number" min="0" id="away-${m.id}" value="${awayGoals}" placeholder="-" style="width:50px">
            <input type="number" min="1" id="week-${m.id}" value="${ingameWeek}" placeholder="W" title="Ingame Woche" style="width:50px;margin-left:.5rem;font-size:.85rem">
          </div>
        </div>`;
    }
    html += '</div>';
  }

  if (html) {
    const saveAllBtn = `
      <div style="display:flex;justify-content:flex-end;margin-bottom:1rem">
        <button class="btn btn-success" onclick="saveAllGroupMatches()" style="font-size:1rem;padding:.6rem 1.5rem">
          💾 Alle Ergebnisse speichern
        </button>
      </div>`;
    container.innerHTML = saveAllBtn + html;
  } else {
    container.innerHTML = '<div class="card"><em>Keine Matches gefunden. Erst Spielplan generieren!</em></div>';
  }
}

async function saveGroupMatch(matchId) {
  const home = document.getElementById(`home-${matchId}`).value;
  const away = document.getElementById(`away-${matchId}`).value;
  const week = document.getElementById(`week-${matchId}`).value;

  if (home === '' || away === '') {
    toast('Bitte beide Ergebnisse eingeben', 'error');
    return;
  }

  try {
    const body = {
      home_goals: parseInt(home),
      away_goals: parseInt(away)
    };

    if (week !== '') {
      body.ingame_week = parseInt(week);
    }

    await authFetch(`${API_URL}/api/matches/${matchId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    toast('Ergebnis gespeichert!');
    loadMatchesForPhase();
  } catch (e) {
    toast('Fehler: ' + e.message, 'error');
  }
}

async function saveAllGroupMatches() {
  const matchCards = document.querySelectorAll('#matches-list .match-card');
  const updates = [];

  matchCards.forEach(card => {
    const homeInput = card.querySelector('input[id^="home-"]');
    if (!homeInput) return;
    const matchId = parseInt(homeInput.id.replace('home-', ''));
    const awayInput = card.querySelector(`#away-${matchId}`);
    const weekInput = card.querySelector(`#week-${matchId}`);

    const homeVal = homeInput.value;
    const awayVal = awayInput.value;

    if (homeVal !== '' && awayVal !== '') {
      const item = {
        match_id: matchId,
        home_goals: parseInt(homeVal),
        away_goals: parseInt(awayVal)
      };
      if (weekInput && weekInput.value !== '') {
        item.ingame_week = parseInt(weekInput.value);
      }
      updates.push(item);
    }
  });

  if (updates.length === 0) {
    toast('Keine Ergebnisse zum Speichern gefunden', 'error');
    return;
  }

  try {
    const res = await authFetch(`${API_URL}/api/matches/bulk-update`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ matches: updates })
    });
    const result = await res.json();
    toast(`✅ ${result.updated} Ergebnis(se) gespeichert!`);
    if (result.errors.length > 0) {
      toast(`⚠️ ${result.errors.length} Fehler: ${result.errors.join(', ')}`, 'error');
    }
    loadMatchesForPhase();
  } catch (e) {
    toast('Fehler: ' + e.message, 'error');
  }
}

// ========== MATCH INSERTER TOOL ==========

async function loadMatchInserterSeasons() {
  try {
    const seasons = await fetch(`${API_URL}/api/seasons`).then(r => r.json());
    const select = document.getElementById('match-insert-season');

    select.innerHTML = '<option value="">Wählen...</option>' +
      seasons.sort((a, b) => b.id - a.id).map(s =>
        `<option value="${s.id}">${s.name}</option>`
      ).join('');

    select.onchange = loadMatchInserterGroups;
  } catch (e) {
    console.error('Fehler beim Laden der Saisons:', e);
  }
}

async function loadMatchInserterGroups() {
  const seasonId = document.getElementById('match-insert-season').value;
  const select = document.getElementById('match-insert-group');
  const matchdayContainer = document.getElementById('match-insert-matchday-container');

  matchdayContainer.style.display = 'none';

  if (!seasonId) {
    select.innerHTML = '<option value="">Erst Saison wählen</option>';
    return;
  }

  try {
    const groups = await fetch(`${API_URL}/api/seasons/${seasonId}/groups-with-teams`).then(r => r.json());

    let html = '<option value="">Wählen...</option>';
    html += `<option value="all:${seasonId}">Alle Gruppen</option>`;
    groups.forEach(g => {
      html += `<option value="group:${g.group.id}">Gruppe ${g.group.name}</option>`;
    });
    html += `<option value="ko:${seasonId}">KO-Phase</option>`;

    select.innerHTML = html;
    select.onchange = loadMatchInserterMatchdays;
  } catch (e) {
    select.innerHTML = '<option value="">Fehler beim Laden</option>';
  }
}

async function loadMatchInserterMatchdays() {
  const groupValue = document.getElementById('match-insert-group').value;
  const seasonId = document.getElementById('match-insert-season').value;
  const matchdayContainer = document.getElementById('match-insert-matchday-container');
  const matchdaySelect = document.getElementById('match-insert-matchday');

  if (!groupValue) {
    matchdayContainer.style.display = 'none';
    return;
  }

  const [type, id] = groupValue.split(':');

  if (type === 'group' || type === 'all') {
    try {
      let endpoint;
      if (type === 'all') {
        endpoint = `${API_URL}/api/seasons/${seasonId}/matchdays`;
      } else {
        endpoint = `${API_URL}/api/groups/${id}/matchdays`;
      }

      const data = await fetch(endpoint).then(r => r.json());
      const maxMatchday = data.max_matchday;

      if (maxMatchday > 0) {
        let html = type === 'all'
          ? '<option value="">Spieltag wählen (erforderlich)</option>'
          : '<option value="">Alle Spieltage</option>';

        for (let i = 1; i <= maxMatchday; i++) {
          html += `<option value="${i}">Spieltag ${i}</option>`;
        }
        matchdaySelect.innerHTML = html;
        matchdayContainer.style.display = 'block';
      } else {
        matchdayContainer.style.display = 'none';
      }
    } catch (e) {
      matchdayContainer.style.display = 'none';
    }
  } else {
    matchdayContainer.style.display = 'none';
  }
}

async function insertMatches() {
  const seasonId = document.getElementById('match-insert-season').value;
  const groupValue = document.getElementById('match-insert-group').value;
  const matchday = document.getElementById('match-insert-matchday').value;
  const textarea = document.getElementById('news-content');

  if (!seasonId || !groupValue) {
    toast('Bitte Saison und Gruppe/Phase wählen', 'error');
    return;
  }

  try {
    const [type, id] = groupValue.split(':');
    let matchIds = [];

    if (type === 'all') {
      if (!matchday) {
        toast('Bitte Spieltag wählen für "Alle Gruppen"', 'error');
        return;
      }

      const matches = await fetch(`${API_URL}/api/seasons/${seasonId}/matchday/${matchday}`).then(r => r.json());
      matchIds = matches.map(m => m.id);

      if (matchIds.length === 0) {
        toast('Keine Matches an diesem Spieltag gefunden', 'error');
        return;
      }

      const syntax = `[matches:${matchIds.join(',')}]`;
      insertAtCursor(textarea, syntax);
      toast(`${matchIds.length} Match(es) von Spieltag ${matchday} eingefügt!`);

    } else if (type === 'group') {
      if (matchday) {
        const matches = await fetch(`${API_URL}/api/groups/${id}/matchday/${matchday}`).then(r => r.json());
        matchIds = matches.map(m => m.id);
      } else {
        const groups = await fetch(`${API_URL}/api/seasons/${seasonId}/groups-with-teams`).then(r => r.json());
        const group = groups.find(g => g.group.id == id);

        if (group && group.matches) {
          matchIds = group.matches.map(m => m.id);
        }
      }

      if (matchIds.length === 0) {
        toast('Keine Matches gefunden', 'error');
        return;
      }

      const syntax = `[matches:${matchIds.join(',')}]`;
      insertAtCursor(textarea, syntax);
      toast(`${matchIds.length} Match(es) eingefügt!`);

    } else if (type === 'ko') {
      const response = await fetch(`${API_URL}/api/seasons/${seasonId}/ko-brackets`);

      if (!response.ok) {
        toast('Noch keine KO-Brackets für diese Saison', 'error');
        return;
      }

      const data = await response.json();

      for (const bracketType of ['meister', 'lucky_loser', 'loser']) {
        const bracket = data.brackets[bracketType];
        if (!bracket || !bracket.rounds) continue;
        for (const rounds of Object.values(bracket.rounds)) {
          rounds.filter(m => !m.is_bye).forEach(m => matchIds.push(m.match_id));
        }
      }

      if (matchIds.length === 0) {
        toast('Keine KO-Matches gefunden', 'error');
        return;
      }

      const syntax = `[ko-matches:${matchIds.join(',')}]`;
      insertAtCursor(textarea, syntax);
      toast(`${matchIds.length} KO-Match(es) eingefügt!`);
    }

  } catch (e) {
    toast('Fehler: ' + e.message, 'error');
  }
}
