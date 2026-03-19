# CSS Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract ~490 lines of duplicated CSS from 10 public HTML pages into a single `frontend/css/shared.css`, eliminating copy-paste maintenance across the frontend.

**Architecture:** Create one flat CSS file with 8 logical sections (Reset, Header, Burger/Toggle, Layout, Cards, Tables, Match Score/Utilities, Footer). Each HTML page keeps only its page-specific styles inline. Inline overrides handle per-page deviations (e.g. different max-width, flat header on team.html).

**Tech Stack:** Vanilla CSS, no build tools, no preprocessor.

**Spec:** `docs/superpowers/specs/2026-03-19-css-consolidation-design.md`

**Verification method:** After each task, open the modified page in the browser side-by-side with the backend running (`uvicorn app.main:app --port 8000` in `backend/`). The page must look visually identical to before the change. Check both light and dark mode.

**Known intentional visual changes from shared defaults:**
- Global `a{text-decoration:underline}` — pages that previously had no global `a` styles (regeln, ewige-tabelle, archiv, turnier, ko) will gain underlined links. This is intentional harmonization.
- `td{text-align:center}` — pages that relied on browser-default left-align (turnier, ko) will get centered table cells. Verify this looks correct.
- `a:hover{opacity:.8}` — new hover effect on pages that didn't have it. Pages needing `opacity:1` include datenschutz, impressum, team (added in their inline overrides).
- `.loading{padding:2rem}` — ewige-tabelle previously used 3rem. Minor change, acceptable.

---

### Task 1: Create `shared.css`

**Files:**
- Create: `frontend/css/shared.css`

- [ ] **Step 1: Create `frontend/css/` directory and `shared.css`**

Write the complete shared.css with all 8 sections as specified in the design spec. Use the exact CSS from the spec document, sections 1-8:

1. Reset & Basis (box-sizing, body, fonts, body::before with `url('../img/logo-bg.png')`, global `a` styles, `h2`)
2. Header (gradient, sticky, `header h1`, `header p`)
3. Burger Menu & Dark Mode Toggle (burger-btn, dark-mode-toggle, menu-overlay, nav panel)
4. Layout (`main{max-width:1200px}`)
5. Cards (.card, .card-header, .card-title, .card-sub, .card h2)
6. Tables (table, th, td with `text-align:center`, tr:hover, tr.leader)
7. Match Score & Utilities (.match-score, .loading, .empty-state)
8. Footer (footer grid, status-dot, theme-select, mobile media query)

- [ ] **Step 2: Commit**

```bash
git add frontend/css/shared.css
git commit -m "feat: create shared.css with common styles from 10 public pages"
```

---

### Task 2: Migrate `regeln.html`

Einfachste Seite zum Starten — nutzt Standard-Header, Standard-Cards, keine JS-Logik.

**Files:**
- Modify: `frontend/regeln.html`

- [ ] **Step 1: Replace `<head>` block**

Replace everything from `<script src="js/themes.js">` through the closing `</style>` with:

```html
<script src="js/themes.js"></script>
<script type="module" src="js/background.js"></script>
<link rel="stylesheet" href="css/shared.css">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet"/>
<style>
  main{max-width:900px}
  h2{margin:2rem 0 1rem;font-size:1.5rem}
  h3{margin:1.5rem 0 .75rem;font-size:1.2rem;color:var(--primary)}
  .card{line-height:1.7}
  .card h3{margin-top:0}
  .card ul{margin:.5rem 0;padding-left:1.5rem}
  .card li{margin:.5rem 0}
  .card strong{color:var(--text);font-weight:600}
  .intro{font-size:1.1rem;color:var(--muted);margin-bottom:2rem;line-height:1.6}
</style>
```

- [ ] **Step 2: Verify in browser**

Open `regeln.html` in browser. Compare light mode and dark mode. Note: links will now be underlined (new shared `a` default) — this is intentional.

- [ ] **Step 3: Commit**

```bash
git add frontend/regeln.html
git commit -m "refactor: migrate regeln.html to shared.css"
```

---

### Task 3: Migrate `datenschutz.html`

**Files:**
- Modify: `frontend/datenschutz.html`

- [ ] **Step 1: Replace `<head>` block**

Same pattern as Task 2. Page-specific inline styles:

```html
<style>
  main{max-width:900px}
  h2{margin:2rem 0 1rem;font-size:1.5rem}
  h3{margin:1.5rem 0 .75rem;font-size:1.2rem;color:var(--primary)}
  .card{line-height:1.7}
  .card h2{margin-top:0}
  .card h3{margin-top:0}
  .card p{margin:.5rem 0}
  .card ul{margin:.5rem 0;padding-left:1.5rem}
  .card li{margin:.5rem 0}
  a{text-decoration:none}
  a:hover{text-decoration:underline;opacity:1}
</style>
```

- [ ] **Step 2: Verify in browser**

- [ ] **Step 3: Commit**

```bash
git add frontend/datenschutz.html
git commit -m "refactor: migrate datenschutz.html to shared.css"
```

---

### Task 4: Migrate `impressum.html`

**Files:**
- Modify: `frontend/impressum.html`

- [ ] **Step 1: Replace `<head>` block**

Same as datenschutz, **plus remove the hardcoded `:root` block** (lines 13-18 in current file). The `themes.js` script handles all CSS variables.

Page-specific inline styles (same as datenschutz):

```html
<style>
  main{max-width:900px}
  h2{margin:2rem 0 1rem;font-size:1.5rem}
  h3{margin:1.5rem 0 .75rem;font-size:1.2rem;color:var(--primary)}
  .card{line-height:1.7}
  .card h2{margin-top:0}
  .card h3{margin-top:0}
  .card p{margin:.5rem 0}
  .card ul{margin:.5rem 0;padding-left:1.5rem}
  .card li{margin:.5rem 0}
  a{text-decoration:none}
  a:hover{text-decoration:underline;opacity:1}
</style>
```

- [ ] **Step 2: Verify in browser** — especially check that theme switching still works (the `:root` removal must not break anything)

- [ ] **Step 3: Commit**

```bash
git add frontend/impressum.html
git commit -m "refactor: migrate impressum.html to shared.css, remove hardcoded :root"
```

---

### Task 5: Migrate `ewige-tabelle.html`

**Files:**
- Modify: `frontend/ewige-tabelle.html`

- [ ] **Step 1: Replace `<head>` block**

Page-specific inline styles:

```html
<style>
  th{position:sticky;top:0;background:var(--card);z-index:10}
  @media(min-width:769px){th{top:72px}}
  td:first-child,th:first-child{text-align:left;padding-left:1rem}
  tr.top3{background:var(--card-alt)}
  tr.top1{font-weight:700;color:var(--primary)}
  .rank{font-weight:700;color:var(--primary);min-width:40px}
</style>
```

- [ ] **Step 2: Verify in browser** — check sticky header scroll behavior. Note: links gain underlines (intentional). `.loading` padding changes from 3rem to 2rem (minor, acceptable).

- [ ] **Step 3: Commit**

```bash
git add frontend/ewige-tabelle.html
git commit -m "refactor: migrate ewige-tabelle.html to shared.css"
```

---

### Task 6: Migrate `archiv.html`

**Files:**
- Modify: `frontend/archiv.html`

- [ ] **Step 1: Replace `<head>` block**

Page-specific inline styles — keep all archiv-specific components:

```html
<style>
  /* Season Cards */
  .season-card{background:var(--card);border:1px solid var(--border);border-radius:12px;margin-bottom:1.5rem;overflow:hidden;transition:box-shadow .2s}
  .season-card:hover{box-shadow:0 8px 24px rgba(0,0,0,.1)}
  .season-header{padding:1.25rem 1.5rem;cursor:pointer;display:flex;justify-content:space-between;align-items:center;user-select:none}
  .season-header:hover{background:var(--card-alt)}
  .season-info{display:flex;align-items:center;gap:1rem}
  .season-name{font-size:1.2rem;font-weight:700}
  .season-meta{display:flex;gap:1rem;align-items:center;font-size:.85rem;color:var(--muted)}
  .season-badge{padding:.25rem .6rem;border-radius:6px;font-size:.75rem;font-weight:600}
  .season-badge.active{background:#dcfce7;color:#166534}
  .season-badge.archived{background:var(--card-alt);color:var(--muted)}
  .season-badge.planned{background:#dbeafe;color:#1e40af}
  .season-toggle{font-size:1.2rem;color:var(--muted);transition:transform .3s}
  .season-toggle.open{transform:rotate(180deg)}
  .season-content{display:none;padding:0 1.5rem 1.5rem;border-top:1px solid var(--border)}
  .season-content.open{display:block}
  /* Compact Table */
  .compact-table{font-size:.85rem}
  .compact-table th{font-size:.75rem}
  .compact-table td{padding:.4rem .5rem}
  /* KO Bracket Compact */
  .ko-bracket-compact{display:flex;gap:1.5rem;overflow-x:auto;padding:1rem 0;font-size:.85rem}
  .ko-round-compact{min-width:150px;display:flex;flex-direction:column;gap:.5rem}
  .ko-round-header-compact{text-align:center;font-size:.8rem;font-weight:600;color:var(--muted);margin-bottom:.5rem}
  .ko-match-compact{background:var(--card-alt);border:1px solid var(--border);border-radius:6px;padding:.5rem;font-size:.8rem}
  .ko-match-compact.played{border-left:3px solid var(--success)}
  .ko-team-compact{display:flex;justify-content:space-between;padding:.2rem 0}
  .ko-team-compact.winner{font-weight:700;color:var(--success)}
  /* Champion Badge */
  .champion-badge{background:linear-gradient(135deg,#fbbf24 0%,#f59e0b 100%);color:#78350f;padding:.5rem 1rem;border-radius:8px;font-weight:700;display:inline-flex;align-items:center;gap:.5rem;font-size:.9rem;margin-bottom:1rem}
</style>
```

- [ ] **Step 2: Verify in browser** — expand a season, check tables and KO bracket display. Note: links gain underlines (intentional).

- [ ] **Step 3: Commit**

```bash
git add frontend/archiv.html
git commit -m "refactor: migrate archiv.html to shared.css"
```

---

### Task 7: Migrate `turnier.html`

**Files:**
- Modify: `frontend/turnier.html`

- [ ] **Step 1: Replace `<head>` block**

Page-specific inline styles:

```html
<style>
  td:first-child,th:first-child{text-align:center;width:40px;font-weight:600}
  td:nth-child(2),th:nth-child(2){text-align:left}
  .seasons-grid{display:flex;flex-wrap:wrap;gap:.5rem;margin-top:.75rem}
  .season-item{padding:.5rem 1rem;cursor:pointer;border-radius:8px;transition:all .2s;background:var(--card);border:1px solid var(--border);font-size:.9rem;white-space:nowrap}
  .season-item:hover{background:color-mix(in srgb,var(--primary) 10%,var(--card));border-color:var(--primary);transform:translateY(-2px);box-shadow:0 4px 12px rgba(0,0,0,.1)}
  .season-item.active{background:color-mix(in srgb,var(--primary) 15%,var(--card));color:var(--primary);font-weight:600;border-color:var(--primary)}
  /* Matches */
  .matches-section{margin-top:1.5rem;padding-top:1rem;border-top:1px solid var(--border)}
  .matchday-group{margin-bottom:1rem}
  .matchday-title{font-size:.85rem;font-weight:600;color:var(--muted);margin-bottom:.5rem;text-transform:uppercase}
  .match-header{display:grid;grid-template-columns:1fr auto 1fr auto;gap:.75rem;align-items:center;padding:.5rem .75rem;margin-bottom:.5rem;background:var(--card);border:1px solid var(--border);border-radius:6px;font-size:.8rem;font-weight:600;color:var(--muted);text-transform:uppercase}
  .match-header-home{text-align:right}
  .match-header-score{text-align:center}
  .match-header-away{text-align:left}
  .match-item{display:grid;grid-template-columns:1fr auto 1fr auto;gap:.75rem;align-items:center;padding:.5rem .75rem;margin-bottom:.25rem;background:var(--card-alt);border-radius:6px;font-size:.9rem}
  .match-home{text-align:right}
  .match-score.scheduled{color:var(--muted)}
  .match-score.played{color:var(--bg)}
  .match-away{text-align:left}
  .match-info{text-align:right;font-size:.8rem;color:var(--muted);white-space:nowrap}
</style>
```

- [ ] **Step 2: Verify in browser** — select a season, check standings table alignment and match display. Note: `td{text-align:center}` from shared.css may change alignment of columns that were previously browser-default (left). Verify this looks correct for all table columns.

- [ ] **Step 3: Commit**

```bash
git add frontend/turnier.html
git commit -m "refactor: migrate turnier.html to shared.css"
```

---

### Task 8: Migrate `ko.html`

**Files:**
- Modify: `frontend/ko.html`

- [ ] **Step 1: Replace `<head>` block**

Page-specific inline styles:

```html
<style>
  main{max-width:1400px}
  .season-item{padding:.5rem;margin:.25rem 0;cursor:pointer;border-radius:6px;transition:background .2s;display:inline-block}
  .season-item:hover{background:color-mix(in srgb,var(--primary) 10%,var(--card))}
  .season-item.active{background:color-mix(in srgb,var(--primary) 15%,var(--card));color:var(--primary);font-weight:600}
  /* Bracket Container */
  #ko-container{background:var(--card);border-radius:12px;border:1px solid var(--border);padding:1.5rem;box-shadow:0 4px 16px rgba(0,0,0,.04);margin-bottom:2rem}
  #ko-container em{display:block;text-align:center;color:var(--muted);padding:1rem}
  /* Tabs */
  .bracket-tabs{display:flex;gap:.5rem;margin-bottom:1.5rem;padding:0;flex-wrap:wrap}
  .bracket-tab{padding:.5rem 1rem;cursor:pointer;border:none;background:var(--card-alt);color:var(--text);font-size:.95rem;font-weight:500;border-radius:8px;transition:all .2s}
  .bracket-tab:hover{background:var(--muted);color:#fff}
  .bracket-tab.active{background:var(--primary);color:#fff;font-weight:700}
  /* KO Bracket */
  .ko-bracket{display:flex;gap:2rem;overflow-x:auto;padding:1rem 0;align-items:flex-start}
  .ko-round{min-width:180px;max-width:220px;display:flex;flex-direction:column;justify-content:space-around}
  .ko-round-header{text-align:center;margin:0 0 1rem;font-size:.95rem;font-weight:600;background:var(--card-alt);border-radius:8px;padding:.4rem .75rem;display:inline-block;color:var(--text)}
  .ko-match{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:.65rem .85rem;margin-bottom:.75rem;font-size:.85rem;position:relative;min-height:60px;display:flex;flex-direction:column;justify-content:center}
  .ko-match.bye{background:color-mix(in srgb,var(--primary) 10%,var(--card));border-style:dashed}
  .ko-match.played{border-left:3px solid var(--success)}
  .ko-match.pending{border-left:3px solid var(--primary)}
  .ko-match-team{display:flex;justify-content:space-between;align-items:center;padding:2px 0}
  .ko-match-team.winner{font-weight:700;color:var(--success)}
  .ko-match-team.loser{color:var(--muted)}
  .ko-match-team .name{flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .ko-match-team .score{min-width:20px;text-align:right;font-weight:600}
  .ko-match-vs{font-size:.7rem;color:var(--muted);text-align:center;margin:2px 0}
  .ko-match-tbd{color:var(--muted);font-style:italic;text-align:center}
  .ko-match-bye-badge{font-size:.7rem;color:var(--muted);text-align:center;background:var(--card-alt);border-radius:4px;padding:1px 6px;margin-top:2px;display:inline-block}
  .ko-match::after{content:"";position:absolute;right:-1rem;top:50%;width:1rem;height:1px;background:var(--border)}
  .ko-round:last-child .ko-match::after{display:none}
  .ko-empty{text-align:center;padding:2rem;color:var(--muted)}
  .ko-third-place{border-left:2px dashed var(--border);padding-left:1.5rem}
  .ko-third-place .ko-round-header{background:color-mix(in srgb,var(--primary) 10%,var(--card));font-style:italic}
</style>
```

- [ ] **Step 2: Verify in browser** — check bracket rendering, tab switching, connectors. Note: if page uses tables, `td{text-align:center}` is now default from shared.css.

- [ ] **Step 3: Commit**

```bash
git add frontend/ko.html
git commit -m "refactor: migrate ko.html to shared.css"
```

---

### Task 9: Migrate `dashboard.html`

**Files:**
- Modify: `frontend/dashboard.html`

- [ ] **Step 1: Replace `<head>` block**

Page-specific inline styles — this page has the most unique CSS (login, profile, forms, toasts):

```html
<style>
  main{max-width:800px}
  h2{margin-bottom:1rem}
  /* Login Screen */
  .login-screen{text-align:center;padding:4rem 2rem}
  .login-screen h2{font-size:1.5rem;margin-bottom:.5rem}
  .login-screen p{color:var(--muted);margin-bottom:2rem}
  .discord-login-btn{display:inline-flex;align-items:center;gap:.75rem;background:#5865F2;color:#fff;border:none;border-radius:10px;padding:.85rem 2rem;font-size:1rem;font-weight:600;cursor:pointer;transition:background .2s,transform .1s;text-decoration:none}
  .discord-login-btn:hover{background:#4752C4;transform:translateY(-1px)}
  .discord-login-btn:active{transform:translateY(0)}
  .discord-login-btn:visited{color:#fff}
  .discord-login-btn svg{width:24px;height:24px}
  /* Profile Header */
  .profile-header{display:flex;align-items:center;gap:1.25rem;margin-bottom:.5rem}
  .profile-avatar{width:64px;height:64px;border-radius:50%;border:3px solid var(--primary);object-fit:cover}
  .profile-info h2{margin:0;font-size:1.3rem}
  .profile-info p{margin:.25rem 0 0;color:var(--muted);font-size:.9rem}
  /* Badges */
  .badge{display:inline-block;padding:.25rem .75rem;border-radius:20px;font-size:.8rem;font-weight:600}
  .badge-success{background:#dcfce7;color:#166534}
  .badge-danger{background:#fee2e2;color:#991b1b}
  .badge-muted{background:var(--card-alt);color:var(--muted)}
  /* Forms */
  .form-group{margin-bottom:1.25rem}
  .form-group label{display:block;font-weight:600;margin-bottom:.4rem;font-size:.9rem}
  .form-group .hint{color:var(--muted);font-size:.8rem;margin-top:.25rem}
  input[type="text"],input[type="url"]{width:100%;padding:.6rem .85rem;border:1px solid var(--border);border-radius:8px;font-size:.95rem;background:var(--bg);color:var(--text);transition:border-color .2s}
  input[type="text"]:focus,input[type="url"]:focus{outline:none;border-color:var(--primary)}
  .btn{display:inline-flex;align-items:center;gap:.5rem;padding:.6rem 1.25rem;border:none;border-radius:8px;font-size:.9rem;font-weight:600;cursor:pointer;transition:background .2s,opacity .2s}
  .btn:disabled{opacity:.5;cursor:not-allowed}
  .btn-primary{background:var(--primary);color:#fff}
  .btn-primary:hover:not(:disabled){background:#059669}
  .btn-danger{background:var(--danger);color:#fff}
  .btn-danger:hover:not(:disabled){background:#b91c1c}
  .btn-outline{background:transparent;border:1px solid var(--border);color:var(--text)}
  .btn-outline:hover:not(:disabled){background:var(--card-alt)}
  /* Toggle Switch */
  .toggle-row{display:flex;align-items:center;justify-content:space-between;padding:.75rem 0}
  .toggle-label{font-weight:600;font-size:.95rem}
  .toggle-sub{color:var(--muted);font-size:.8rem}
  .toggle-switch{position:relative;width:52px;height:28px;cursor:pointer}
  .toggle-switch input{opacity:0;width:0;height:0}
  .toggle-slider{position:absolute;top:0;left:0;right:0;bottom:0;background:var(--border);border-radius:14px;transition:background .3s}
  .toggle-slider::before{content:"";position:absolute;width:22px;height:22px;left:3px;bottom:3px;background:#fff;border-radius:50%;transition:transform .3s}
  .toggle-switch input:checked + .toggle-slider{background:var(--primary)}
  .toggle-switch input:checked + .toggle-slider::before{transform:translateX(24px)}
  /* Crest Upload */
  .crest-preview{width:128px;height:128px;border-radius:12px;border:2px dashed var(--border);display:flex;align-items:center;justify-content:center;overflow:hidden;background:var(--bg);margin-bottom:1rem;position:relative}
  .crest-preview img{width:100%;height:100%;object-fit:contain}
  .crest-preview .placeholder{color:var(--muted);font-size:.8rem;text-align:center;padding:.5rem}
  .crest-upload-area{display:flex;align-items:flex-start;gap:1.5rem}
  .crest-actions{display:flex;flex-direction:column;gap:.5rem}
  /* Team Search */
  .team-search-results{max-height:200px;overflow-y:auto;border:1px solid var(--border);border-radius:8px;margin-top:.5rem;display:none}
  .team-search-results.visible{display:block}
  .team-result{padding:.6rem .85rem;cursor:pointer;transition:background .15s;border-bottom:1px solid var(--border);font-size:.9rem}
  .team-result:last-child{border-bottom:none}
  .team-result:hover{background:var(--card-alt)}
  .team-current{display:flex;align-items:center;gap:.75rem;padding:.75rem;background:color-mix(in srgb,var(--primary) 10%,var(--card));border-radius:8px;margin-bottom:1rem}
  .team-current-logo{width:32px;height:32px;border-radius:4px;object-fit:contain}
  /* Toast */
  .toast{position:fixed;bottom:2rem;right:2rem;padding:.85rem 1.25rem;border-radius:10px;font-size:.9rem;font-weight:500;color:#fff;z-index:200;transform:translateY(100px);opacity:0;transition:all .3s}
  .toast.visible{transform:translateY(0);opacity:1}
  .toast-success{background:var(--success)}
  .toast-error{background:#dc2626}
  /* Logout */
  .logout-row{display:flex;justify-content:flex-end;margin-top:1rem}
</style>
```

- [ ] **Step 2: Verify in browser** — check login screen, profile page (if logged in), form elements

- [ ] **Step 3: Commit**

```bash
git add frontend/dashboard.html
git commit -m "refactor: migrate dashboard.html to shared.css"
```

---

### Task 10: Migrate `team.html`

Höchstes Risiko — hat abweichenden Header, Cards und Match-Score.

**Files:**
- Modify: `frontend/team.html`

- [ ] **Step 1: Replace `<head>` block**

Page-specific inline styles — includes overrides for header, card, match-score:

```html
<style>
  /* Overrides: flat header */
  header{background:var(--card);border-bottom:1px solid var(--border);box-shadow:none}
  main{max-width:900px}
  a{text-decoration:none}
  a:hover{text-decoration:underline;opacity:1}
  .back-link{display:inline-flex;align-items:center;gap:.5rem;color:var(--muted);font-size:.9rem;margin-bottom:1.5rem}
  .back-link:hover{color:var(--primary)}
  /* Team Header */
  .team-header{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:2rem;margin-bottom:2rem;display:flex;flex-direction:column;align-items:center;gap:1rem;text-align:center}
  .team-logo{width:160px;height:160px;border-radius:12px;background:color-mix(in srgb,var(--primary) 10%,var(--card));display:flex;align-items:center;justify-content:center;font-size:4rem;font-weight:700;color:var(--primary);flex-shrink:0;border:1px solid var(--border)}
  .team-logo img{width:100%;height:100%;object-fit:cover;border-radius:10px}
  .team-name{font-size:2rem;font-weight:700;margin:0}
  .team-buttons{display:flex;gap:.5rem;justify-content:center}
  .team-buttons button,.team-buttons a{padding:.5rem 1rem;border-radius:8px;text-decoration:none;font-weight:600;font-size:.9rem}
  .team-meta{display:flex;gap:1rem;color:var(--muted);font-size:.9rem}
  .team-meta a{color:var(--primary);text-decoration:none}
  .team-meta a:hover{text-decoration:underline}
  /* Stats Cards */
  .stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:1rem;margin-bottom:2rem}
  .stat-card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:1rem;text-align:center}
  .stat-value{font-size:1.8rem;font-weight:700;font-family:'Outfit',sans-serif;color:var(--primary)}
  .stat-label{font-size:.8rem;color:var(--muted);margin-top:.25rem}
  /* Override: flat cards */
  .card{background:var(--card);border-top:1px solid var(--border);border-top-left-radius:12px;border-top-right-radius:12px;box-shadow:0 4px 16px rgba(0,0,0,.04)}
  .card h2{margin:0 0 1rem;font-size:1.2rem}
  /* Match List */
  .match-list{display:flex;flex-direction:column;gap:.75rem}
  .match-item{background:var(--card-alt);border:1px solid var(--border);border-radius:10px;padding:1rem;display:flex;justify-content:space-between;align-items:center}
  .match-item.win{border-left:4px solid var(--success)}
  .match-item.loss{border-left:4px solid var(--danger)}
  .match-item.draw{border-left:4px solid var(--warning)}
  .match-item.scheduled{border-left:4px solid var(--muted)}
  .match-teams{flex:1}
  /* Override: inverted match-score */
  .match-score{background:var(--card-alt);color:var(--primary);box-shadow:none}
  .match-result{font-size:1.2rem;font-weight:700;min-width:60px;text-align:center}
  .match-result.win{color:var(--success)}
  .match-result.loss{color:var(--danger)}
  .match-result.draw{color:var(--warning)}
  .match-badge{font-size:.75rem;color:var(--muted);margin-top:.25rem}
  .opponent-link{color:var(--primary);text-decoration:none;font-weight:600}
  .opponent-link:hover{text-decoration:underline}
</style>
```

- [ ] **Step 2: Verify in browser** — critical: check flat header (no gradient/shadow), flat cards, inverted match scores. Compare carefully with current state.

- [ ] **Step 3: Commit**

```bash
git add frontend/team.html
git commit -m "refactor: migrate team.html to shared.css with flat header/card overrides"
```

---

### Task 11: Migrate `index.html`

**Files:**
- Modify: `frontend/index.html`

- [ ] **Step 1: Replace `<head>` block**

Page-specific inline styles — Hero Bar, Tabs, Accordions, Match Rows, Content Grid, Compact Standings, Mini Bracket:

```html
<style>
  h2{margin-bottom:1rem}

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

  /* Match Rows */
  .match-row{display:flex;align-items:center;padding:.5rem 0;border-bottom:1px solid var(--border)}
  .match-row:last-child{border-bottom:none}
  .match-team{flex:1;font-size:.85rem;font-weight:500;display:inline-flex;align-items:center}
  .match-team.home{justify-content:flex-end;text-align:right}
  .match-team.away{justify-content:flex-start;text-align:left}
  .match-score-center{margin:0 .5rem;min-width:50px;text-align:center}
  .matchday-label{font-size:.75rem;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:0.04em;margin-bottom:.5rem;margin-top:.25rem}

  /* Content Grid */
  .content-grid{display:grid;grid-template-columns:2fr 1fr;gap:1.5rem;align-items:start}
  @media(max-width:768px){.content-grid{grid-template-columns:1fr}}

  /* Compact Standings */
  .compact-standings{background:linear-gradient(145deg,var(--card) 0%,var(--card-alt) 100%);border:1px solid var(--border);border-radius:12px;padding:1rem;margin-bottom:1rem;font-size:.85rem;box-shadow:0 2px 8px rgba(0,0,0,.04),inset 0 1px 0 color-mix(in srgb,var(--primary) 12%,transparent)}
  .compact-standings h3{margin:0 0 .75rem;font-size:.95rem;font-weight:600}
  .compact-standings table{margin:0;font-size:.85rem}
  .compact-standings th{font-size:.75rem;padding:.4rem .5rem}
  .compact-standings td{padding:.4rem .5rem}
  .compact-standings .pos{font-weight:700;color:var(--primary);width:30px}

  /* Mini KO Bracket */
  .mini-bracket{margin-top:.5rem}
  .mini-match-card{background:var(--card);border:1px solid var(--border);border-radius:6px;padding:.4rem .6rem;font-size:.75rem;min-width:100px;flex:1}
  .mini-match-card .mini-team-row{display:flex;justify-content:space-between;padding:2px 0}
  .mini-match-card .mini-team-row.winner{color:var(--primary);font-weight:700}
  .mini-connector{color:var(--muted);font-size:.9rem;flex-shrink:0}
  .bracket-label{font-size:.8rem;font-weight:700;color:var(--primary);margin:1rem 0 .25rem;font-family:'Outfit',sans-serif}
  .bracket-label:first-child{margin-top:0}
  .bracket-link{display:block;text-align:center;margin-top:.75rem;font-size:.8rem;color:var(--primary);text-decoration:none}
  .bracket-link:hover{text-decoration:underline}
</style>
```

- [ ] **Step 2: Verify in browser** — check Hero Bar, both tabs, accordion open/close, sidebar standings and mini bracket

- [ ] **Step 3: Commit**

```bash
git add frontend/index.html
git commit -m "refactor: migrate index.html to shared.css"
```

---

### Task 12: Final verification & cleanup

- [ ] **Step 1: Open every page and verify**

Check all 10 pages in both light and dark mode. Quick checklist:
- Header: gradient, sticky scroll, logo
- Burger menu: opens/closes
- Dark mode toggle: switches theme
- Footer: backend status, version, theme selector
- Cards, tables, match scores look correct
- Page-specific elements unchanged

- [ ] **Step 2: Check `.gitignore` for `.superpowers/`**

Add `.superpowers/` to `.gitignore` if not already there (brainstorm session files).

- [ ] **Step 3: Update `frontend-todo.md`**

Add entry to Umsetzungslog in `docs/frontend-todo.md`:
```
- **2026-03-19: Bereich A (CSS konsolidieren) abgeschlossen** — `css/shared.css` erstellt, 10 Seiten migriert, ~490 Zeilen Duplication eliminiert
```

Mark Bereich A checkboxes as done.

- [ ] **Step 4: Final commit**

```bash
git add docs/frontend-todo.md .gitignore
git commit -m "docs: mark CSS consolidation complete in frontend-todo"
```
