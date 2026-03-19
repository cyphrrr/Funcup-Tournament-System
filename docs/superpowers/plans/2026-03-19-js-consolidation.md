# JS-Boilerplate Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate duplicated JS boilerplate (burger menu, admin link, backend status, crest/team utils) from 10 HTML files into two shared ES Modules.

**Architecture:** Two new ES Modules — `js/shared-ui.js` (UI boilerplate for all 10 pages) and `js/team-utils.js` (crest/team functions for 5 data pages). Each HTML page imports only what it needs, replacing inline duplicated code. Migration happens in 3 phases: create modules, migrate static pages, migrate data pages.

**Tech Stack:** Vanilla JS (ES Modules), no build tools

**Spec:** `docs/superpowers/specs/2026-03-19-js-consolidation-design.md`

---

### Task 1: Create `js/shared-ui.js`

**Files:**
- Create: `frontend/js/shared-ui.js`

- [ ] **Step 1: Create the module**

Create `frontend/js/shared-ui.js` with the following content:

```js
import { API_URL } from './config.js';

export function initBurgerMenu() {
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
}

export function initAdminLink() {
  if (localStorage.getItem('biw_token')) {
    document.getElementById('admin-link').style.display = 'block';
  }
}

export function initBackendStatus() {
  const statusDot = document.getElementById('backend-status-dot');
  const statusText = document.getElementById('backend-status-text');
  if (!statusDot || !statusText) return;

  function update() {
    fetch(`${API_URL}/api/seasons`).then(r => {
      statusDot.className = r.ok ? 'status-dot online' : 'status-dot offline';
      statusText.textContent = r.ok ? 'Backend verbunden' : 'Backend getrennt';
    }).catch(() => {
      statusDot.className = 'status-dot offline';
      statusText.textContent = 'Backend getrennt';
    });
  }

  update();
  setInterval(update, 30000);
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/js/shared-ui.js
git commit -m "feat: create shared-ui.js module (burger menu, admin link, backend status)"
```

---

### Task 2: Create `js/team-utils.js`

**Files:**
- Create: `frontend/js/team-utils.js`

- [ ] **Step 1: Create the module**

Create `frontend/js/team-utils.js` with the following content:

```js
import { API_URL } from './config.js';

let crestCache = {};
const teamCache = {};

export async function loadCrests() {
  try {
    crestCache = await fetch(`${API_URL}/api/teams/crests`).then(r => r.json());
  } catch (e) {
    console.warn('Crests konnten nicht geladen werden:', e);
  }
}

export function crestImg(teamId, size = 24) {
  if (!teamId) return '';
  const url = crestCache[String(teamId)];
  if (!url) return '';
  const src = url.startsWith('http') ? url : `${API_URL}${url}`;
  return `<img src="${src}" alt="" loading="lazy" style="width:${size}px;height:${size}px;object-fit:contain;vertical-align:middle;margin-right:4px;border-radius:3px;flex-shrink:0" onerror="this.style.display='none'">`;
}

export function teamName(id) {
  return teamCache[id] || `Team ${id}`;
}

export function registerTeams(groups) {
  groups.forEach(g => g.teams.forEach(t => { teamCache[t.id] = t.name; }));
}

export function registerTeam(id, name) {
  teamCache[id] = name;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/js/team-utils.js
git commit -m "feat: create team-utils.js module (crests, team name cache)"
```

---

### Task 3: Migrate static pages — regeln.html, datenschutz.html, impressum.html

These three pages share the same structure: a plain `<script>` block (not module) before the footer with burger+admin code, and a separate `<script type="module">` block after the footer with backend status.

**Files:**
- Modify: `frontend/regeln.html:141-169` (plain script) + `187-204` (status module)
- Modify: `frontend/datenschutz.html:135-162` (plain script) + `181-198` (status module)
- Modify: `frontend/impressum.html:92-119` (plain script) + `138-155` (status module)

- [ ] **Step 1: Migrate regeln.html**

In `frontend/regeln.html`, replace the plain `<script>` block (lines 141-169) with:

```html
<script type="module">
import { initBurgerMenu, initAdminLink } from './js/shared-ui.js';
initBurgerMenu();
initAdminLink();
</script>
```

Then delete the separate backend status `<script type="module">` block (lines 187-204) and replace with:

```html
<script type="module">
import { initBackendStatus } from './js/shared-ui.js';
initBackendStatus();
</script>
```

**Why two separate blocks?** The burger/admin block is placed before the footer (where it currently lives). The backend status block is placed after the footer (where the footer DOM elements exist). Both are `type="module"` now.

- [ ] **Step 2: Migrate datenschutz.html**

Same pattern as regeln.html. Replace the plain `<script>` block (lines 135-162) with:

```html
<script type="module">
import { initBurgerMenu, initAdminLink } from './js/shared-ui.js';
initBurgerMenu();
initAdminLink();
</script>
```

Delete the backend status `<script type="module">` block (lines 181-198) and replace with:

```html
<script type="module">
import { initBackendStatus } from './js/shared-ui.js';
initBackendStatus();
</script>
```

- [ ] **Step 3: Migrate impressum.html**

Same pattern. Replace the plain `<script>` block (lines 92-119) with:

```html
<script type="module">
import { initBurgerMenu, initAdminLink } from './js/shared-ui.js';
initBurgerMenu();
initAdminLink();
</script>
```

Delete the backend status `<script type="module">` block (lines 138-155) and replace with:

```html
<script type="module">
import { initBackendStatus } from './js/shared-ui.js';
initBackendStatus();
</script>
```

- [ ] **Step 4: Visual verification**

Open each page in browser. Verify:
- Burger menu opens/closes
- Admin link visible when logged in (check localStorage has `biw_token`)
- Backend status dot shows green/red in footer

- [ ] **Step 5: Commit**

```bash
git add frontend/regeln.html frontend/datenschutz.html frontend/impressum.html
git commit -m "refactor: migrate regeln, datenschutz, impressum to shared-ui.js"
```

---

### Task 4: Migrate static pages — dashboard.html, team.html

These pages already use `<script type="module">` and have burger/admin/status code inside the main module block (no separate block).

**Files:**
- Modify: `frontend/dashboard.html:226` (main module block)
- Modify: `frontend/team.html:104` (main module block)

- [ ] **Step 1: Migrate dashboard.html**

In `frontend/dashboard.html`, the main `<script type="module">` starts at line 226. The boilerplate is near the end of the block:

1. Find and delete the admin link check (line 536):
```js
if (localStorage.getItem('biw_token')) {
  document.getElementById('admin-link').style.display = 'block';
}
```

2. Find and delete the burger menu block (lines 540-557):
```js
const burgerBtn = document.getElementById('burger-btn');
// ... through to the last navMenu.querySelectorAll listener
```

3. Find and delete the updateBackendStatus block (lines 559-569):
```js
function updateBackendStatus() { ... }
updateBackendStatus();
setInterval(updateBackendStatus, 30000);
```

4. At the top of the `<script type="module">` block (after `import { API_URL } from './js/config.js';`), add:
```js
import { initBurgerMenu, initAdminLink, initBackendStatus } from './js/shared-ui.js';
initBurgerMenu();
initAdminLink();
initBackendStatus();
```

- [ ] **Step 2: Migrate team.html**

In `frontend/team.html`, the main `<script type="module">` starts at line 104.

1. Find and delete the admin link check (line 109):
```js
if (localStorage.getItem('biw_token')) { ... }
```

2. Find and delete the burger menu block (lines 114-131):
```js
const burgerBtn = document.getElementById('burger-btn');
// ... through to the last listener
```

3. Find and delete the updateBackendStatus block (lines 134-147):
```js
function updateBackendStatus() { ... }
updateBackendStatus();
setInterval(updateBackendStatus, 30000);
```

4. At the top of the `<script type="module">` block (after `import { API_URL } from './js/config.js';`), add:
```js
import { initBurgerMenu, initAdminLink, initBackendStatus } from './js/shared-ui.js';
initBurgerMenu();
initAdminLink();
initBackendStatus();
```

- [ ] **Step 3: Visual verification**

Open both pages. Verify burger menu, admin link, backend status all work.

- [ ] **Step 4: Commit**

```bash
git add frontend/dashboard.html frontend/team.html
git commit -m "refactor: migrate dashboard, team to shared-ui.js"
```

---

### Task 5: Migrate ewige-tabelle.html

**Files:**
- Modify: `frontend/ewige-tabelle.html:74` (main module) + `205-222` (status block)

- [ ] **Step 1: Replace imports and remove boilerplate**

In `frontend/ewige-tabelle.html`, the main `<script type="module">` starts at line 74.

1. Replace the opening lines (75-90):
```js
import { API_URL } from './js/config.js';
const API = API_URL;

let crestCache = {};

async function loadCrests() {
  try { crestCache = await fetch(`${API}/api/teams/crests`).then(r => r.json()); } catch(e) {}
}

function crestImg(teamId) {
  if (!teamId) return '';
  const url = crestCache[String(teamId)];
  if (!url) return '';
  const src = url.startsWith('http') ? url : `${API}${url}`;
  return `<img src="${src}" alt="" loading="lazy" style="width:20px;height:20px;object-fit:contain;vertical-align:middle;margin-right:4px;border-radius:3px;flex-shrink:0" onerror="this.style.display='none'">`;
}
```

With:
```js
import { API_URL } from './js/config.js';
import { initBurgerMenu, initAdminLink } from './js/shared-ui.js';
import { loadCrests, crestImg } from './js/team-utils.js';
const API = API_URL;

initBurgerMenu();
initAdminLink();
```

2. Delete the admin link check (lines 159-162):
```js
if (localStorage.getItem('biw_token')) {
  document.getElementById('admin-link').style.display = 'block';
}
```

3. Delete the burger menu block (lines 164-185).

4. Delete the separate backend status `<script type="module">` block after the footer (lines 205-222) and replace with:
```html
<script type="module">
import { initBackendStatus } from './js/shared-ui.js';
initBackendStatus();
</script>
```

**Note:** `crestImg()` calls in the page use no size argument (e.g., `crestImg(row.team_id)`), so they'll get the new default of 24px (was 20px). This is the intended uniform size.

- [ ] **Step 2: Visual verification**

Open ewige-tabelle.html. Verify:
- Table loads with crest images (now 24px)
- Burger menu works
- Backend status shows in footer

- [ ] **Step 3: Commit**

```bash
git add frontend/ewige-tabelle.html
git commit -m "refactor: migrate ewige-tabelle to shared-ui.js + team-utils.js"
```

---

### Task 6: Migrate ko.html

**Files:**
- Modify: `frontend/ko.html:102` (main module) + `403-420` (status block)

- [ ] **Step 1: Replace imports and remove boilerplate**

In `frontend/ko.html`, the main `<script type="module">` starts at line 102.

1. Replace the opening lines (103-121) — the `import`, `crestCache`, `loadCrests`, `crestImg` definitions:

```js
import { API_URL } from './js/config.js';
const API = API_URL;

let crestCache = {};
async function loadCrests() {
  try { crestCache = await fetch(`${API}/api/teams/crests`).then(r => r.json()); } catch(e) {}
}

function crestImg(teamId) {
  if (!teamId) return '';
  const url = crestCache[String(teamId)];
  if (!url) return '';
  const src = url.startsWith('http') ? url : `${API}${url}`;
  return `<img src="${src}" alt="" loading="lazy" style="width:20px;height:20px;object-fit:contain;vertical-align:middle;margin-right:4px;border-radius:3px;flex-shrink:0" onerror="this.style.display='none'">`;
}
```

With:
```js
import { API_URL } from './js/config.js';
import { initBurgerMenu, initAdminLink } from './js/shared-ui.js';
import { loadCrests, crestImg } from './js/team-utils.js';
const API = API_URL;

initBurgerMenu();
initAdminLink();
```

2. Delete the admin link check (line 361):
```js
if (localStorage.getItem('biw_token')) {
  document.getElementById('admin-link').style.display = 'block';
}
```

3. Delete the burger menu block (lines 365-383).

4. Delete the separate backend status `<script type="module">` block (lines 403-420) and replace with:
```html
<script type="module">
import { initBackendStatus } from './js/shared-ui.js';
initBackendStatus();
</script>
```

- [ ] **Step 2: Visual verification**

Open ko.html. Verify bracket renders with crests, burger menu, backend status.

- [ ] **Step 3: Commit**

```bash
git add frontend/ko.html
git commit -m "refactor: migrate ko to shared-ui.js + team-utils.js"
```

---

### Task 7: Migrate turnier.html

**Files:**
- Modify: `frontend/turnier.html:88` (main module) + `374-391` (status block)

- [ ] **Step 1: Replace imports and remove boilerplate**

In `frontend/turnier.html`, the main `<script type="module">` starts at line 88.

1. Replace the opening lines (89-121) — the `import`, `crestCache`, `loadCrests`, `crestImg`, `teamCache`, `teamName`, `loadTeams` definitions. The current code is:

```js
import { API_URL } from './js/config.js';
const API = API_URL;

let crestCache = {};

async function loadCrests() {
  try { crestCache = await fetch(`${API}/api/teams/crests`).then(r => r.json()); } catch(e) {}
}

function crestImg(teamId) {
  ...
}

let teamCache = {};

async function loadTeams(seasonId) {
  const groups = await fetch(`${API}/api/seasons/${seasonId}/groups-with-teams`).then(r => r.json());
  groups.forEach(g => g.teams.forEach(t => teamCache[t.id] = t.name));
  return groups;
}

function teamName(id) {
  return teamCache[id] || `Team ${id}`;
}
```

Replace with:
```js
import { API_URL } from './js/config.js';
import { initBurgerMenu, initAdminLink } from './js/shared-ui.js';
import { loadCrests, crestImg, teamName, registerTeams } from './js/team-utils.js';
const API = API_URL;

initBurgerMenu();
initAdminLink();

async function loadTeams(seasonId) {
  const groups = await fetch(`${API}/api/seasons/${seasonId}/groups-with-teams`).then(r => r.json());
  registerTeams(groups);
  return groups;
}
```

**Note:** `loadTeams()` stays as page-specific code because it fetches data — but now calls `registerTeams(groups)` instead of inline forEach. The `teamCache` variable, `teamName()`, `loadCrests()`, and `crestImg()` definitions are removed.

2. Delete the admin link check (line 329):
```js
if (localStorage.getItem('biw_token')) { ... }
```

3. Delete the burger menu block (lines 334-354).

4. Delete the separate backend status `<script type="module">` block (lines 374-391) and replace with:
```html
<script type="module">
import { initBackendStatus } from './js/shared-ui.js';
initBackendStatus();
</script>
```

- [ ] **Step 2: Visual verification**

Open turnier.html. Verify:
- Season selector works
- Table loads with crests (now 24px, was also 24px — no change here)
- Burger menu, backend status work

- [ ] **Step 3: Commit**

```bash
git add frontend/turnier.html
git commit -m "refactor: migrate turnier to shared-ui.js + team-utils.js"
```

---

### Task 8: Migrate archiv.html

**Files:**
- Modify: `frontend/archiv.html:99` (main module) + `530-547` (status block)

- [ ] **Step 1: Replace imports and remove boilerplate**

In `frontend/archiv.html`, the main `<script type="module">` starts at line 99.

1. Replace the opening lines (100-152) with the code below. This single replacement removes the admin link check (was ~118), burger menu block (was ~123-142), crestCache, loadCrests, crestImg, teamCache, teamName, and loadTeams definitions — all in one step:

```js
import { API_URL } from './js/config.js';
import { initBurgerMenu, initAdminLink } from './js/shared-ui.js';
import { loadCrests, crestImg, teamName, registerTeams } from './js/team-utils.js';
const API = API_URL;

initBurgerMenu();
initAdminLink();

async function loadTeams(seasonId) {
  const groups = await fetch(`${API}/api/seasons/${seasonId}/groups-with-teams`).then(r => r.json());
  registerTeams(groups);
  return groups;
}
```

2. **Important — module scope fix:** archiv.html uses `onclick="toggleSeason(${season.id})"` in innerHTML (line 486). Since the script is `type="module"`, `toggleSeason` is not on `window`. Add this line after the `toggleSeason` function definition:

```js
window.toggleSeason = toggleSeason;
```

Find the `function toggleSeason(seasonId)` definition and add `window.toggleSeason = toggleSeason;` right after the closing `}` of that function.

5. Delete the separate backend status `<script type="module">` block (lines 530-547) and replace with:
```html
<script type="module">
import { initBackendStatus } from './js/shared-ui.js';
initBackendStatus();
</script>
```

- [ ] **Step 2: Visual verification**

Open archiv.html. Verify:
- Season list loads
- Clicking a season expands it (toggleSeason works via window)
- Standings tables show crests
- KO brackets render
- Burger menu, backend status work

- [ ] **Step 3: Commit**

```bash
git add frontend/archiv.html
git commit -m "refactor: migrate archiv to shared-ui.js + team-utils.js"
```

---

### Task 9: Migrate index.html

The most complex page. Has burger/admin/status inline in the main module, plus crest/team functions and a KO team caching function.

**Files:**
- Modify: `frontend/index.html:165` (main module, runs through line 751)

- [ ] **Step 1: Replace imports and remove data function definitions**

In `frontend/index.html`, the main `<script type="module">` starts at line 165.

1. Replace lines 166-200 (imports + state + data loading functions):

Current code:
```js
import { API_URL } from './js/config.js';
const API = API_URL;

// --- Constants ---
const BRACKET_LABELS = { ... };

// --- State ---
let teamCache = {};
let crestCache = {};
let groupsData = [];
let allMatches = [];
let koBrackets = null;
let activeSeason = null;
let isKOPhase = false;

// --- Data Loading ---
async function loadCrests() { ... }
function crestImg(teamId, size = 20) { ... }
function teamName(id) { ... }
```

Replace with:
```js
import { API_URL } from './js/config.js';
import { initBurgerMenu, initAdminLink, initBackendStatus } from './js/shared-ui.js';
import { loadCrests, crestImg, teamName, registerTeams, registerTeam } from './js/team-utils.js';
const API = API_URL;

// --- Constants ---
const BRACKET_LABELS = { meister: 'Meister-Bracket', lucky_loser: 'Lucky Loser', loser: 'Trostpflaster' };

// --- State ---
let groupsData = [];
let allMatches = [];
let koBrackets = null;
let activeSeason = null;
let isKOPhase = false;
```

**Note:** `teamCache`, `crestCache`, `loadCrests`, `crestImg`, `teamName` definitions are removed. State variables that are page-specific (`groupsData`, `allMatches`, etc.) stay.

2. In `loadGroupsAndTeams()` (line 212-218), replace the teamCache population line:

Current:
```js
groupsData.forEach(g => g.teams.forEach(t => { teamCache[t.id] = t.name; }));
```

Replace with:
```js
registerTeams(groupsData);
```

3. In `cacheKOTeamNames()` (lines 411-422), replace `teamCache[m.home_team.id] = m.home_team.name` pattern:

Current:
```js
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
```

Replace with:
```js
function cacheKOTeamNames() {
  if (!koBrackets) return;
  for (const bracket of Object.values(koBrackets)) {
    if (!bracket || !bracket.rounds) continue;
    for (const matches of Object.values(bracket.rounds)) {
      matches.forEach(m => {
        if (m.home_team) registerTeam(m.home_team.id, m.home_team.name);
        if (m.away_team) registerTeam(m.away_team.id, m.away_team.name);
      });
    }
  }
}
```

- [ ] **Step 2: Remove boilerplate at end of module and add init calls**

1. Delete the admin link check (lines 708-711):
```js
if (localStorage.getItem('biw_token')) {
  document.getElementById('admin-link').style.display = 'block';
}
```

2. Delete the burger menu block (lines 713-730).

3. Delete the updateBackendStatus block (lines 732-750).

4. At the end of the module (where the boilerplate used to be, before `</script>`), add:
```js
// --- UI: Shared init ---
initBurgerMenu();
initAdminLink();
initBackendStatus();
```

**Why at the end?** index.html's main module is one big block — the init calls should be after the page-specific function definitions but still inside the module. The footer DOM elements are after the `</script>` tag, but `initBackendStatus()` has a null-guard and modules are deferred, so it will execute after full DOM parsing.

**Note on crestImg sizes:** index.html currently uses `crestImg(teamId, 20)` and `crestImg(row.team_id, 18)` in some places. With the new module, calls without a size arg get 24px (the new default). Calls that pass an explicit size keep that size. Review all `crestImg` calls on this page — if they previously used the old default of 20, they now get 24 unless explicitly passed 20.

- [ ] **Step 3: Visual verification**

Open index.html. Verify:
- Hero bar loads season data
- Tabs switch (Ergebnisse/News)
- Sidebar standings show with crests
- KO bracket tab works (if KO phase active)
- Burger menu, admin link, backend status all work

- [ ] **Step 4: Commit**

```bash
git add frontend/index.html
git commit -m "refactor: migrate index to shared-ui.js + team-utils.js"
```

---

### Task 10: Update frontend-todo.md

**Files:**
- Modify: `docs/frontend-todo.md`

- [ ] **Step 1: Mark Bereich B items as done**

In `docs/frontend-todo.md`, update the Bereich B section (lines 118-123):

```markdown
- [x] `js/shared-ui.js` erstellen (ES Module) mit: `initBurgerMenu()`, `initAdminLink()`, `initBackendStatus()`, `initThemeAndDarkMode()` → shared-ui.js mit 3 Funktionen (Theme bleibt separat in themes.js)
- [x] `js/team-utils.js` erstellen mit: `loadCrests()`, `crestImg()`, `teamName()`, `teamCache` → team-utils.js mit registerTeams/registerTeam
- [x] Alle Seiten: Boilerplate durch `import { initSharedUI } from './js/shared-ui.js'` ersetzen → 10 Seiten migriert auf ES Module Imports
- [x] Backend-Status-Script (separater `<script type="module">` Block am Ende jeder Seite) eliminieren → in shared-ui.js konsolidiert
```

- [ ] **Step 2: Add Umsetzungslog entry**

Add to the Umsetzungslog section (after last entry):

```markdown
- **2026-03-19: Bereich B (JS-Boilerplate konsolidieren) abgeschlossen** — `shared-ui.js` (Burger, Admin-Link, Backend-Status) und `team-utils.js` (Crests, Team-Cache) erstellt. 10 Seiten auf ES Module Imports migriert, ~250 Zeilen Duplication eliminiert.
```

- [ ] **Step 3: Commit**

```bash
git add docs/frontend-todo.md
git commit -m "docs: mark Bereich B (JS consolidation) as complete in frontend-todo"
```
