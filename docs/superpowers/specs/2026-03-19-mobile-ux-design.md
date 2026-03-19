# Bereich F: Mobile & UX — Design Spec

> **Ziel:** Mobile-Erfahrung verbessern — scrollbare Navigation, Tabellen-Overflow, KO-Bracket-Scroll-Hint, Touch-Targets.

---

## 1. Nav Overflow

**Problem:** `nav` hat `height: 100vh` aber kein `overflow-y`. Bei kleinen Screens (iPhone SE, alte Android) können die 9 Nav-Links abgeschnitten werden.

**Lösung:** `overflow-y: auto` auf `nav` in `shared.css` ergänzen.

```css
nav {
  /* bestehende Regeln bleiben */
  overflow-y: auto;
}
```

**Dateien:** `css/shared.css` (1 Zeile)

---

## 2. Tabellen-Scrollbarkeit

**Problem:** Dynamisch erzeugte Tabellen haben keinen `overflow-x: auto`-Wrapper. Auf schmalen Screens werden sie abgeschnitten oder erzwingen horizontales Scrollen der gesamten Seite.

**Lösung:** Tabellen in ein `<div style="overflow-x:auto">` wrappen — je nach Erzeugungsmethode:

### turnier.html (createElement)
Die Standings-Tabelle wird per `createElement('table')` erzeugt und via `card.appendChild(tbl)` eingefügt. Vor dem Append wird ein Wrapper-Div dazwischengeschaltet:

```js
const wrapper = document.createElement('div');
wrapper.style.overflowX = 'auto';
wrapper.appendChild(tbl);
card.appendChild(wrapper);
```

**Stelle:** `turnier.html:194` — `card.appendChild(tbl)` ersetzen.

### ewige-tabelle.html (innerHTML)
Die Tabelle wird als HTML-String gebaut und via `container.innerHTML = html` eingefügt. Den `<table>`-String in einen Wrapper einbetten:

```js
container.innerHTML = '<div style="overflow-x:auto">' + html + '</div>';
```

**Alternativ:** Den bestehenden `html`-String mit `<div style="overflow-x:auto">` prefixen und `</div>` suffixen.

**Stelle:** `ewige-tabelle.html:151` — `container.innerHTML = html` anpassen.

### archiv.html (innerHTML)
Standings-Tabellen werden als Teil eines größeren HTML-Strings gebaut. Die `<table class="compact-table">...</table>`-Blöcke jeweils in `<div style="overflow-x:auto">` wrappen.

**Stelle:** `archiv.html:211` — Tabellen-String wrappen.

**Dateien:** `turnier.html`, `ewige-tabelle.html`, `archiv.html`

---

## 3. KO-Bracket Scroll-Hint

**Problem:** `.ko-bracket` und `.ko-bracket-compact` haben `overflow-x: auto`, aber keinen visuellen Hinweis, dass horizontal gescrollt werden kann.

**Lösung:** Wrapper-Div mit `position: relative` + `::after` Pseudo-Element. Der Gradient liegt auf dem Wrapper (nicht auf dem scrollbaren Container selbst), damit er beim Scrollen fixiert bleibt.

**Wichtig:** `::after` auf einem `overflow: auto`-Element scrollt mit dem Content — daher muss der Gradient auf einem **nicht-scrollenden Parent** liegen.

Jede `.ko-bracket` / `.ko-bracket-compact` wird in ein `<div class="ko-scroll-wrapper">` gewrappt:

```css
.ko-scroll-wrapper {
  position: relative;
}

.ko-scroll-wrapper::after {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  width: 40px;
  height: 100%;
  background: linear-gradient(to right, transparent, var(--bg));
  pointer-events: none;
}
```

Der Gradient nutzt `var(--bg)` (Hintergrundfarbe), damit er in beiden Themes (Light/Dark) korrekt ausblendet.

**Umsetzung:**
- `ko.html`: Das `<div>` mit Klasse `ko-bracket` (per JS erzeugt) in ein Wrapper-Div einbetten. CSS-Klasse `.ko-scroll-wrapper` inline in `ko.html` definieren.
- `archiv.html`: Analog für `.ko-bracket-compact`. CSS-Klasse `.ko-scroll-wrapper` inline in `archiv.html` definieren. Alternativ: da beide Seiten die gleiche Klasse brauchen, kann `.ko-scroll-wrapper` in `shared.css` landen.

**Dateien:** `ko.html` (HTML/JS + Inline-CSS), `archiv.html` (HTML/JS + Inline-CSS), ggf. `css/shared.css`

---

## 4. Touch-Targets

**Problem:** Burger-Button hat `padding: .5rem` mit 24px-Spans — ergibt ~40px Gesamt-Touch-Target, unter dem 44px-Minimum.

**Lösung:** `min-height: 44px; min-width: 44px` + Zentrierung in `shared.css`:

```css
.burger-btn {
  /* bestehende Regeln bleiben */
  min-height: 44px;
  min-width: 44px;
  align-items: center;
  justify-content: center;
}
```

**Befund restliche Elemente:**
- Nav-Links: `padding: .75rem 1rem` → ~44px Höhe — OK
- Dark-Mode-Toggle: `50px × 28px` — Breite OK, Höhe unter 44px, aber als Checkbox ohne Label akzeptabel (kein primäres Interaktionselement)
- Season-Items: `padding: .5rem 1rem` — OK (Text macht sie groß genug)

**Dateien:** `css/shared.css` (3 Zeilen)

---

## Zusammenfassung

| # | Änderung | Dateien | Aufwand |
|---|----------|---------|---------|
| 1 | Nav overflow-y | shared.css | trivial |
| 2 | Tabellen overflow-x wrapper | turnier.html, ewige-tabelle.html, archiv.html | klein |
| 3 | KO-Bracket scroll-hint | ko.html, archiv.html | klein |
| 4 | Burger touch-target | shared.css | trivial |
