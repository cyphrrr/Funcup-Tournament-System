# Bereich B: JS-Boilerplate konsolidieren — Design Spec

> **Ziel:** Duplizierte JS-Funktionen (Burger-Menü, Admin-Link, Backend-Status, Crest/Team-Utilities) in zwei ES Modules zusammenlegen. Jede Seite importiert nur was sie braucht, statt denselben Code inline zu wiederholen.

---

## Entscheidungen

- **Zwei Module:** `js/shared-ui.js` (alle 10 Seiten) + `js/team-utils.js` (5 datengetriebene Seiten)
- **ES Modules:** Alle Seiten auf `<script type="module">` umstellen
- **Crest-Größe:** Einheitlich 24px (kein size-Parameter)
- **Backend-Status:** Nur zusammenlegen, keine Performance-Optimierung (bleibt Bereich E)
- **admin.html:** Nicht betroffen

---

## 1. `js/shared-ui.js` — UI-Boilerplate

Neues ES Module. Wird von allen 10 Public-Seiten importiert.

### Exports

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

### Nutzung (jede Seite)

```html
<script type="module">
  import { initBurgerMenu, initAdminLink, initBackendStatus } from './js/shared-ui.js';
  initBurgerMenu();
  initAdminLink();
  initBackendStatus();
</script>
```

---

## 2. `js/team-utils.js` — Team/Crest-Funktionen

Neues ES Module. Wird nur von 5 Seiten importiert: index.html, turnier.html, ko.html, archiv.html, ewige-tabelle.html.

### Exports

```js
import { API_URL } from './config.js';

let crestCache = {};
export let teamCache = {};

export async function loadCrests() {
  try {
    crestCache = await fetch(`${API_URL}/api/teams/crests`).then(r => r.json());
  } catch (e) {
    console.warn('Crests konnten nicht geladen werden:', e);
  }
}

export function crestImg(teamId) {
  if (!teamId) return '';
  const url = crestCache[String(teamId)];
  if (!url) return '';
  const src = url.startsWith('http') ? url : `${API_URL}${url}`;
  return `<img src="${src}" alt="" loading="lazy" style="width:24px;height:24px;object-fit:contain;vertical-align:middle;margin-right:4px;border-radius:3px;flex-shrink:0" onerror="this.style.display='none'">`;
}

export function teamName(id) {
  return teamCache[id] || `Team ${id}`;
}

export function registerTeams(groups) {
  groups.forEach(g => g.teams.forEach(t => { teamCache[t.id] = t.name; }));
}
```

### Nutzung (datengetriebene Seiten)

```html
<script type="module">
  import { initBurgerMenu, initAdminLink, initBackendStatus } from './js/shared-ui.js';
  import { loadCrests, crestImg, teamName, registerTeams } from './js/team-utils.js';

  initBurgerMenu();
  initAdminLink();
  initBackendStatus();
  await loadCrests();

  // Seitenspezifischer Code nutzt crestImg(), teamName(), registerTeams()
</script>
```

---

## 3. Migration der Seiten

### Gruppe A: Statische Seiten (einfach)

**regeln.html, datenschutz.html, impressum.html, dashboard.html, team.html**

Änderungen pro Seite:
1. Burger-Menu-Boilerplate entfernen (toggleMenu, Event-Listener)
2. Admin-Link-Check entfernen
3. updateBackendStatus()-Funktion + separaten `<script type="module">`-Block entfernen
4. Durch Import + Init ersetzen (3 Zeilen)
5. `<script>` auf `<script type="module">` umstellen wo nötig (regeln, datenschutz, impressum)

### Gruppe B: Datengetriebene Seiten (mehr Arbeit)

**index.html, turnier.html, ko.html, archiv.html, ewige-tabelle.html**

Änderungen pro Seite:
1. Alles aus Gruppe A (Burger, Admin, Status entfernen)
2. `let crestCache = {}` / `loadCrests()` / `crestImg()` Definitionen entfernen
3. `let teamCache = {}` / `teamName()` Definitionen entfernen
4. Inline `groups.forEach(g => g.teams.forEach(...))` durch `registerTeams(groups)` ersetzen
5. Imports für `shared-ui.js` + `team-utils.js` hinzufügen
6. Bestehende `crestImg()`-Aufrufe bleiben (Signatur ist kompatibel, Output wird einheitlich 24px)
7. Separaten `<script type="module">`-Block für Backend-Status entfernen

### Was sich NICHT ändert

- Seitenspezifische Logik (Bracket-Rendering, Tabellen, Tabs, Formulare etc.)
- `js/themes.js`, `js/version.js`, `js/tracking.js`, `js/background.js`
- `admin.html` — eigenes JS-System, nicht betroffen

---

## 4. Erwartetes Ergebnis

- **~250 Zeilen** duplizierter JS-Code eliminiert
- **2 neue Dateien:** `js/shared-ui.js` (~40 Zeilen), `js/team-utils.js` (~30 Zeilen)
- **10 HTML-Dateien** modifiziert (Boilerplate raus, Imports rein)
- **Einheitliche Crest-Darstellung** (24px auf allen Seiten)
- **Konsistentes Module-Format** auf allen Public-Seiten
