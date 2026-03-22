# Bereich D: Visuelle Konsistenz — Design Spec

> **Ziel:** Visuelle Inkonsistenzen zwischen den Public-Seiten beseitigen.

---

## 1. Header-Subtitel auf index.html

**Problem:** `index.html` ist die einzige Public-Seite ohne Subtitel im Header. Alle anderen 9 Seiten haben `/ Turnier`, `/ KO-Phase` etc.

**Lösung:** `/ Start` als Subtitel auf index.html hinzufügen — identisches Markup wie alle anderen Seiten:

```html
<span style="opacity:0.4;font-weight:400;font-size:1rem;margin-left:0.3rem">/ Start</span>
```

**Dateien:** `index.html` (1 Zeile)

---

## 2. `.season-item` Styling vereinheitlichen

**Problem:** `turnier.html` und `ko.html` definieren `.season-item` mit unterschiedlichem Styling:
- turnier.html: Border, Background, Lift-Hover mit Box-Shadow (prominente "Chips")
- ko.html: Kein Border/Background, nur Hover-Highlight (dezente Inline-Links)

**Lösung:** turnier.html-Variante wird Standard. Regeln kommen in `shared.css`, beide Seiten entfernen ihre Inline-Definitionen.

```css
/* In shared.css */
.season-item{padding:.5rem 1rem;cursor:pointer;border-radius:8px;transition:all .2s;background:var(--card);border:1px solid var(--border);font-size:.9rem;white-space:nowrap}
.season-item:hover{background:color-mix(in srgb,var(--primary) 10%,var(--card));border-color:var(--primary);transform:translateY(-2px);box-shadow:0 4px 12px rgba(0,0,0,.1)}
.season-item.active{background:color-mix(in srgb,var(--primary) 15%,var(--card));color:var(--primary);font-weight:600;border-color:var(--primary)}
```

**Dateien:** `css/shared.css`, `turnier.html`, `ko.html`

---

## 3. `.btn`-Klassen global in shared.css

**Problem:** `dashboard.html` und `admin.html` definieren jeweils eigene `.btn`-Varianten. `shared.css` hat keine Button-Klassen. Zukünftige Seiten müssten Buttons erneut inline definieren.

**Lösung:** Basis-Set in `shared.css` aufnehmen, orientiert an dashboard.html-Variante (moderner):

```css
/* In shared.css */
.btn{display:inline-flex;align-items:center;gap:.5rem;padding:.6rem 1.25rem;border:none;border-radius:8px;font-size:.9rem;font-weight:600;cursor:pointer;transition:background .2s,opacity .2s}
.btn:disabled{opacity:.5;cursor:not-allowed}
.btn-primary{background:var(--primary);color:#fff}
.btn-primary:hover:not(:disabled){opacity:.85}
.btn-danger{background:var(--danger,#dc2626);color:#fff}
.btn-danger:hover:not(:disabled){opacity:.85}
.btn-outline{background:transparent;border:1px solid var(--border);color:var(--text)}
.btn-outline:hover:not(:disabled){background:var(--card-alt)}
```

`dashboard.html` entfernt seinen `.btn`-Inline-Block. `admin.html` bleibt unverändert (eigenes CSS-System).

**Dateien:** `css/shared.css`, `dashboard.html`

---

## 4. Tabellen-Alignment

**Befund:** Kein echter Widerspruch.
- `turnier.html`: `td:first-child{text-align:center}` — zentriert Rang-Spalte (Nummer)
- `ewige-tabelle.html`: `td:first-child{text-align:left}` — linksbündet Team-Name-Spalte

Verschiedene Spalten-Typen an Position 1 → korrektes Verhalten. **Keine Änderung nötig.**

---

## 5. Archiv KO-API Migration

**Problem:** `archiv.html` nutzt `/ko-bracket` (alt, Singular, flat), `index.html` nutzt `/ko-brackets` (neu, Plural, 3-Bracket-System). Die alte API liefert ein einzelnes Bracket mit `matches[]` (Team-IDs), die neue liefert `brackets: { meister, lucky_loser, loser }` mit Team-Objekten `{id, name}`.

**Lösung:**
1. Fetch-URL ändern: `/ko-bracket` → `/ko-brackets`
2. Response-Parsing anpassen: `data.brackets.meister/lucky_loser/loser` iterieren
3. `renderCompactBracket()` anpassen: `m.home_team?.id` / `m.home_team?.name` statt `m.home_team_id`
4. Alle 3 Brackets anzeigen mit Überschriften ("Meister", "Lucky Loser", "Verlierer")
5. Champion-Erkennung: Finale des Meister-Brackets prüfen
6. Fallback: Wenn keine Brackets vorhanden → "Noch nicht gestartet"

**Achtung:** Archivierte Saisons nutzen möglicherweise noch das alte KO-Format (vor v2). Der Code muss beide Fälle handhaben — wenn `/ko-brackets` 404 oder leer zurückgibt, Fallback auf `/ko-bracket` (alt) versuchen.

**Dateien:** `archiv.html` (JS-Logik, ~40 Zeilen betroffen)

---

## Zusammenfassung

| # | Änderung | Dateien | Aufwand |
|---|----------|---------|---------|
| 1 | Header-Subtitel `/ Start` | index.html | trivial |
| 2 | `.season-item` in shared.css | shared.css, turnier.html, ko.html | klein |
| 3 | `.btn`-Klassen in shared.css | shared.css, dashboard.html | klein |
| 4 | Tabellen-Alignment | — | keine Änderung |
| 5 | Archiv KO-API Migration | archiv.html | mittel |
