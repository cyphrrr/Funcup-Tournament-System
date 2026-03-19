# Frontend Bestandsaufnahme & Refinement-Plan

> Arbeitsdokument zur schrittweisen Verbesserung des Frontends.
> Stand: 2026-03-19

---

## 1. Ist-Zustand: Architektur

**11 HTML-Seiten** (alle Vanilla HTML/JS/CSS, kein Build-Prozess):

| Seite | Zweck | Zeilen |
|-------|-------|--------|
| `index.html` | Homepage: Hero-Bar, Tabs (Ergebnisse/News), Sidebar | 835 |
| `admin.html` | Admin-Interface (eigener Stack) | 862 |
| `turnier.html` | Gruppenphase: Saison-Auswahl, Tabellen, Spielplan | 461 |
| `ko.html` | KO-Bracket-Visualisierung | 485 |
| `dashboard.html` | User-Profil (Discord OAuth, Wappen, Team-Claim) | 695 |
| `archiv.html` | Saison-Archiv mit aufklappbaren Details | 512 |
| `ewige-tabelle.html` | All-Time-Standings | 288 |
| `team.html` | Team-Profilseite | 320 |
| `regeln.html` | Regelwerk (statisch) | 258 |
| `datenschutz.html` | Datenschutz (statisch) | 252 |
| `impressum.html` | Impressum (statisch) | 213 |

**Shared JS** (`js/`): config, api, auth, utils, themes, version, tracking, background, init
**Admin JS** (`js/admin/`): 10 Module (setup, ko-phase, ergebnisse, news, etc.)

---

## 2. Identifizierte Probleme

### 2.1 CSS-Duplication (Kritisch)

Jede HTML-Datei hat einen eigenen `<style>`-Block. Folgende Blöcke sind **nahezu identisch** in allen Public-Seiten kopiert:

| CSS-Block | Zeilen pro Datei | Vorkommen | Gesamt-Duplication |
|-----------|------------------|-----------|--------------------|
| Reset + Body + Fonts | ~5 | 9x | ~45 Zeilen |
| Header (sticky, gradient, blur) | ~4 | 9x | ~36 Zeilen |
| Burger Menu + Animation | ~7 | 9x | ~63 Zeilen |
| Dark Mode Toggle | ~7 | 9x | ~63 Zeilen |
| Menu Overlay + Nav Panel | ~10 | 9x | ~90 Zeilen |
| Card-Styles | ~5 | 8x | ~40 Zeilen |
| Table-Styles | ~6 | 7x | ~42 Zeilen |
| Footer (Grid, Status, Theme) | ~12 | 9x | ~108 Zeilen |
| **Gesamt-Duplication** | | | **~490 Zeilen** |

**Konsequenz:** Eine Farbe oder ein Abstand muss in bis zu 9 Dateien gleichzeitig geändert werden.

### 2.2 JS-Duplication (Kritisch)

Identischer Boilerplate-Code wird in jede Seite kopiert:

| JS-Block | Zeilen | Vorkommen |
|----------|--------|-----------|
| Burger Menu Toggle (`toggleMenu()`) | ~15 | 8x (alle Public-Seiten) |
| Admin-Link Sichtbarkeit | ~3 | 8x |
| Backend-Status Check (`updateBackendStatus()`) | ~15 | 7x (eigener `<script type="module">`) |
| `loadCrests()` + `crestImg()` | ~12 | 5x (index, turnier, ko, archiv, ewige-tabelle) |
| `teamName()` + `teamCache` | ~5 | 4x |

**Gesamt:** ~250+ Zeilen duplizierter JS-Code

### 2.3 HTML-Duplication (Mittel)

Header, Navigation und Footer sind in jeder Datei manuell kopiert:

- **Header** (~20 Zeilen): Logo, Titel, Dark-Mode-Toggle, Burger-Button
- **Navigation** (~15 Zeilen): Identische `<nav>` mit `<ul>`, nur `class="active"` variiert
- **Footer** (~16 Zeilen): Backend-Status, Copyright, Version, Theme-Selector

**Gesamt:** ~50 Zeilen HTML x 9 Seiten = ~450 Zeilen Duplication

### 2.4 Visuelle Inkonsistenzen

- `index.html` hat keinen Subtitel im Header (`/ Turnier`, `/ KO-Phase` etc.) — Absicht oder Fehler?
- `turnier.html` und `ko.html` verwenden `.season-item` mit leicht unterschiedlichem Styling
- Tabellen haben auf manchen Seiten `td:first-child{text-align:center}`, auf anderen nicht
- `dashboard.html` definiert eigene `.btn`-Klassen, die auf anderen Seiten nicht existieren
- Archiv nutzt altes KO-API-Format (`/ko-bracket`), Index nutzt neues (`/ko-brackets`)

### 2.5 Performance

- **Backend-Status-Polling:** Jede Seite startet eigenen `setInterval(updateBackendStatus, 30000)` mit Fetch auf `/api/seasons` — doppelter Traffic beim Seitenload
- **Kein Caching:** Crest-Daten, Team-Daten werden bei jedem Seitenload neu geholt
- **Archiv-Seite:** Lädt sequentiell alle Saisons + Gruppen im Waterfall (`await` in Schleife)
- **Google Fonts:** Doppelt geladen (einmal im HTML, eventuell im Cache, aber keine `preconnect`-Hints)

### 2.6 Mobile Experience

- Navigation ist Burger-Menu (funktional), aber:
  - Kein `overflow-y: auto` auf `nav` — bei vielen Menüpunkten scrollt es nicht
  - KO-Bracket (`ko.html`) hat `overflow-x: auto` aber keine Touch-Scroll-Hinweise
  - Tabellen werden auf kleinen Screens eng — kein horizontales Scrolling
  - Hero-Bar auf Index hat 2x2 Grid auf Mobile — funktional, aber Divider verschwinden

---

## 3. Refinement-Bereiche

### Bereich A: CSS konsolidieren

**Ziel:** Gemeinsame Styles in eine `shared.css` auslagern, seitenspezifisches CSS bleibt inline.

**Scope:**
- [x] `shared.css` erstellen mit: Reset, Body, Fonts, Header, Burger, Dark-Mode-Toggle, Nav, Cards, Tables, Footer, Hover-Effekte
- [x] Alle 10 Public-Seiten auf `<link rel="stylesheet" href="css/shared.css">` umstellen
- [x] Nur seitenspezifische Styles in `<style>` belassen
- [x] Admin.html separat behandeln (eigenes CSS-System)

**Geschätzter Effekt:** ~490 Zeilen CSS-Duplication eliminiert, eine Stelle zum Ändern.

### Bereich B: JS-Boilerplate konsolidieren

**Ziel:** Shared-Funktionen in ein Modul auslagern, das jede Seite importiert.

**Scope:**
- [x] `js/shared-ui.js` erstellen (ES Module) mit: `initBurgerMenu()`, `initAdminLink()`, `initBackendStatus()` → Theme bleibt separat in themes.js
- [x] `js/team-utils.js` erstellen mit: `loadCrests()`, `crestImg()`, `teamName()`, `registerTeams()`, `registerTeam()`
- [x] Alle Seiten: Boilerplate durch ES Module Imports ersetzen → 10 Seiten migriert
- [x] Backend-Status-Script (separater `<script type="module">` Block am Ende jeder Seite) eliminieren → in shared-ui.js konsolidiert

**Geschätzter Effekt:** ~250+ Zeilen JS-Duplication eliminiert.

### Bereich C: HTML-Templates (Optional, Low Priority)

**Ziel:** Header/Nav/Footer dynamisch laden oder als Web Component.

**Optionen:**
1. **JS-Include:** `shared-ui.js` injiziert Header/Nav/Footer ins DOM (einfach, aber Flash)
2. **HTML Imports via fetch:** `fetch('partials/header.html')` (FOUC-Problem)
3. **Status quo beibehalten:** Bei 9 Seiten ist manuelles Kopieren tragbar

**Empfehlung:** Noch abwarten — CSS/JS-Konsolidierung hat den größeren Hebel.

### Bereich D: Visuelle Konsistenz

**Scope:**
- [x] Header-Subtitel-Konvention klären (mit/ohne auf Index?) → "/ Start" hinzugefügt
- [x] `.season-item`-Styling vereinheitlichen (turnier vs. ko) → turnier-Variante in shared.css
- [ ] Tabellen-Alignment konsistent machen → kein Handlungsbedarf (verschiedene Spaltentypen)
- [x] Button-Klassen (`.btn`, `.btn-primary`) in `shared.css` global verfügbar machen
- [x] Archiv: KO-API auf neues Format (`/ko-brackets`) migrieren (mit v1-Fallback)

### Bereich E: Performance

**Scope:**
- [x] `<link rel="preconnect" href="https://fonts.googleapis.com">` hinzufügen (erledigt mit CSS-Konsolidierung)
- [x] Backend-Status: Nur einmal prüfen statt doppelt → `setBackendStatus(online)` + `/api/version`-Polling
- [x] Archiv: Parallelisierung der Saison-Loads → `Promise.all` für groups + standings, doppelten Fetch eliminiert
- [x] Crest/Team-Cache in `sessionStorage` → 10min TTL, cross-page Caching

### Bereich F: Mobile & UX

**Scope:**
- [x] Nav: `overflow-y: auto; max-height: 100vh` hinzufügen → overflow-y auf nav in shared.css
- [x] Tabellen: `overflow-x: auto` Wrapper für mobile Scrollbarkeit → JS-Wrapper in turnier, ewige-tabelle, archiv
- [x] KO-Bracket: Scroll-Indicator oder Touch-Hint → CSS-Gradient scroll-hint mit Wrapper-Div
- [x] Allgemein: Touch-Targets prüfen (min. 44px) → Burger-Button auf 44x44 min-size

---

## 4. Priorisierung

| Prio | Bereich | Begründung |
|------|---------|------------|
| 1 | **A: CSS konsolidieren** | Größter Pain Point, blockiert alle Style-Änderungen |
| 2 | **B: JS konsolidieren** | Zweitgrößte Duplication, Bug-Risiko bei Änderungen |
| 3 | **D: Visuelle Konsistenz** | Profitiert direkt von A, schnelle Wins |
| 4 | **F: Mobile & UX** | User-facing, relativ wenig Aufwand |
| 5 | **E: Performance** | Nice-to-have, kein akuter Pain |
| 6 | **C: HTML-Templates** | Geringer ROI bei 9 Seiten |

---

## 5. Umsetzungslog

> Hier werden abgeschlossene Schritte dokumentiert.

- **2026-03-19: Bereich A (CSS konsolidieren) abgeschlossen** — `css/shared.css` erstellt, 10 Seiten migriert, ~490 Zeilen Duplication eliminiert. Preconnect-Hints (Bereich E) gleich mit erledigt.
- **2026-03-19: Bereich D (Visuelle Konsistenz) abgeschlossen** — Header-Subtitel `/ Start` auf index.html, `.season-item` und `.btn` in shared.css vereinheitlicht, archiv.html KO-API auf `/ko-brackets` migriert (mit v1-Fallback).
- **2026-03-19: Bereich F (Mobile & UX) abgeschlossen** — Nav overflow-y, Tabellen overflow-x Wrapper, KO-Bracket scroll-hint Gradient, Burger touch-target 44px.
- **2026-03-19: Bereich B (JS-Boilerplate konsolidieren) abgeschlossen** — `shared-ui.js` (Burger, Admin-Link, Backend-Status) und `team-utils.js` (Crests, Team-Cache) erstellt. 10 Seiten auf ES Module Imports migriert, ~250 Zeilen Duplication eliminiert.
- **2026-03-19: Bereich E (Performance) abgeschlossen** — Backend-Status: `setBackendStatus(online)` eliminiert doppelten Fetch, Interval nutzt `/api/version`. Archiv: `Promise.all` für parallele Season/Standings-Loads, doppelten groups-with-teams-Fetch eliminiert. Crests: `sessionStorage`-Cache mit 10min TTL.
