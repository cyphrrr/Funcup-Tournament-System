# `<fts-layout>` Web Component — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract duplicated Header/Nav/Footer HTML and shared JS init into a `<fts-layout>` Custom Element, reducing ~540 lines of boilerplate across 10 pages.

**Architecture:** Single Custom Element using Light DOM. `connectedCallback()` renders header/nav/footer, moves children into `<main>`, initializes shared UI. Pages keep `themes.js` and `background.js` in `<head>`, page-specific styles in `<style>`, and page-specific JS in their own `<script type="module">`.

**Tech Stack:** Vanilla JS, Custom Elements API (no Shadow DOM, no build)

**Spec:** `docs/superpowers/specs/2026-03-19-fts-layout-component-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `frontend/js/fts-layout.js` | Create | Custom Element definition |
| `frontend/index.html` | Modify | Remove header/nav/footer, wrap content in `<fts-layout>` |
| `frontend/turnier.html` | Modify | Same |
| `frontend/ko.html` | Modify | Same |
| `frontend/archiv.html` | Modify | Same |
| `frontend/ewige-tabelle.html` | Modify | Same |
| `frontend/dashboard.html` | Modify | Same |
| `frontend/team.html` | Modify | Same |
| `frontend/regeln.html` | Modify | Same |
| `frontend/datenschutz.html` | Modify | Same |
| `frontend/impressum.html` | Modify | Same |
| `docs/frontend-todo.md` | Modify | Mark Bereich C complete |

---

### Task 1: Create `fts-layout.js` Custom Element

**Files:**
- Create: `frontend/js/fts-layout.js`

- [ ] **Step 1: Create the component file**

```javascript
import { initBurgerMenu, initAdminLink, initBackendStatus } from './shared-ui.js';

class FTSLayout extends HTMLElement {
  connectedCallback() {
    if (this._initialized) return;
    this._initialized = true;

    const pageTitle = this.getAttribute('page-title') || '';

    // Collect existing children before we modify the DOM
    const children = [...this.childNodes];

    // Build the layout
    this.innerHTML = '';

    // Header
    const header = document.createElement('header');
    header.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center">
        <div style="display:flex;align-items:center;gap:1rem">
          <a href="index.html" style="text-decoration:none"><img src="img/logo_comic.png" alt="BIW Pokal Logo" style="height:50px;width:auto"></a>
          <div>
            <h1 style="font-family:'Outfit',sans-serif;font-size:1.3rem;font-weight:800;letter-spacing:-0.02em;margin:0;display:flex;align-items:center;gap:0.4rem">
              <span style="color:var(--text)">BIW</span><span style="color:var(--primary)">Pokal</span><span style="opacity:0.4;font-weight:400;font-size:1rem;margin-left:0.3rem">${pageTitle}</span>
            </h1>
            <p style="margin:0.15rem 0 0;font-family:'DM Sans',sans-serif;font-size:.8rem;color:var(--muted)">Die Besten im Westen</p>
          </div>
        </div>
        <div style="display:flex;align-items:center;gap:1rem">
          <input type="checkbox" class="dark-mode-toggle" id="dark-mode-toggle" aria-label="Dark Mode">
          <button class="burger-btn" id="burger-btn" aria-label="Menü öffnen">
            <span></span><span></span><span></span>
          </button>
        </div>
      </div>`;
    this.appendChild(header);

    // Menu overlay
    const overlay = document.createElement('div');
    overlay.className = 'menu-overlay';
    overlay.id = 'menu-overlay';
    this.appendChild(overlay);

    // Nav
    const nav = document.createElement('nav');
    nav.id = 'nav-menu';
    nav.innerHTML = `
      <ul>
        <li><a href="index.html">Start</a></li>
        <li><a href="regeln.html">Regeln</a></li>
        <li style="border-top:1px solid var(--border);margin-top:.5rem;padding-top:.5rem"><a href="dashboard.html">Mein Profil</a></li>
        <li style="border-top:1px solid var(--border);margin-top:.5rem;padding-top:.5rem"><a href="turnier.html">Gruppenphase</a></li>
        <li><a href="ko.html">KO\u2011Phase</a></li>
        <li style="border-top:1px solid var(--border);margin-top:.5rem;padding-top:.5rem"><a href="ewige-tabelle.html">Ewige Tabelle</a></li>
        <li><a href="archiv.html">Archiv</a></li>
        <li id="admin-link" style="display:none;border-top:1px solid var(--border);margin-top:.5rem;padding-top:.5rem"><a href="admin.html" style="color:var(--primary);font-weight:600">\ud83d\udd10 Admin</a></li>
      </ul>`;
    this.appendChild(nav);

    // Active nav link
    const currentPath = window.location.pathname.split('/').pop() || 'index.html';
    nav.querySelectorAll('a').forEach(link => {
      if (link.getAttribute('href') === currentPath) link.classList.add('active');
    });

    // Main — move original children here
    const main = document.createElement('main');
    children.forEach(child => main.appendChild(child));
    this.appendChild(main);

    // Footer
    const footer = document.createElement('footer');
    footer.innerHTML = `
      <div class="footer-left">
        <div class="backend-status">
          <span class="status-dot online" id="backend-status-dot"></span>
          <span id="backend-status-text">Backend verbunden</span>
        </div>
      </div>
      <div class="footer-center">
        <p style="margin:0">\u00a9 2026 BIW Pokal | <a href="impressum.html">Impressum</a> | <a href="datenschutz.html">Datenschutz</a></p>
      </div>
      <div class="footer-right" style="display:flex;align-items:center;gap:0.75rem;justify-content:flex-end">
        <span id="app-version" style="font-size:.75rem;opacity:.6"></span>
        <label for="theme-select" style="font-size:.8rem;color:var(--muted)">Theme:</label>
        <select id="theme-select"></select>
      </div>`;
    this.appendChild(footer);

    // Initialize shared UI
    initBurgerMenu();
    initAdminLink();
    initBackendStatus();

    // Load version display
    const versionEl = document.getElementById('app-version');
    if (versionEl) {
      import('./config.js').then(({ API_URL }) => {
        fetch(`${API_URL}/api/version`)
          .then(r => r.json())
          .then(data => {
            versionEl.textContent = `v${data.version}`;
            versionEl.title = `${data.app} ${data.version} (${data.status})`;
          })
          .catch(() => { versionEl.textContent = ''; });
      });
    }

    // Load page tracking
    import('./config.js').then(({ API_URL }) => {
      fetch(`${API_URL}/api/track`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: window.location.pathname })
      }).catch(() => {});
    });
  }
}

customElements.define('fts-layout', FTSLayout);
```

- [ ] **Step 2: Verify the file loads without errors**

Open any page in browser devtools console, manually add `<script type="module" src="js/fts-layout.js"></script>` — check no import errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/js/fts-layout.js
git commit -m "feat: create <fts-layout> Web Component"
```

---

### Task 2: Migrate `regeln.html` (simplest page — proof of concept)

**Files:**
- Modify: `frontend/regeln.html`

This is the simplest page (static content, no data fetching, no `setBackendStatus` calls). Use it to prove the component works.

- [ ] **Step 1: Rewrite `regeln.html`**

The page currently has: `<head>` → `<body>` → header → overlay → nav → `<main>` → `</main>` → script (burger/admin) → footer → script (backendStatus) → version.js → tracking.js.

Replace with: `<head>` (add fts-layout.js, remove nothing from head) → `<body>` → `<fts-layout>` → content only → `</fts-layout>`.

**Remove:**
- The entire `<header>...</header>` block
- The `<div class="menu-overlay" ...></div>`
- The `<nav id="nav-menu">...</nav>`
- The `<footer>...</footer>` block
- The `<script type="module">` block that imports `initBurgerMenu`, `initAdminLink` (before footer)
- The `<script type="module">` block that imports `initBackendStatus` (after footer)
- `<script src="js/version.js"></script>`
- `<script src="js/tracking.js"></script>`

**Add:**
- `<script type="module" src="js/fts-layout.js"></script>` in `<head>`
- Wrap remaining `<main>` content in `<fts-layout page-title="/ Regelwerk">`

The result should look like:

```html
<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8" />
  <link rel="icon" type="image/png" href="img/logo_comic.png">
  <title>Regelwerk – BIW Pokal</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="robots" content="noindex, nofollow" />
  <script src="js/themes.js"></script>
  <script type="module" src="js/background.js"></script>
  <script type="module" src="js/fts-layout.js"></script>
  <link rel="stylesheet" href="css/shared.css">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet"/>
  <style>
    /* ... page-specific styles stay as-is ... */
  </style>
</head>
<body>
  <fts-layout page-title="/ Regelwerk">
    <section>
      <!-- existing regeln content stays unchanged -->
    </section>
  </fts-layout>
</body>
</html>
```

- [ ] **Step 2: Test in browser**

1. Start backend: `cd backend && uvicorn app.main:app --reload --port 8000`
2. Start frontend: `cd frontend && python -m http.server 5500`
3. Open `http://127.0.0.1:5500/regeln.html`
4. Verify: Header shows "BIW Pokal / Regelwerk"
5. Verify: "Regeln" is highlighted in nav
6. Verify: Dark mode toggle works
7. Verify: Burger menu opens/closes
8. Verify: Footer shows backend status, version, theme selector
9. Verify: Admin link appears if `biw_token` is in localStorage

- [ ] **Step 3: Commit**

```bash
git add frontend/regeln.html
git commit -m "refactor: migrate regeln.html to <fts-layout>"
```

---

### Task 3: Migrate static pages (`datenschutz.html`, `impressum.html`)

**Files:**
- Modify: `frontend/datenschutz.html`
- Modify: `frontend/impressum.html`

Same pattern as regeln.html — these are static pages with no data fetching.

- [ ] **Step 1: Migrate `datenschutz.html`**

Same transformation as regeln.html:
- Add `<script type="module" src="js/fts-layout.js"></script>` to `<head>`
- Remove header, overlay, nav, footer, shared-ui script blocks, version.js, tracking.js
- Wrap content in `<fts-layout page-title="/ Datenschutz">`

- [ ] **Step 2: Migrate `impressum.html`**

Same transformation:
- Wrap content in `<fts-layout page-title="/ Impressum">`

- [ ] **Step 3: Test both pages in browser**

Verify header, nav (no active link for these — they're not in the nav), footer, dark mode, burger menu.

- [ ] **Step 4: Commit**

```bash
git add frontend/datenschutz.html frontend/impressum.html
git commit -m "refactor: migrate datenschutz + impressum to <fts-layout>"
```

---

### Task 4: Migrate data-fetching pages (`turnier.html`, `ko.html`, `ewige-tabelle.html`, `archiv.html`)

**Files:**
- Modify: `frontend/turnier.html`
- Modify: `frontend/ko.html`
- Modify: `frontend/ewige-tabelle.html`
- Modify: `frontend/archiv.html`

These pages have their own `<script type="module">` blocks that fetch data. The key change: **remove** `initBurgerMenu()`, `initAdminLink()`, `initBackendStatus()` imports/calls. **Keep** `setBackendStatus` import where used.

- [ ] **Step 1: Migrate `turnier.html`**

- Add `<script type="module" src="js/fts-layout.js"></script>` to `<head>`
- Remove header, overlay, nav, footer, footer script block (initBackendStatus), version.js, tracking.js
- Wrap content in `<fts-layout page-title="/ Turnier">`
- In the main `<script type="module">`: remove `initBurgerMenu`, `initAdminLink` imports and calls. Keep `setBackendStatus` import from `shared-ui.js`. Change import line from:
  ```javascript
  import { initBurgerMenu, initAdminLink, setBackendStatus } from './js/shared-ui.js';
  ```
  to:
  ```javascript
  import { setBackendStatus } from './js/shared-ui.js';
  ```
- Remove `initBurgerMenu();` and `initAdminLink();` calls

- [ ] **Step 2: Migrate `ko.html`**

Same pattern. Wrap in `<fts-layout page-title="/ KO-Phase">`. Keep `setBackendStatus` import.

- [ ] **Step 3: Migrate `ewige-tabelle.html`**

Same pattern. Wrap in `<fts-layout page-title="/ Ewige Tabelle">`. Keep `setBackendStatus` import.

- [ ] **Step 4: Migrate `archiv.html`**

Same pattern. Wrap in `<fts-layout page-title="/ Archiv">`. Keep `setBackendStatus` import. Remove footer script block.

- [ ] **Step 5: Test all four pages**

For each page:
1. Open in browser
2. Verify header with correct subtitle
3. Verify correct nav link is active
4. Verify data loads correctly (seasons, groups, standings, brackets)
5. Verify backend status updates on data load
6. Verify dark mode, burger menu, footer

- [ ] **Step 6: Commit**

```bash
git add frontend/turnier.html frontend/ko.html frontend/ewige-tabelle.html frontend/archiv.html
git commit -m "refactor: migrate turnier, ko, ewige-tabelle, archiv to <fts-layout>"
```

---

### Task 5: Migrate `dashboard.html` and `team.html`

**Files:**
- Modify: `frontend/dashboard.html`
- Modify: `frontend/team.html`

These pages import `initBackendStatus` directly in their main script block (not in a separate footer script). Remove those imports/calls.

- [ ] **Step 1: Migrate `dashboard.html`**

- Add `<script type="module" src="js/fts-layout.js"></script>` to `<head>`
- Remove header, overlay, nav, footer, version.js, tracking.js
- Wrap content in `<fts-layout page-title="/ Mein Profil">`
- In main `<script type="module">`: change import from:
  ```javascript
  import { initBurgerMenu, initAdminLink, initBackendStatus, setBackendStatus } from './js/shared-ui.js';
  ```
  to:
  ```javascript
  import { setBackendStatus } from './js/shared-ui.js';
  ```
- Remove `initBurgerMenu();`, `initAdminLink();`, `initBackendStatus();` calls

- [ ] **Step 2: Migrate `team.html`**

- Same pattern. Wrap in `<fts-layout page-title="/ Team">`
- Change import from:
  ```javascript
  import { initBurgerMenu, initAdminLink, initBackendStatus, setBackendStatus } from './js/shared-ui.js';
  ```
  to:
  ```javascript
  import { setBackendStatus } from './js/shared-ui.js';
  ```
- Remove `initBurgerMenu();`, `initAdminLink();`, `initBackendStatus();` calls
- **Keep** the page-specific `<style>` that overrides `header` — this works with Light DOM

- [ ] **Step 3: Test both pages**

- Dashboard: verify OAuth flow, profile display, backend status
- Team: verify team profile loads, header style override (different background), backend status

- [ ] **Step 4: Commit**

```bash
git add frontend/dashboard.html frontend/team.html
git commit -m "refactor: migrate dashboard + team to <fts-layout>"
```

---

### Task 6: Migrate `index.html`

**Files:**
- Modify: `frontend/index.html`

Most complex page — has hero-bar between nav and main, complex IIFE, many features.

- [ ] **Step 1: Migrate `index.html`**

- Add `<script type="module" src="js/fts-layout.js"></script>` to `<head>`
- Remove header, overlay, nav, footer, version.js, tracking.js
- Wrap content in `<fts-layout page-title="/ Start">` — this includes the hero-bar and main section. The hero-bar moves inside `<main>` (rendered by the component), which is fine.
- In main `<script type="module">`: change import from:
  ```javascript
  import { initBurgerMenu, initAdminLink, initBackendStatus, setBackendStatus } from './js/shared-ui.js';
  ```
  to:
  ```javascript
  import { setBackendStatus } from './js/shared-ui.js';
  ```
- Remove `initBurgerMenu();`, `initAdminLink();`, `initBackendStatus();` calls at the bottom of the script

- [ ] **Step 2: Test thoroughly**

1. Open `http://127.0.0.1:5500/index.html`
2. Verify: Hero-bar displays correctly (Saison, Phase, Spieltag, Teams)
3. Verify: Tabs work (Ergebnisse / News)
4. Verify: Sidebar shows standings
5. Verify: Header shows "BIW Pokal / Start"
6. Verify: "Start" is active in nav
7. Verify: Dark mode, burger menu, footer all work
8. Verify: Backend status updates after data load

- [ ] **Step 3: Commit**

```bash
git add frontend/index.html
git commit -m "refactor: migrate index.html to <fts-layout>"
```

---

### Task 7: Cleanup and documentation

**Files:**
- Modify: `docs/frontend-todo.md`

- [ ] **Step 1: Remove old version.js and tracking.js script tags check**

Verify no page still loads `<script src="js/version.js">` or `<script src="js/tracking.js">` directly:

```bash
grep -r 'src="js/version.js"' frontend/*.html
grep -r 'src="js/tracking.js"' frontend/*.html
```

Expected: Only `admin.html` (if any). No public pages.

- [ ] **Step 2: Verify no page still calls initBurgerMenu/initAdminLink/initBackendStatus**

```bash
grep -r 'initBurgerMenu\|initAdminLink\|initBackendStatus' frontend/*.html
```

Expected: No matches in public pages. Only `admin.html` if applicable.

- [ ] **Step 3: Update `docs/frontend-todo.md`**

Mark Bereich C as complete. Add Umsetzungslog entry:

Under Bereich C, change the section to show the chosen approach:

```markdown
### Bereich C: HTML-Templates

**Ziel:** Header/Nav/Footer dynamisch laden oder als Web Component.

**Lösung:** `<fts-layout>` Web Component (Light DOM, Custom Element)
- [x] `js/fts-layout.js` erstellt — rendert Header, Nav, Footer, initialisiert Shared UI
- [x] Alle 10 Public-Seiten migriert
- [x] Active Nav Link automatisch per URL
- [x] version.js + tracking.js in Komponente integriert
```

Add to Umsetzungslog:

```markdown
- **2026-03-19: Bereich C (HTML-Templates) abgeschlossen** — `<fts-layout>` Web Component (Light DOM) erstellt. 10 Seiten migriert, ~540 Zeilen Boilerplate eliminiert. Header/Nav/Footer nur noch in `fts-layout.js` gepflegt.
```

- [ ] **Step 4: Commit**

```bash
git add docs/frontend-todo.md
git commit -m "docs: mark Bereich C (HTML-Templates) as complete"
```
