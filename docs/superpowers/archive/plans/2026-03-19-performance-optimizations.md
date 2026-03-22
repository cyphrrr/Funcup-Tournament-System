# Bereich E: Performance-Optimierungen — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate redundant API calls, parallelize sequential loads, and add cross-page caching for crests/teams.

**Architecture:** Three independent improvements to the frontend: (1) refactor `initBackendStatus()` to accept external success signals and use `/api/version` for polling, (2) replace sequential `await`-in-loop patterns in archiv.html with `Promise.all`, (3) add `sessionStorage` caching layer to `team-utils.js`.

**Tech Stack:** Vanilla JS (ES Modules), Fetch API, sessionStorage

---

### Task 1: Refactor Backend-Status to eliminate double fetches

**Files:**
- Modify: `frontend/js/shared-ui.js:29-46`
- Modify: `frontend/index.html:692` (inline `initBackendStatus()` call)
- Modify: `frontend/turnier.html:332-334` (footer script block)
- Modify: `frontend/ko.html:372-375` (footer script block)
- Modify: `frontend/archiv.html:490-493` (footer script block)
- Modify: `frontend/ewige-tabelle.html:169-172` (footer script block)
- Modify: `frontend/dashboard.html:538` (inline call)
- Modify: `frontend/team.html:111` (inline call)
- No change needed: `frontend/regeln.html`, `frontend/datenschutz.html`, `frontend/impressum.html` (no own API calls — keep current behavior with `/api/version`)

**Current problem:** `initBackendStatus()` fetches `/api/seasons` immediately on load AND every 30s. Pages like index, turnier, ko, archiv already fetch `/api/seasons` on load → duplicate request.

**Solution:** Split into two exports:
- `setBackendStatus(online)` — sets the status dot directly, no fetch
- `initBackendStatus()` — sets up 30s interval using `/api/version` (lightweight), but does NOT fetch immediately (waits for first interval tick or explicit `setBackendStatus` call)

Pages that fetch data call `setBackendStatus(true)` on success (or `false` on catch). Static pages rely on the interval.

- [ ] **Step 1: Refactor `shared-ui.js` — new API**

Replace `initBackendStatus()` (lines 29-46) with:

```javascript
export function setBackendStatus(online) {
  const statusDot = document.getElementById('backend-status-dot');
  const statusText = document.getElementById('backend-status-text');
  if (!statusDot || !statusText) return;
  statusDot.className = online ? 'status-dot online' : 'status-dot offline';
  statusText.textContent = online ? 'Backend verbunden' : 'Backend getrennt';
}

export function initBackendStatus() {
  setInterval(() => {
    fetch(`${API_URL}/api/version`).then(r => {
      setBackendStatus(r.ok);
    }).catch(() => {
      setBackendStatus(false);
    });
  }, 30000);
}
```

- [ ] **Step 2: Update index.html — use `setBackendStatus`**

In the main `<script type="module">` block (line 167): add `setBackendStatus` to the import from `shared-ui.js`.

In the IIFE (around line 660-687), after `resolveActiveSeason()` succeeds, call `setBackendStatus(true)`. In the catch block, call `setBackendStatus(false)`.

Remove the separate footer `<script type="module">` block that calls `initBackendStatus()` (there is none for index — it's inline at line 692). Replace `initBackendStatus()` at line 692 with `initBackendStatus()` (keep it — it starts the 30s interval, just no longer does the immediate fetch).

Specifically at line 692, keep `initBackendStatus()` but change the import at line 167 to also import `setBackendStatus`. Then inside the IIFE, add `setBackendStatus(true)` after successful data load and `setBackendStatus(false)` in catch.

- [ ] **Step 3: Update turnier.html — use `setBackendStatus`**

Line 279: The seasons fetch is `fetch(...).then(r => r.json()).then(seasons => { ... })`. Add `.catch(() => setBackendStatus(false))` and `setBackendStatus(true)` at start of the success callback.

Import `setBackendStatus` alongside existing imports. Keep the footer `initBackendStatus()` call for the 30s interval.

- [ ] **Step 4: Update ko.html — use `setBackendStatus`**

Same pattern as turnier: line 313 has `fetch(...).then(r => r.json()).then(seasons => { ... })`. Add `setBackendStatus(true)` in success, catch for failure.

Import `setBackendStatus`. Keep footer `initBackendStatus()`.

- [ ] **Step 5: Update archiv.html — use `setBackendStatus`**

In `loadSeasons()` (line 424): after `fetch(`${API}/api/seasons`)` succeeds, call `setBackendStatus(true)`. Add catch with `setBackendStatus(false)`.

Import `setBackendStatus` at line 101. Keep footer `initBackendStatus()`.

- [ ] **Step 6: Update ewige-tabelle.html — use `setBackendStatus`**

In `loadAllTimeStandings()` (line 84): after `loadCrests()` + standings fetch succeed, call `setBackendStatus(true)`. Catch → `setBackendStatus(false)`.

Import `setBackendStatus` at line 76. Keep footer `initBackendStatus()`.

- [ ] **Step 7: Update dashboard.html — use `setBackendStatus`**

Line 228: import `setBackendStatus`. In `init()` function, after first successful API call, `setBackendStatus(true)`. Catch → `setBackendStatus(false)`.

Keep `initBackendStatus()` at line 538.

- [ ] **Step 8: Update team.html — use `setBackendStatus`**

Line 106: import `setBackendStatus`. In `loadTeamProfile()`, after successful team fetch, `setBackendStatus(true)`. Catch → `setBackendStatus(false)`.

Keep `initBackendStatus()` at line 111.

- [ ] **Step 9: Commit**

```bash
git add frontend/js/shared-ui.js frontend/index.html frontend/turnier.html frontend/ko.html frontend/archiv.html frontend/ewige-tabelle.html frontend/dashboard.html frontend/team.html
git commit -m "perf: eliminate double backend-status fetch, use /api/version for polling"
```

---

### Task 2: Parallelize Archiv sequential loads

**Files:**
- Modify: `frontend/archiv.html:436-461` (`loadSeasons` function)
- Modify: `frontend/archiv.html:156-197` (`loadSeasonDetails` function, standings loop)

**Current problem:** Two sequential `await`-in-loop patterns:
1. `loadSeasons()`: fetches `groups-with-teams` for each season sequentially (line 441)
2. `loadSeasonDetails()`: fetches `standings` for each group sequentially (line 170)

**Solution:** Use `Promise.all` to parallelize both loops.

- [ ] **Step 1: Parallelize `loadSeasons()` — fetch all groups in parallel**

Replace the sequential for-loop (lines 436-461) with:

```javascript
// Fetch all group data in parallel
const groupResults = await Promise.all(
  seasons.map(s => fetch(`${API}/api/seasons/${s.id}/groups-with-teams`).then(r => r.json()))
);

let html = '';
seasons.forEach((season, i) => {
  const groups = groupResults[i];
  const badgeClass = season.status === 'active' ? 'active' : season.status === 'archived' ? 'archived' : 'planned';
  const badgeText = season.status === 'active' ? 'Aktiv' : season.status === 'archived' ? 'Archiviert' : 'Geplant';
  const teamCount = groups.reduce((sum, g) => sum + g.teams.length, 0);

  html += `
    <div class="season-card">
      <div class="season-header" onclick="toggleSeason(${season.id})">
        <div class="season-info">
          <div>
            <div class="season-name">${season.name}</div>
            <div class="season-meta">
              <span class="season-badge ${badgeClass}">${badgeText}</span>
              <span>${teamCount} Teams</span>
              <span>${groups.length} Gruppen</span>
            </div>
          </div>
        </div>
        <div class="season-toggle" id="season-toggle-${season.id}">▼</div>
      </div>
      <div class="season-content" id="season-content-${season.id}"></div>
    </div>`;
});
```

- [ ] **Step 2: Parallelize `loadSeasonDetails()` — fetch all standings in parallel**

Replace the sequential standings loop (lines 164-196) with parallel fetch:

```javascript
// Fetch all standings in parallel
const standingsResults = await Promise.all(
  groups.map(g => fetch(`${API}/api/groups/${g.group.id}/standings`).then(r => r.json()))
);

for (let i = 0; i < groups.length; i++) {
  const g = groups[i];
  const standings = standingsResults[i];

  html += `<div class="card" style="margin-bottom:1rem">
    <div class="card-header">
      <div class="card-title">Gruppe ${g.group.name}</div>
    </div>`;

  if (standings.length > 0) {
    html += '<div style="overflow-x:auto"><table class="compact-table">...'; // (existing table HTML)
  } else {
    html += '<p style="color:var(--muted);font-size:.85rem;margin-top:.5rem">Noch keine Spiele ausgetragen</p>';
  }
  html += '</div>';
}
```

- [ ] **Step 3: Also fix duplicate `groups-with-teams` fetch in `loadSeasonDetails()`**

Currently `loadSeasonDetails()` calls both `loadTeams(seasonId)` (line 153, which fetches `groups-with-teams`) AND fetches `groups-with-teams` again at line 156. Eliminate the duplicate:

```javascript
async function loadSeasonDetails(seasonId) {
  const container = document.getElementById(`season-content-${seasonId}`);
  container.innerHTML = '<div class="loading"><em>Lade Details...</em></div>';

  try {
    // Load groups+teams and crests in parallel (single groups fetch, not two)
    const [groups, _] = await Promise.all([
      fetch(`${API}/api/seasons/${seasonId}/groups-with-teams`).then(r => r.json()),
      loadCrests()
    ]);
    registerTeams(groups);

    // ... rest of function using groups
```

- [ ] **Step 4: Commit**

```bash
git add frontend/archiv.html
git commit -m "perf: parallelize archiv season and standings loads with Promise.all"
```

---

### Task 3: Add sessionStorage cache for crests

**Files:**
- Modify: `frontend/js/team-utils.js:1-12`

**Current problem:** `loadCrests()` fetches `/api/teams/crests` on every page load. Navigating between pages triggers redundant identical fetches.

**Solution:** Cache in `sessionStorage` with 10-minute TTL. On `loadCrests()`, check cache first. On cache miss or expired TTL, fetch and store.

- [ ] **Step 1: Add sessionStorage caching to `loadCrests()`**

Replace `loadCrests()` (lines 6-12) with:

```javascript
const CREST_CACHE_KEY = 'biw_crests';
const CREST_CACHE_TTL = 10 * 60 * 1000; // 10 minutes

export async function loadCrests() {
  // Check sessionStorage first
  try {
    const cached = sessionStorage.getItem(CREST_CACHE_KEY);
    if (cached) {
      const { data, ts } = JSON.parse(cached);
      if (Date.now() - ts < CREST_CACHE_TTL) {
        crestCache = data;
        return;
      }
    }
  } catch (e) { /* ignore parse errors */ }

  // Cache miss or expired — fetch
  try {
    crestCache = await fetch(`${API_URL}/api/teams/crests`).then(r => r.json());
    sessionStorage.setItem(CREST_CACHE_KEY, JSON.stringify({ data: crestCache, ts: Date.now() }));
  } catch (e) {
    console.warn('Crests konnten nicht geladen werden:', e);
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/js/team-utils.js
git commit -m "perf: cache crests in sessionStorage with 10min TTL"
```

---

### Task 4: Update frontend-todo.md

**Files:**
- Modify: `docs/frontend-todo.md`

- [ ] **Step 1: Mark Bereich E tasks as complete and add Umsetzungslog entry**

Check off the three items in Bereich E and add a log entry.

- [ ] **Step 2: Commit**

```bash
git add docs/frontend-todo.md
git commit -m "docs: mark Bereich E (Performance) as complete in frontend-todo"
```
