# Homepage Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current News + Standings homepage with a dashboard-style layout: Hero bar + tabbed content + persistent sidebar, with automatic KO phase adaptation.

**Architecture:** Single-file rewrite of `frontend/index.html`. The `<head>`, `<header>`, `<nav>`, and `<footer>` sections stay unchanged. We rewrite the `<style>` block (add new CSS, keep existing shared styles), the `<main>` HTML structure, and the entire `<script type="module">` block. No backend changes.

**Tech Stack:** Vanilla HTML/JS/CSS, existing theme system (CSS custom properties), existing API endpoints.

**Spec:** `docs/superpowers/specs/2026-03-19-homepage-redesign-design.md`

---

### Task 1: Add CSS for Hero Dashboard Bar

**Files:**
- Modify: `frontend/index.html:12-91` (the `<style>` block)

- [ ] **Step 1: Add hero dashboard CSS after the existing `.card h2` rule (line 90)**

Add these styles inside the existing `<style>` block, before the closing `</style>` tag:

```css
/* Hero Dashboard Bar */
.hero-bar{background:linear-gradient(135deg,var(--card) 0%,var(--card-alt) 100%);border-bottom:1px solid var(--border);padding:1rem 2rem}
.hero-bar-inner{max-width:1200px;margin:0 auto;display:flex;gap:1rem;align-items:center;flex-wrap:wrap}
.hero-stat{background:var(--card-alt);border:1px solid var(--border);border-radius:8px;padding:.5rem 1rem;text-align:center;flex:1;min-width:100px}
.hero-stat .hero-label{font-size:.7rem;text-transform:uppercase;color:var(--muted);letter-spacing:0.05em;margin-bottom:2px}
.hero-stat .hero-value{font-family:'Outfit',sans-serif;font-size:1rem;font-weight:700;color:var(--primary)}
.hero-stat .hero-value.neutral{color:var(--text)}
.hero-stat-divider{width:1px;height:2rem;background:var(--border);flex-shrink:0}
.phase-badge{display:inline-block;font-size:.7rem;font-weight:700;padding:2px 8px;border-radius:4px;text-transform:uppercase;letter-spacing:0.04em}
.phase-badge.group{background:color-mix(in srgb,var(--success) 15%,transparent);color:var(--success);border:1px solid var(--success)}
.phase-badge.ko{background:color-mix(in srgb,var(--danger) 15%,transparent);color:var(--danger);border:1px solid var(--danger)}
@media(max-width:768px){.hero-bar-inner{display:grid;grid-template-columns:1fr 1fr;gap:.5rem}.hero-stat-divider{display:none}}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/index.html
git commit -m "style: add hero dashboard bar CSS"
```

---

### Task 2: Add CSS for Tab System, Accordions, and Match Rows

**Files:**
- Modify: `frontend/index.html` (`<style>` block)

- [ ] **Step 1: Add tab, accordion, and match row CSS after the hero CSS**

```css
/* Tabs */
.tab-bar{display:flex;gap:4px;margin-bottom:0}
.tab-btn{padding:.5rem 1rem;border:1px solid var(--border);border-bottom:none;border-radius:8px 8px 0 0;background:var(--card);color:var(--muted);font-family:'DM Sans',sans-serif;font-size:.85rem;font-weight:500;cursor:pointer;transition:all .2s}
.tab-btn:hover{color:var(--text);background:var(--card-alt)}
.tab-btn.active{color:var(--primary);font-weight:700;background:var(--card-alt);border-color:var(--primary);border-bottom:2px solid var(--card-alt);position:relative;z-index:1;margin-bottom:-1px}
.tab-content{background:linear-gradient(145deg,var(--card) 0%,var(--card-alt) 100%);border:1px solid var(--border);border-top-color:var(--primary);border-radius:0 8px 8px 8px;padding:1.25rem 1.5rem;min-height:200px}
.tab-panel{display:none}
.tab-panel.active{display:block}

/* Accordion */
.accordion-toggle{display:flex;align-items:center;gap:.5rem;padding:.6rem 0;border:none;background:none;color:var(--muted);font-family:'DM Sans',sans-serif;font-size:.8rem;font-weight:600;cursor:pointer;width:100%;text-align:left;border-top:1px solid var(--border);margin-top:.5rem}
.accordion-toggle:hover{color:var(--text)}
.accordion-toggle .arrow{transition:transform .2s;font-size:.7rem}
.accordion-toggle.open .arrow{transform:rotate(90deg)}
.accordion-body{display:none}
.accordion-body.open{display:block}

/* Match rows */
.match-row{display:flex;align-items:center;padding:.5rem 0;border-bottom:1px solid var(--border)}
.match-row:last-child{border-bottom:none}
.match-team{flex:1;font-size:.85rem;font-weight:500;display:inline-flex;align-items:center}
.match-team.home{justify-content:flex-end;text-align:right}
.match-team.away{justify-content:flex-start;text-align:left}
.match-score-center{margin:0 .5rem;min-width:50px;text-align:center}
.matchday-label{font-size:.75rem;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:0.04em;margin-bottom:.5rem;margin-top:.25rem}

/* Content grid (tabs + sidebar) */
.content-grid{display:grid;grid-template-columns:2fr 1fr;gap:1.5rem;align-items:start}
@media(max-width:768px){.content-grid{grid-template-columns:1fr}}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/index.html
git commit -m "style: add tab system, accordion, and match row CSS"
```

---

### Task 3: Add CSS for Mini KO Bracket (Sidebar)

**Files:**
- Modify: `frontend/index.html` (`<style>` block)

- [ ] **Step 1: Add mini bracket CSS after the content grid CSS**

```css
/* Mini KO Bracket (sidebar) */
.mini-bracket{margin-top:.5rem}
.mini-bracket-round{display:flex;gap:.75rem;align-items:center;margin-bottom:.5rem}
.mini-match-card{background:var(--card);border:1px solid var(--border);border-radius:6px;padding:.4rem .6rem;font-size:.75rem;min-width:100px;flex:1}
.mini-match-card .mini-team-row{display:flex;justify-content:space-between;padding:2px 0}
.mini-match-card .mini-team-row.winner{color:var(--primary);font-weight:700}
.mini-connector{color:var(--muted);font-size:.9rem;flex-shrink:0}
.bracket-label{font-size:.8rem;font-weight:700;color:var(--primary);margin:1rem 0 .25rem;font-family:'Outfit',sans-serif}
.bracket-label:first-child{margin-top:0}
.bracket-link{display:block;text-align:center;margin-top:.75rem;font-size:.8rem;color:var(--primary);text-decoration:none}
.bracket-link:hover{text-decoration:underline}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/index.html
git commit -m "style: add mini KO bracket sidebar CSS"
```

---

### Task 4: Rewrite HTML Structure (Hero + Tabs + Sidebar)

**Files:**
- Modify: `frontend/index.html:131-151` (the `<main>` section)

- [ ] **Step 1: Replace the entire `<main>` section (lines 131–151) with the new structure**

Replace from `<main>` to `</main>` with:

```html
  <!-- Hero Dashboard Bar -->
  <div class="hero-bar">
    <div class="hero-bar-inner">
      <div class="hero-stat">
        <div class="hero-label">Saison</div>
        <div class="hero-value neutral" id="hero-season">...</div>
      </div>
      <div class="hero-stat-divider"></div>
      <div class="hero-stat">
        <div class="hero-label">Phase</div>
        <div class="hero-value" id="hero-phase">...</div>
      </div>
      <div class="hero-stat-divider"></div>
      <div class="hero-stat">
        <div class="hero-label" id="hero-matchday-label">Spieltag</div>
        <div class="hero-value" id="hero-matchday">...</div>
      </div>
      <div class="hero-stat-divider"></div>
      <div class="hero-stat">
        <div class="hero-label" id="hero-teams-label">Teams</div>
        <div class="hero-value neutral" id="hero-teams">...</div>
      </div>
    </div>
  </div>

  <main>
    <div class="content-grid">
      <!-- Tabs (2/3) -->
      <div>
        <div class="tab-bar" id="tab-bar">
          <button class="tab-btn active" data-tab="ergebnisse">Ergebnisse</button>
          <button class="tab-btn" data-tab="news">News</button>
        </div>
        <div class="tab-content">
          <div class="tab-panel active" id="panel-ergebnisse"><em>Lade Ergebnisse...</em></div>
          <div class="tab-panel" id="panel-news"><em>Lade News...</em></div>
        </div>
      </div>

      <!-- Sidebar (1/3) -->
      <div id="sidebar">
        <div id="sidebar-content"><em>Lade Tabellen...</em></div>
      </div>
    </div>
  </main>
```

- [ ] **Step 2: Remove old CSS that is no longer needed**

Remove the `.start-grid` CSS rule (line 60-61 in the original):
```css
/* DELETE these two lines */
.start-grid{display:grid;grid-template-columns:2fr 1fr;gap:2rem;align-items:start}
@media(max-width:768px){.start-grid{grid-template-columns:1fr}}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/index.html
git commit -m "feat: rewrite homepage HTML structure with hero bar, tabs, and sidebar"
```

---

### Task 5: Rewrite JavaScript — Data Loading, Caching, Phase Detection

**Files:**
- Modify: `frontend/index.html` (the `<script type="module">` block, lines 153–412)

- [ ] **Step 1: Replace the entire `<script type="module">` block with the new JavaScript**

Replace everything between `<script type="module">` and its closing `</script>` tag. This step writes the data layer and initialization. The rendering functions follow in subsequent tasks.

```javascript
import { API_URL } from './js/config.js';
const API = API_URL;

// --- State ---
let teamCache = {};
let crestCache = {};
let groupsData = [];
let allMatches = [];
let koBrackets = null;
let activeSeason = null;
let isKOPhase = false;

// --- Data Loading ---

async function loadCrests() {
  try {
    crestCache = await fetch(`${API}/api/teams/crests`).then(r => r.json());
  } catch (e) {
    console.warn('Crests konnten nicht geladen werden:', e);
  }
}

function crestImg(teamId, size = 20) {
  const url = crestCache[String(teamId)];
  if (!url) return '';
  const src = url.startsWith('http') ? url : `${API}${url}`;
  return `<img src="${src}" alt="" loading="lazy" style="width:${size}px;height:${size}px;object-fit:contain;vertical-align:middle;margin-right:4px;border-radius:3px;flex-shrink:0" onerror="this.style.display='none'">`;
}

function teamName(id) {
  return teamCache[id] || `Team ${id}`;
}

async function resolveActiveSeason() {
  const seasons = await fetch(`${API}/api/seasons`).then(r => r.json());
  const activeSeasons = seasons.filter(s => s.status === 'active');
  if (activeSeasons.length > 0) {
    activeSeasons.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    return activeSeasons[0];
  }
  return seasons[0] || null;
}

async function loadGroupsAndTeams(seasonId) {
  groupsData = await fetch(`${API}/api/seasons/${seasonId}/groups-with-teams`).then(r => r.json());
  groupsData.forEach(g => g.teams.forEach(t => { teamCache[t.id] = t.name; }));
  allMatches = groupsData.flatMap(g =>
    (g.matches || []).map(m => ({ ...m, groupName: g.group.name }))
  );
}

// KO brackets API response format:
// { season_id, brackets: { meister: { bracket_id, status, rounds: { runde_1: [...], runde_2: [...] } }, lucky_loser: ..., loser: ... } }
// Each match: { match_id, round (string like "finale"), home_team: {id, name} | null, away_team: {id, name} | null, home_goals, away_goals, winner_id, is_bye, is_third_place, status }

async function detectKOPhase(seasonId) {
  try {
    const resp = await fetch(`${API}/api/seasons/${seasonId}/ko-brackets`);
    if (!resp.ok) return false;
    const data = await resp.json();
    if (data && data.brackets) {
      const hasBrackets = Object.values(data.brackets).some(b => b && b.rounds && Object.keys(b.rounds).length > 0);
      if (hasBrackets) {
        koBrackets = data.brackets;
        return true;
      }
    }
  } catch (e) {
    console.warn('KO brackets not available:', e);
  }
  return false;
}

// Flatten a bracket object (e.g. koBrackets.meister) into a flat array of matches
function flattenBracketMatches(bracket) {
  if (!bracket || !bracket.rounds) return [];
  return Object.values(bracket.rounds).flat();
}

function deriveCurrentMatchday() {
  if (allMatches.length === 0) return { current: 0, total: 0 };
  const matchdays = [...new Set(allMatches.map(m => m.matchday))].sort((a, b) => a - b);
  const total = matchdays.length > 0 ? Math.max(...matchdays) : 0;
  const playedMatchdays = matchdays.filter(md =>
    allMatches.some(m => m.matchday === md && m.status === 'played')
  );
  const current = playedMatchdays.length > 0 ? Math.max(...playedMatchdays) : 0;
  return { current, total };
}

function deriveKORoundInfo() {
  if (!koBrackets || !koBrackets.meister) return { roundName: '—', teamsRemaining: 0 };
  const meisterMatches = flattenBracketMatches(koBrackets.meister);
  if (meisterMatches.length === 0) return { roundName: '—', teamsRemaining: 0 };

  // round field is a string like "finale", "halbfinale", "viertelfinale", "achtelfinale", "runde_N"
  // Use runde_X keys for ordering
  const roundKeys = Object.keys(koBrackets.meister.rounds).sort(); // runde_1 < runde_2 etc.

  // Find the first round (by key order) that has at least one unplayed, non-bye match
  const currentRoundKey = roundKeys.find(key =>
    koBrackets.meister.rounds[key].some(m => m.status !== 'played' && !m.is_bye)
  ) || roundKeys[roundKeys.length - 1];

  const currentRoundMatches = koBrackets.meister.rounds[currentRoundKey] || [];
  const nonByeMatches = currentRoundMatches.filter(m => !m.is_bye);

  // Get round name from the first match's round field
  const roundName = nonByeMatches.length > 0
    ? nonByeMatches[0].round.charAt(0).toUpperCase() + nonByeMatches[0].round.slice(1)
    : '—';

  // Count distinct teams in current round
  const teamIds = new Set();
  nonByeMatches.forEach(m => {
    if (m.home_team) teamIds.add(m.home_team.id);
    if (m.away_team) teamIds.add(m.away_team.id);
  });

  return { roundName, teamsRemaining: teamIds.size };
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/index.html
git commit -m "feat: homepage JS data layer — season resolution, phase detection, matchday derivation"
```

---

### Task 6: JavaScript — Hero Bar Rendering

**Files:**
- Modify: `frontend/index.html` (continue in the `<script type="module">` block, after the data layer)

- [ ] **Step 1: Add the hero rendering function after `deriveKORoundInfo()`**

```javascript
// --- Hero Bar ---

function renderHero() {
  document.getElementById('hero-season').textContent = activeSeason ? activeSeason.name : 'Keine aktive Saison';

  if (!activeSeason) {
    document.getElementById('hero-phase').innerHTML = '<span class="phase-badge group">—</span>';
    document.getElementById('hero-matchday').textContent = '—';
    document.getElementById('hero-teams').textContent = '—';
    return;
  }

  if (isKOPhase) {
    document.getElementById('hero-phase').innerHTML = '<span class="phase-badge ko">KO-Phase</span>';
    const { roundName, teamsRemaining } = deriveKORoundInfo();
    document.getElementById('hero-matchday-label').textContent = 'Runde';
    document.getElementById('hero-matchday').textContent = roundName;
    document.getElementById('hero-teams-label').textContent = 'Teams übrig';
    document.getElementById('hero-teams').textContent = teamsRemaining;
  } else {
    document.getElementById('hero-phase').innerHTML = '<span class="phase-badge group">Gruppenphase</span>';
    const { current, total } = deriveCurrentMatchday();
    document.getElementById('hero-matchday-label').textContent = 'Spieltag';
    document.getElementById('hero-matchday').textContent = `SP${current} / SP${total}`;
    document.getElementById('hero-teams-label').textContent = 'Teams';
    document.getElementById('hero-teams').textContent = activeSeason.participant_count || '—';
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/index.html
git commit -m "feat: hero dashboard bar rendering with phase-aware content"
```

---

### Task 7: JavaScript — Tab System

**Files:**
- Modify: `frontend/index.html` (continue in `<script type="module">` block)

- [ ] **Step 1: Add tab system logic after the hero function**

```javascript
// --- Tab System ---

function initTabs() {
  const tabBar = document.getElementById('tab-bar');
  const buttons = tabBar.querySelectorAll('.tab-btn');

  // Update tab labels for KO phase
  if (isKOPhase) {
    const ergebnisseBtn = tabBar.querySelector('[data-tab="ergebnisse"]');
    if (ergebnisseBtn) ergebnisseBtn.textContent = 'KO-Ergebnisse';
  }

  buttons.forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });

  // Restore tab from URL hash
  const hash = window.location.hash.replace('#', '');
  if (hash && document.getElementById(`panel-${hash}`)) {
    switchTab(hash);
  }
}

function switchTab(tabId) {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tabId);
  });
  document.querySelectorAll('.tab-panel').forEach(panel => {
    panel.classList.toggle('active', panel.id === `panel-${tabId}`);
  });
  window.location.hash = tabId;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/index.html
git commit -m "feat: tab system with hash-based persistence"
```

---

### Task 8: JavaScript — Ergebnisse Tab (Group Phase)

**Files:**
- Modify: `frontend/index.html` (continue in `<script type="module">` block)

- [ ] **Step 1: Add Ergebnisse rendering after the tab system code**

```javascript
// --- Ergebnisse Tab ---

function renderMatchRow(m) {
  const home = teamName(m.home_team_id);
  const away = teamName(m.away_team_id);
  const score = m.status === 'played'
    ? `<span class="match-score">${m.home_goals}:${m.away_goals}</span>`
    : '<span style="color:var(--muted)">-:-</span>';
  return `
    <div class="match-row">
      <span class="match-team home">${home}&nbsp;${crestImg(m.home_team_id)}</span>
      <span class="match-score-center">${score}</span>
      <span class="match-team away">${crestImg(m.away_team_id)}&nbsp;${away}</span>
    </div>`;
}

function renderGroupErgebnisse() {
  const panel = document.getElementById('panel-ergebnisse');
  if (allMatches.length === 0) {
    panel.innerHTML = '<p style="color:var(--muted)">Noch keine Ergebnisse.</p>';
    return;
  }

  const { current } = deriveCurrentMatchday();
  const matchdays = [...new Set(allMatches.map(m => m.matchday))].sort((a, b) => b - a);

  let html = '';
  matchdays.forEach(md => {
    const mdMatches = allMatches.filter(m => m.matchday === md);
    const isCurrentOrNewer = md >= current && current > 0;
    const isOpen = isCurrentOrNewer || current === 0;

    if (isOpen) {
      html += `<div class="matchday-label">Spieltag ${md}</div>`;
      html += mdMatches.map(renderMatchRow).join('');
    } else {
      const playedCount = mdMatches.filter(m => m.status === 'played').length;
      html += `
        <button class="accordion-toggle" onclick="this.classList.toggle('open');this.nextElementSibling.classList.toggle('open')">
          <span class="arrow">▸</span> Spieltag ${md} (${playedCount} Spiele)
        </button>
        <div class="accordion-body">
          ${mdMatches.map(renderMatchRow).join('')}
        </div>`;
    }
  });

  panel.innerHTML = html;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/index.html
git commit -m "feat: Ergebnisse tab with matchday accordions"
```

---

### Task 9: JavaScript — KO Ergebnisse Tab

**Files:**
- Modify: `frontend/index.html` (continue in `<script type="module">` block)

- [ ] **Step 1: Add KO Ergebnisse rendering after the group Ergebnisse code**

```javascript
// --- KO Ergebnisse Tab ---

// Helper: convert KO match (with home_team/away_team objects) to the format renderMatchRow expects
function koMatchToMatchRow(m) {
  return {
    home_team_id: m.home_team ? m.home_team.id : null,
    away_team_id: m.away_team ? m.away_team.id : null,
    home_goals: m.home_goals,
    away_goals: m.away_goals,
    status: m.status
  };
}

// Also cache team names from KO bracket data
function cacheKOTeamNames() {
  if (!koBrackets) return;
  for (const bracket of Object.values(koBrackets)) {
    if (!bracket || !bracket.rounds) continue;
    for (const matches of Object.values(bracket.rounds)) {
      matches.forEach(m => {
        if (m.home_team) teamCache[m.home_team.id] = m.home_team.name;
        if (m.away_team) teamCache[m.away_team.id] = m.away_team.name;
      });
    }
  }
}

function renderKOErgebnisse() {
  const panel = document.getElementById('panel-ergebnisse');
  if (!koBrackets) {
    panel.innerHTML = '<p style="color:var(--muted)">KO-Bracket nicht verfügbar.</p>';
    return;
  }

  cacheKOTeamNames();

  const bracketLabels = { meister: 'Meister-Bracket', lucky_loser: 'Lucky Loser', loser: 'Trostpflaster' };
  let html = '';

  for (const [bracketType, bracket] of Object.entries(koBrackets)) {
    if (!bracket || !bracket.rounds) continue;

    const roundKeys = Object.keys(bracket.rounds).sort().reverse(); // newest round first
    const allEmpty = roundKeys.every(key => bracket.rounds[key].filter(m => !m.is_bye).length === 0);
    if (allEmpty) continue;

    html += `<div class="matchday-label" style="margin-top:1rem;font-size:.85rem;color:var(--primary)">${bracketLabels[bracketType] || bracketType}</div>`;

    roundKeys.forEach((roundKey, idx) => {
      const roundMatches = bracket.rounds[roundKey].filter(m => !m.is_bye);
      if (roundMatches.length === 0) return;

      // Use the round field from the first match as display name
      const roundLabel = roundMatches[0].round
        ? roundMatches[0].round.charAt(0).toUpperCase() + roundMatches[0].round.slice(1)
        : roundKey;

      const isOpen = idx === 0; // newest round open by default

      if (isOpen) {
        html += `<div class="matchday-label">${roundLabel}</div>`;
        html += roundMatches.map(m => renderMatchRow(koMatchToMatchRow(m))).join('');
      } else {
        const playedCount = roundMatches.filter(m => m.status === 'played').length;
        html += `
          <button class="accordion-toggle" onclick="this.classList.toggle('open');this.nextElementSibling.classList.toggle('open')">
            <span class="arrow">▸</span> ${roundLabel} (${playedCount}/${roundMatches.length} Spiele)
          </button>
          <div class="accordion-body">
            ${roundMatches.map(m => renderMatchRow(koMatchToMatchRow(m))).join('')}
          </div>`;
      }
    });
  }

  panel.innerHTML = html || '<p style="color:var(--muted)">Noch keine KO-Spiele.</p>';
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/index.html
git commit -m "feat: KO-Ergebnisse tab with round accordions and bracket labels"
```

---

### Task 10: JavaScript — News Tab (Migrated)

**Files:**
- Modify: `frontend/index.html` (continue in `<script type="module">` block)

- [ ] **Step 1: Add News tab rendering — migrated from existing code with minor adaptations**

```javascript
// --- News Tab ---

async function renderMatchesBlock(matchIds, isKO = false) {
  try {
    const endpoint = isKO ? 'ko-matches/batch' : 'matches/batch';
    const matches = await fetch(`${API}/api/${endpoint}?match_ids=${matchIds}`).then(r => r.json());
    if (matches.length === 0) return '<em style="color:var(--muted)">Keine Matches gefunden</em>';

    let html = '<div style="background:var(--card-alt);border:1px solid var(--border);border-radius:8px;padding:1rem;margin:1rem 0">';
    html += '<table style="width:100%;font-size:.9rem">';
    matches.forEach(m => {
      const homeTeam = teamName(m.home_team_id);
      const awayTeam = teamName(m.away_team_id);
      const score = m.status === 'played'
        ? `<span class="match-score">${m.home_goals}:${m.away_goals}</span>`
        : '<span style="color:var(--muted)">-:-</span>';
      html += `
        <tr>
          <td style="text-align:right;padding:.4rem;width:calc(50% - 30px)"><span style="display:inline-flex;align-items:center;justify-content:flex-end">${homeTeam}${crestImg(m.home_team_id)}</span></td>
          <td style="text-align:center;padding:.4rem;width:60px">${score}</td>
          <td style="text-align:left;padding:.4rem;width:calc(50% - 30px)"><span style="display:inline-flex;align-items:center">${crestImg(m.away_team_id)}${awayTeam}</span></td>
        </tr>`;
    });
    html += '</table></div>';
    return html;
  } catch (e) {
    return '<em style="color:var(--danger)">Fehler beim Laden der Matches</em>';
  }
}

async function loadNews() {
  const panel = document.getElementById('panel-news');
  try {
    const news = await fetch(`${API}/api/news`).then(r => r.json());
    if (news.length === 0) {
      panel.innerHTML = '<p style="color:var(--muted)">Noch keine News vorhanden.</p>';
      return;
    }

    panel.innerHTML = '';
    for (const n of news) {
      const date = new Date(n.created_at).toLocaleDateString('de-DE', {
        day: '2-digit', month: 'long', year: 'numeric'
      });

      let content = n.content
        .replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        .replace(/\n/g, '<br>');

      const matchPattern = /\[matches:([0-9,\s]+)\]/g;
      const koMatchPattern = /\[ko-matches:([0-9,\s]+)\]/g;
      const matchBlocks = [];
      let match;
      while ((match = matchPattern.exec(content)) !== null) {
        matchBlocks.push({ placeholder: match[0], matchIds: match[1].trim(), isKO: false });
      }
      while ((match = koMatchPattern.exec(content)) !== null) {
        matchBlocks.push({ placeholder: match[0], matchIds: match[1].trim(), isKO: true });
      }
      for (const block of matchBlocks) {
        const rendered = await renderMatchesBlock(block.matchIds, block.isKO);
        content = content.replace(block.placeholder, rendered);
      }

      const newsCard = document.createElement('div');
      newsCard.className = 'card';
      newsCard.innerHTML = `
        <div class="card-header">
          <div class="card-title">${n.title}</div>
          <div class="card-sub">${date} · ${n.author}</div>
        </div>
        <div style="line-height:1.6">${content}</div>`;
      panel.appendChild(newsCard);
    }
  } catch (e) {
    panel.innerHTML = '<p style="color:var(--danger)">News konnten nicht geladen werden.</p>';
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/index.html
git commit -m "feat: News tab rendering (migrated from original)"
```

---

### Task 11: JavaScript — Sidebar (Group Standings + Mini Bracket)

**Files:**
- Modify: `frontend/index.html` (continue in `<script type="module">` block)

- [ ] **Step 1: Add sidebar rendering functions**

```javascript
// --- Sidebar ---

async function renderGroupStandings() {
  const container = document.getElementById('sidebar-content');
  try {
    if (groupsData.length === 0) {
      container.innerHTML = '<p style="color:var(--muted);font-size:.85rem">Keine Gruppen vorhanden</p>';
      return;
    }

    container.innerHTML = '';
    for (const g of groupsData) {
      const standings = await fetch(`${API}/api/groups/${g.group.id}/standings`).then(r => r.json());
      if (standings.length === 0) continue;

      const div = document.createElement('div');
      div.className = 'compact-standings';
      div.innerHTML = `
        <h3>Gruppe ${g.group.name}</h3>
        <table>
          <thead>
            <tr>
              <th class="pos">#</th>
              <th style="text-align:left">Team</th>
              <th>S</th>
              <th>U</th>
              <th>N</th>
              <th>Pkt</th>
            </tr>
          </thead>
          <tbody>
            ${standings.map((row, idx) => `
              <tr ${idx === 0 ? 'class="leader"' : ''}>
                <td class="pos">${idx + 1}</td>
                <td style="text-align:left"><a href="team.html?id=${row.team_id}" style="color:inherit;text-decoration:none;font-weight:${idx === 0 ? '700' : '500'};display:inline-flex;align-items:center">${crestImg(row.team_id, 18)}${teamName(row.team_id)}</a></td>
                <td>${row.won}</td>
                <td>${row.draw}</td>
                <td>${row.lost}</td>
                <td style="font-weight:600">${row.points}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>`;
      container.appendChild(div);
    }
  } catch (e) {
    container.innerHTML = '<p style="color:var(--danger);font-size:.85rem">Fehler beim Laden</p>';
  }
}

function renderMiniBracket() {
  const container = document.getElementById('sidebar-content');
  if (!koBrackets) {
    container.innerHTML = '<p style="color:var(--muted);font-size:.85rem">KO-Bracket nicht verfügbar</p>';
    return;
  }

  cacheKOTeamNames();

  const bracketLabels = { meister: 'Meister-Bracket', lucky_loser: 'Lucky Loser', loser: 'Trostpflaster' };
  let html = '';

  for (const [bracketType, bracket] of Object.entries(koBrackets)) {
    if (!bracket || !bracket.rounds) continue;

    const roundKeys = Object.keys(bracket.rounds).sort(); // runde_1, runde_2, ...
    const allEmpty = roundKeys.every(key => bracket.rounds[key].filter(m => !m.is_bye).length === 0);
    if (allEmpty) continue;

    html += `<div class="bracket-label">${bracketLabels[bracketType] || bracketType}</div>`;
    html += '<div class="mini-bracket">';

    roundKeys.forEach((roundKey, idx) => {
      const roundMatches = bracket.rounds[roundKey].filter(m => !m.is_bye);
      if (roundMatches.length === 0) return;

      if (idx > 0) html += '<div class="mini-connector">→</div>';
      html += '<div>';
      roundMatches.forEach(m => {
        const homeScore = m.status === 'played' ? m.home_goals : '-';
        const awayScore = m.status === 'played' ? m.away_goals : '-';
        const homeName = m.home_team ? m.home_team.name : '???';
        const awayName = m.away_team ? m.away_team.name : '???';
        const homeId = m.home_team ? m.home_team.id : null;
        const awayId = m.away_team ? m.away_team.id : null;
        const winnerClass = (id) => m.winner_id && m.winner_id === id ? ' winner' : '';

        html += `
          <div class="mini-match-card">
            <div class="mini-team-row${winnerClass(homeId)}">${homeName} <span>${homeScore}</span></div>
            <div class="mini-team-row${winnerClass(awayId)}">${awayName} <span>${awayScore}</span></div>
          </div>`;
      });
      html += '</div>';
    });
    html += '</div>';
  }

  html += '<a class="bracket-link" href="ko.html">Zum vollständigen Bracket →</a>';
  container.innerHTML = html || '<p style="color:var(--muted);font-size:.85rem">Noch keine KO-Daten</p>';
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/index.html
git commit -m "feat: sidebar rendering — group standings and mini KO bracket"
```

---

### Task 12: JavaScript — Main Initialization + Remaining UI Logic

**Files:**
- Modify: `frontend/index.html` (end of `<script type="module">` block)

- [ ] **Step 1: Add the main init function and remaining UI logic (burger menu, backend status)**

```javascript
// --- Initialization ---

(async () => {
  try {
    activeSeason = await resolveActiveSeason();
  } catch (e) {
    document.getElementById('hero-season').textContent = 'Fehler beim Laden';
    document.getElementById('panel-ergebnisse').innerHTML = '<p style="color:var(--danger)">Fehler beim Laden</p>';
    document.getElementById('sidebar-content').innerHTML = '<p style="color:var(--danger)">Fehler beim Laden</p>';
    return;
  }

  if (!activeSeason) {
    renderHero();
    document.getElementById('panel-ergebnisse').innerHTML = '<p style="color:var(--muted)">Keine aktive Saison.</p>';
    document.getElementById('panel-news').innerHTML = '<p style="color:var(--muted)">Keine News.</p>';
    document.getElementById('sidebar-content').innerHTML = '<p style="color:var(--muted)">Keine Daten verfügbar.</p>';
    initTabs();
    return;
  }

  // Load data in parallel
  await Promise.all([
    loadGroupsAndTeams(activeSeason.id),
    loadCrests(),
    detectKOPhase(activeSeason.id).then(result => { isKOPhase = result; })
  ]);

  // Render everything
  renderHero();
  initTabs();

  if (isKOPhase) {
    renderKOErgebnisse();
    renderMiniBracket();
  } else {
    renderGroupErgebnisse();
    renderGroupStandings();
  }

  // News loads independently
  loadNews();
})();

// --- UI: Admin link ---
if (localStorage.getItem('biw_token')) {
  document.getElementById('admin-link').style.display = 'block';
}

// --- UI: Burger Menu ---
const burgerBtn = document.getElementById('burger-btn');
const navMenu = document.getElementById('nav-menu');
const menuOverlay = document.getElementById('menu-overlay');

function toggleMenu() {
  burgerBtn.classList.toggle('open');
  navMenu.classList.toggle('open');
  menuOverlay.classList.toggle('open');
}

burgerBtn.addEventListener('click', toggleMenu);
menuOverlay.addEventListener('click', toggleMenu);
navMenu.querySelectorAll('a').forEach(link => {
  link.addEventListener('click', () => {
    if (navMenu.classList.contains('open')) toggleMenu();
  });
});

// --- UI: Backend Status ---
function updateBackendStatus() {
  const statusDot = document.getElementById('backend-status-dot');
  const statusText = document.getElementById('backend-status-text');
  if (!statusDot || !statusText) return;

  fetch(`${API}/api/seasons`).then(r => {
    if (r.ok) {
      statusDot.className = 'status-dot online';
      statusText.textContent = 'Backend verbunden';
    } else { throw new Error('API Error'); }
  }).catch(() => {
    statusDot.className = 'status-dot offline';
    statusText.textContent = 'Backend getrennt';
  });
}

updateBackendStatus();
setInterval(updateBackendStatus, 30000);
```

- [ ] **Step 2: Commit**

```bash
git add frontend/index.html
git commit -m "feat: homepage init, phase-aware rendering, burger menu, backend status"
```

---

### Task 13: Manual Verification

**Files:**
- Verify: `frontend/index.html`

- [ ] **Step 1: Start the backend**

```bash
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000
```

- [ ] **Step 2: Start the frontend**

```bash
cd frontend && python -m http.server 5500
```

- [ ] **Step 3: Open http://127.0.0.1:5500/index.html and verify:**

Checklist:
- Hero bar shows season name, phase badge (green "Gruppenphase"), matchday (SPx/SPy), team count
- Hero stats are responsive (2x2 grid on mobile, row on desktop)
- Tab bar shows "Ergebnisse" and "News"
- Ergebnisse tab shows matches grouped by matchday, current matchday expanded
- Older matchdays are collapsible accordions
- Match rows show team names with crests and score badges
- News tab shows news articles with markdown rendering and match embeds
- Sidebar shows all group standings with S/U/N/Pkt columns
- Team names in sidebar link to team.html
- URL hash changes when switching tabs (#ergebnisse, #news)
- Refreshing with #news in URL opens News tab
- Dark mode toggle still works
- Theme selector still works
- Burger menu still works
- Backend status indicator works
- Footer unchanged

- [ ] **Step 4: Test mobile responsive (resize browser to ≤768px):**

- Hero stats switch to 2x2 grid
- Content grid becomes single column (tabs above, sidebar below)
- Match rows and standings tables remain readable

- [ ] **Step 5: Final commit if any fixes were needed**

```bash
git add frontend/index.html
git commit -m "fix: homepage polish after manual verification"
```
