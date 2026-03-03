# BIW Pokal – ARCHITECTURE.md

Dieses Dokument beschreibt die **Ziel‑Architektur** des BIW‑Pokalsystems.
Es leitet sich direkt aus `LOGIC.md` ab und fokussiert auf **Trennung von Verantwortung**, **Automatisierung** und **GitHub‑Tauglichkeit**.

---

## 1. Überblick

**Drei klar getrennte Schichten:**

1. **Automation (n8n)** – Orchestrator
2. **Backend (API)** – Daten & Regeln
3. **Frontend (Webapp)** – Darstellung

Kein CMS. Keine Plugins. Keine implizite Logik.

---

## 2. Automation – n8n (Orchestrator)

### Rolle
- Externe Daten einsammeln
- Prozesse auslösen
- Exporte & Benachrichtigungen steuern

### Verantwortungen
- Ergebnis‑Import (onlineliga → normalisiert)
- Matchday‑Abschluss erkennen
- Spieltags‑Posts erzeugen
- Auto‑Exports (Excel/CSV/JSON)
- Discord‑Webhooks

### Schnittstelle zum Backend
- **REST API** (HTTP)
- n8n schreibt **niemals direkt** in die Datenbank

**Beispiel:**
```
POST /api/matches/import          # Bulk-Import mit Swap-Erkennung + Filterung
POST /api/matchdays/complete
POST /api/posts
GET  /api/exports/matchday/{id}
```

---

## 3. Backend – API (Single Source of Truth)

### Rolle
- Zentrale Geschäftslogik
- Persistenz
- Berechnungen

### Verantwortungen
- CRUD für:
  - Seasons
  - Groups
  - Teams
  - Matches
  - Matchdays
  - Posts
- Berechnung von:
  - Tabellenständen
  - KO‑Weiterkommen
- Validierung von Zuständen

### Eigenschaften
- **Stateless API**
- **Deterministisch**
- **Testbar**

### Technik (offen)
- Node.js (Fastify/Nest) **oder** Python (FastAPI)
- DB: SQLite (lokal) → Postgres (prod)

---

## 4. Frontend – Webapp (Read‑Only)

### Rolle
- Darstellung für Teilnehmer

### Verantwortungen
- Anzeige von:
  - Spielplänen
  - Ergebnissen
  - Gruppen
  - KO‑Baum
  - Spieltags‑Posts

### Prinzipien
- **Keine Logik** im Frontend
- Nur API‑Calls
- Vollständig statisch auslieferbar

### Technik
- React / Vue / Svelte **oder** Vanilla JS
- Hosting:
  - Apache2
  - GitHub Pages
  - Netlify

---

## 5. Datenfluss (vereinfacht)

```
onlineliga.de
     ↓
    n8n
     ↓ (HTTP)
   Backend API
     ↓
  Datenbank
     ↓
  Frontend (Read‑Only)
     ↓
   Teilnehmer
```

---

## 6. Auto‑Export Architektur

### Ablauf
1. n8n triggert Export (Matchday abgeschlossen)
2. Backend generiert Export
3. Rückgabe als Datei‑Stream
4. n8n verteilt:
   - Download
   - Discord

### Formate
- CSV
- XLSX
- JSON

---

## 7. Historische Saisons

- Backend kennt `status = archived`
- Frontend zeigt Archiv getrennt
- n8n greift **nicht** mehr ein

---

## 8. GitHub‑Projektstruktur (Ziel)

```
biw-pokal/
├─ backend/
├─ frontend/
├─ n8n-flows/
├─ docs/
│  ├─ LOGIC.md
│  └─ ARCHITECTURE.md
└─ README.md
```

Alles versionierbar. Alles nachvollziehbar.

---

## 9. Zielbild

Ein **leichtgewichtiges, offenes Turniersystem**,

- das automatisierbar ist
- das verständlich bleibt
- das geteilt werden kann
- das dir gehört

---

_Ende von ARCHITECTURE.md_
