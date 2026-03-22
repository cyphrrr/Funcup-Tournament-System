# CSS Consolidation Design Spec

> Eliminiert ~490 Zeilen CSS-Duplication über 10 Public-Seiten durch Auslagerung in eine gemeinsame `shared.css`.

## Entscheidungen

| Frage | Entscheidung |
|-------|-------------|
| Strategie | Eine `shared.css` + seitenspezifisches CSS bleibt inline |
| Dateistruktur | Flach, eine Datei mit Kommentar-Sektionen |
| Inkonsistenzen | Sinnvolle Defaults in shared, Abweichungen inline |

## Scope

**In Scope:** 10 Public-Seiten (index, turnier, ko, dashboard, archiv, ewige-tabelle, team, regeln, datenschutz, impressum)
**Out of Scope:** admin.html (eigenes CSS-System, dark-only Theme)

**Voraussetzung:** Verzeichnis `frontend/css/` muss erstellt werden.

## Neue Datei: `frontend/css/shared.css`

Flache Datei, 8 Sektionen mit Kommentar-Headern:

### Sektion 1 — Reset & Basis

```css
/* === Reset & Basis === */
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;font-family:'DM Sans',system-ui,-apple-system,sans-serif;color:var(--text);background:var(--bg)}
h1,h2,h3,.card-title,.season-name{font-family:'Outfit',sans-serif;letter-spacing:-0.02em}
body::before{content:'';position:fixed;top:0;left:0;width:100%;height:100%;background:url('../img/logo-bg.png') repeat;z-index:-1;opacity:var(--bg-pattern-opacity,0.1);filter:var(--bg-pattern-filter,none);transition:opacity 0.4s,filter 0.4s}
a{color:var(--primary);text-decoration:underline;cursor:pointer}
a:visited{color:var(--primary)}
a:hover{text-decoration:none;opacity:.8}
h2{margin-bottom:1.5rem}
```

**Hinweis `body::before`:** URL relativ von `css/` aus: `url('../img/logo-bg.png')`.

**Hinweis `a`-Styles:** Bisher nur auf index.html und dashboard.html global gesetzt. Wird jetzt universell. Seiten die `text-decoration:none` brauchen (datenschutz, impressum, team) müssen inline überschreiben.

### Sektion 2 — Header

```css
/* === Header === */
header{background:linear-gradient(135deg,var(--card) 0%,var(--card-alt) 100%);border-bottom:2px solid var(--primary);box-shadow:0 2px 20px color-mix(in srgb,var(--primary) 8%,transparent);padding:1rem 2rem;z-index:50;backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px)}
@media(min-width:769px){header{position:sticky;top:0}}
header h1{margin:0;font-size:1.5rem}
header p{margin:.25rem 0 0;color:var(--muted)}
```

**Achtung `team.html`:** Nutzt einen flat Header ohne Gradient/Shadow/Primary-Border:
```css
header{background:var(--card);border-bottom:1px solid var(--border);box-shadow:none}
```
Muss inline überschrieben werden (3 Properties).

### Sektion 3 — Burger Menu & Dark Mode Toggle

```css
/* === Burger Menu === */
.burger-btn{background:none;border:none;cursor:pointer;padding:.5rem;display:flex;flex-direction:column;gap:4px;z-index:100}
.burger-btn span{display:block;width:24px;height:3px;background:var(--text);border-radius:2px;transition:all .3s}
.burger-btn.open span:nth-child(1){transform:rotate(45deg) translate(5px,5px)}
.burger-btn.open span:nth-child(2){opacity:0}
.burger-btn.open span:nth-child(3){transform:rotate(-45deg) translate(7px,-6px)}

/* === Dark Mode Toggle === */
.dark-mode-toggle{appearance:none;cursor:pointer;width:50px;height:28px;background:var(--border);border:none;border-radius:14px;position:relative;transition:background .3s}
.dark-mode-toggle::before{content:"☀️";position:absolute;left:4px;top:50%;transform:translateY(-50%);font-size:14px;transition:left .3s}
.dark-mode-toggle::after{content:"🌙";position:absolute;right:4px;top:50%;transform:translateY(-50%);font-size:14px;opacity:0;transition:opacity .3s}
.dark-mode-toggle:checked{background:var(--primary)}
.dark-mode-toggle:checked::before{opacity:0}
.dark-mode-toggle:checked::after{opacity:1}

/* === Menu Overlay & Nav Panel === */
.menu-overlay{position:fixed;top:0;right:0;width:100%;height:100vh;background:rgba(0,0,0,.5);z-index:90;opacity:0;pointer-events:none;transition:opacity .3s}
.menu-overlay.open{opacity:1;pointer-events:auto}
nav{position:fixed;top:0;right:-100%;width:280px;height:100vh;background:var(--card);z-index:100;transition:right .3s;padding:5rem 2rem 2rem;box-shadow:-4px 0 24px rgba(0,0,0,.1)}
nav.open{right:0}
nav ul{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:.5rem}
nav a{text-decoration:none;color:var(--text);padding:.75rem 1rem;border-radius:8px;font-weight:500;display:block;transition:background .2s}
nav a:hover{background:color-mix(in srgb,var(--primary) 10%,var(--card))}
nav a.active{background:color-mix(in srgb,var(--primary) 15%,var(--card));color:var(--primary);font-weight:700}
```

### Sektion 4 — Layout

```css
/* === Layout === */
main{max-width:1200px;margin:0 auto;padding:2.5rem 2rem}
```

### Sektion 5 — Cards

```css
/* === Cards === */
.card{background:linear-gradient(145deg,var(--card) 0%,var(--card-alt) 100%);border:1px solid var(--border);border-radius:12px;border-top:2px solid var(--primary);border-top-left-radius:10px;border-top-right-radius:10px;padding:1.25rem 1.5rem;margin-bottom:1.5rem;box-shadow:0 4px 16px rgba(0,0,0,.06),inset 0 1px 0 color-mix(in srgb,var(--primary) 15%,transparent)}
.card-header{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:.75rem}
.card-title{font-weight:700;font-size:1.1rem}
.card-sub{color:var(--muted);font-size:.9rem}
.card h2{padding-bottom:.5rem;border-bottom:2px solid color-mix(in srgb,var(--primary) 40%,transparent);margin-bottom:1rem}
```

**Achtung `team.html`:** Nutzt flat Cards ohne Gradient/Primary-Border/Inset-Shadow:
```css
.card{background:var(--card);border-top:1px solid var(--border);border-top-left-radius:12px;border-top-right-radius:12px;box-shadow:0 4px 16px rgba(0,0,0,.04)}
```
Muss inline überschrieben werden.

### Sektion 6 — Tables

```css
/* === Tables === */
table{width:100%;border-collapse:collapse;margin-top:.75rem;font-size:.85rem}
th{color:var(--muted);font-weight:600;font-size:.75rem;text-transform:uppercase;letter-spacing:0.04em;padding:.5rem .6rem;border-bottom:2px solid var(--border)}
td{padding:.5rem .6rem;border-bottom:1px solid var(--border);text-align:center}
tr:hover td{background:color-mix(in srgb,var(--primary) 8%,transparent)}
tr.leader{font-weight:700;color:var(--primary)}
tr.leader td{background:color-mix(in srgb,var(--primary) 6%,transparent)}
```

**Hinweis `td{text-align:center}`:** Mehrheit der Seiten nutzt center. Seiten mit abweichendem Alignment überschreiben inline (turnier, ewige-tabelle, archiv).

### Sektion 7 — Match Score Badge & Utilities

```css
/* === Match Score === */
.match-score{font-family:'Outfit',sans-serif;font-weight:700;font-size:.95rem;letter-spacing:0.05em;padding:.2rem .6rem;border-radius:6px;background:var(--primary);color:var(--bg);box-shadow:0 2px 8px color-mix(in srgb,var(--primary) 30%,transparent)}

/* === Utilities === */
.loading{text-align:center;padding:2rem;color:var(--muted)}
.empty-state{text-align:center;padding:3rem;color:var(--muted)}
```

**Achtung `team.html`:** Nutzt invertiertes `.match-score` (`background:var(--card-alt);color:var(--primary)`). Muss inline überschrieben werden.

### Sektion 8 — Footer

```css
/* === Footer === */
footer{background:var(--card);border-top:1px solid var(--border);padding:1.5rem 2rem;margin-top:3rem;display:grid;grid-template-columns:1fr 1fr 1fr;gap:2rem;align-items:center;font-size:.85rem;color:var(--muted)}
.footer-left{text-align:left}
.footer-center{text-align:center}
.footer-right{text-align:right}
footer a{color:var(--primary);text-decoration:none}
footer a:hover{text-decoration:underline}
footer a:visited{color:var(--primary)}
.backend-status{display:inline-flex;align-items:center;gap:.5rem;font-weight:500}
.status-dot{width:8px;height:8px;border-radius:50%;display:inline-block}
.status-dot.online{background:#3fb950}
.status-dot.offline{background:#dc2626}
#theme-select{padding:.35rem .6rem;border-radius:6px;border:1px solid var(--border);background:var(--card);color:var(--text);font-family:'DM Sans',sans-serif;font-size:.8rem;cursor:pointer}
#theme-select:focus{outline:none;border-color:var(--primary)}
@media(max-width:768px){footer{grid-template-columns:1fr;gap:1rem;text-align:center}.footer-left,.footer-right{text-align:center}}
```

## Einbindung pro Seite

Jede Public-Seite bekommt diesen `<head>`-Block:

```html
<head>
  <meta charset="utf-8" />
  <link rel="icon" type="image/png" href="img/logo_comic.png">
  <title>Seitentitel – BIW Pokal</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <!-- Theme-System zuerst (synchron, setzt CSS-Variablen sofort, kein Flash) -->
  <script src="js/themes.js"></script>
  <script type="module" src="js/background.js"></script>
  <!-- Shared CSS (nutzt die CSS-Variablen) -->
  <link rel="stylesheet" href="css/shared.css">
  <!-- Google Fonts mit Preconnect -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet"/>
  <!-- Seitenspezifisches CSS (nur was nicht in shared.css ist) -->
  <style>
    /* ... page-specific styles only ... */
  </style>
</head>
```

**Hinweis:** `themes.js` lädt synchron (kein `defer`/`async`), daher stehen die CSS-Variablen bereit bevor `shared.css` geparsed wird. Kein FOUC.

## Was pro Seite inline bleibt

| Seite | Inline-CSS Inhalt |
|-------|-------------------|
| `index.html` | `h2{margin-bottom:1rem}`, Hero Bar, Tabs, Accordions, Match Rows, Content Grid, Compact Standings, Mini Bracket |
| `turnier.html` | Season Grid, Match Items (4-col grid), Match Header, Matchday Groups, `td:first-child{text-align:center;width:40px}`, `td:nth-child(2){text-align:left}` |
| `ko.html` | `main{max-width:1400px}`, KO Bracket (flex), Round Headers, Match Cards, Connectors, Bracket Tabs, Third-Place, Bye Badges |
| `dashboard.html` | `main{max-width:800px}`, `h2{margin-bottom:1rem}`, Login Screen, Profile Header, Discord Button, Badges, Forms, Toggle Switch, Crest Upload, Team Search, Toasts |
| `archiv.html` | Season Cards (collapsible), Season Badges, Compact Tables, KO Bracket Compact, Champion Badge, `td{text-align}` Overrides |
| `ewige-tabelle.html` | `th{position:sticky;top:0;background:var(--card);z-index:10}`, `@media(min-width:769px){th{top:72px}}`, `td:first-child,th:first-child{text-align:left;padding-left:1rem}`, Top-3 Highlights (`tr.top1`, `tr.top3`), Rank Column |
| `team.html` | `main{max-width:900px}`, Header-Override (flat), `.card`-Override (flat), `.match-score`-Override (invertiert), `a{text-decoration:none}`, Back-Link, Team Header, Stats Grid, Match List, Badges |
| `regeln.html` | `main{max-width:900px}`, `h2{margin:2rem 0 1rem;font-size:1.5rem}`, `h3{margin:1.5rem 0 .75rem;color:var(--primary)}`, `.card{line-height:1.7}`, `.card h3`, `.card ul`, `.card li`, `.card strong`, `.intro` |
| `datenschutz.html` | `main{max-width:900px}`, `h2{margin:2rem 0 1rem;font-size:1.5rem}`, `h3` Override, `.card{line-height:1.7}`, `.card p`, `.card ul`, `.card li`, `a{text-decoration:none}` |
| `impressum.html` | Wie datenschutz + **`:root`-Block entfernen** (hardcoded dark-theme Variablen, wird durch themes.js ersetzt) |

## Inkonsistenzen — Harmonisierung

| Eigenschaft | Shared Default | Seitenspezifische Overrides (inline) |
|-------------|---------------|--------------------------------------|
| `main` max-width | `1200px` | ko: `1400px`, dashboard: `800px`, team/regeln/datenschutz/impressum: `900px` |
| `td` text-align | `center` | turnier: `td:first-child{center;width:40px}` + `td:nth-child(2){left}`, ewige-tabelle: `td:first-child,th:first-child{left}`, archiv: nach Bedarf |
| `h2` margin-bottom | `1.5rem` | index/dashboard: `1rem`, regeln/datenschutz/impressum: `margin:2rem 0 1rem;font-size:1.5rem` |
| `a` global styles | `text-decoration:underline` | datenschutz/impressum/team: `a{text-decoration:none}` |
| `header` style | Gradient + primary border + shadow | team: flat `background:var(--card)`, `1px border`, kein shadow |
| `.card` style | Gradient + primary top-border + inset shadow | team: flat `background:var(--card)`, keine Akzente |
| `.match-score` | `background:var(--primary);color:var(--bg)` | team: `background:var(--card-alt);color:var(--primary)` |
| `header h1` / `header p` | Shared (8 von 10 Seiten identisch) | index: hat keine `header h1/p` Rules (nutzt inline-styles im HTML) |
| `footer a:visited` | `color:var(--primary)` | Neu als globaler Default (bisher nur auf 3 Seiten) |

## Sonderfall: `impressum.html` `:root`-Block

`impressum.html` enthält einen hardcoded `:root`-Block mit Dark-Theme-Variablen. Dieser wird bei der Migration **entfernt**, da `themes.js` diese Variablen bereits setzt. Die `:root`-Werte sind identisch mit dem Flutlicht-Dark-Theme.

## Pfad-Anpassung

Die `body::before` background-URL ändert sich:
- **Vorher** (inline): `url('img/logo-bg.png')`
- **Nachher** (aus `css/`): `url('../img/logo-bg.png')`

## Nicht in Scope

- **admin.html** — eigenes CSS-System, dark-only Theme, separater Admin-Stack
- **JS-Konsolidierung** — separater Refinement-Bereich (B in frontend-todo.md)
- **HTML-Templates** — separater Refinement-Bereich (C in frontend-todo.md)
