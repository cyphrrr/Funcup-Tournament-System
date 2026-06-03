# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projektübersicht

BIW Pokal ist ein offenes, automatisierbares Turniersystem für Pokal- und Ligawettbewerbe. Es ersetzt WordPress + SportPress durch ein klares, nachvollziehbares System mit drei getrennten Schichten:

1. **n8n** (Automation) - Orchestriert Ergebnis-Import, Matchday-Abschluss, Exporte und Discord-Webhooks
2. **Backend** (FastAPI) - Single Source of Truth für Daten und Geschäftslogik
3. **Frontend** (HTML/JS) - Read-only Webapp für Teilnehmer

## Tech Stack

- **Backend**: FastAPI + SQLAlchemy + SQLite (dev) / Postgres (prod)
- **Frontend**: Vanilla HTML/JS (statisch auslieferbar)
- **Automation**: n8n (Workflows versioniert unter `n8n-flows/`)
- **Auth**: JWT für Browser, API-Key für n8n

## Development Commands

### Backend

```bash
cd backend

# Virtual Environment aktivieren
source .venv/bin/activate  # Linux/Mac
# oder: .venv\Scripts\activate  # Windows

# Dependencies installieren (falls nötig)
pip install fastapi sqlalchemy python-dotenv pyjwt uvicorn

# Server starten
uvicorn app.main:app --reload --port 8000

# Datenbank zurücksetzen (löscht biw.db und startet neu)
rm biw.db
# Bei nächstem Start wird die DB automatisch neu erstellt
```

### Frontend

```bash
cd frontend

# Mit Python HTTP Server
python -m http.server 5500

# Oder mit VS Code Live Server Extension
# → Rechtsklick auf index.html → "Open with Live Server"
```

### Environment

Die Backend-Konfiguration liegt in `backend/.env` (siehe `.env.example` im Projekt-Root für alle Variablen).

**Wichtig**: Alle Credentials (Passwörter, API-Keys, JWT-Secret) müssen vor Production geändert werden!

## Architektur-Highlights

### Saisonbasierte Isolation

- **Jede Saison ist vollständig isoliert** - alle Daten (Gruppen, Teams, Matches) existieren nur im Kontext einer Saison
- Historische Saisons sind `status = archived` und read-only
- Keine rückwirkenden Neuberechnungen

### Datenmodell

Kern-Entitäten (siehe `docs/DATA_MODEL.md`):
- `Season` - Turniersaison (planned/active/archived)
- `Group` - Gruppen innerhalb einer Saison (automatisch generiert, max. 4 Teams)
- `Team` - Teilnehmende Teams (können in mehreren Saisons sein)
- `SeasonTeam` - Zuordnung Team ↔ Saison ↔ Gruppe
- `Match` - Gruppenphase-Spiele
- `KOMatch` - KO-Phase-Spiele mit Bracket-Struktur
- `News` - News-Artikel für die Turnierseite

### Automatische Gruppengenerierung

Gruppen werden beim Erstellen einer Saison automatisch berechnet:
```python
group_count = ceil(participant_count / 4)  # Max. 4 Teams pro Gruppe
```

Teams werden beim Hinzufügen automatisch gleichmäßig verteilt (kleinste Gruppe bevorzugt).

### KO-Bracket-System

Das KO-System unterstützt:
- **Freilose (Byes)** bei nicht-Zweierpotenzen (kein Sonderfall, regulärer Zustand)
- **Automatische Sieger-Weiterleitung**: `next_match_id` + `next_match_slot` ("home"/"away")
- **Bracket-Persistenz**: Vollständiges KO-Bracket wird beim Generieren persistiert
- Round-Robin-Scheduling für Gruppenphase

### Auth-System

Zwei Auth-Mechanismen parallel:
- **JWT Bearer Token** für Browser/Admin-UI (24h Gültigkeit)
- **X-API-Key Header** für n8n-Automatisierung

Geschützte Endpoints verwenden `Depends(get_current_user)`.

### Berechnete Daten

**Nie persistieren**, immer on-the-fly berechnen:
- Tabellenstände (siehe `GET /groups/{id}/standings`)
- Tordifferenzen
- Ranglisten
- KO-Weiterkommen

### Schema-Migrationen (additiv, automatisch)

Beim Start ergänzt `run_auto_migrations(engine)` (`backend/app/migrations.py`, aufgerufen in `main.py` nach `create_all`) fehlende Modell-Spalten in bestehenden Tabellen per `ALTER TABLE ... ADD COLUMN`.

- **Greift automatisch:** neue Spalte zu einem Modell hinzufügen → beim nächsten Start in der DB. Kein Alembic, kein manuelles `ALTER` nötig.
- **Greift NICHT:** Spalten umbenennen/löschen, Typänderungen, neue Constraints/Indizes, Daten-Backfills. Solche strukturellen Änderungen weiterhin manuell migrieren oder DB neu erzeugen.
- Spalten werden **nullable und ohne `server_default`** ergänzt (SQLite-`ALTER` kann keine non-konstanten Defaults wie `CURRENT_TIMESTAMP` setzen). Python-seitige `default=` greifen bei neuen Inserts; Bestandszeilen erhalten `NULL`.

## Versionierung

Das Projekt nutzt Semantic Versioning (SemVer) mit Beta-Suffix.

- **Single Source of Truth:** `VERSION` Datei im Projekt-Root (z.B. `0.9.0-beta`)
- **Backend:** `main.py` liest VERSION-Datei, exportiert als `APP_VERSION`
- **API:** `GET /api/version` → `{"version":"0.9.0-beta","app":"BIW Pokal","status":"beta"}`
- **Frontend:** `js/version.js` fetcht `/api/version` und zeigt Version im Footer (`#app-version`)
- **Admin:** Sidebar-Bottom zeigt Version (`#admin-version`)
- **Git-Tags:** Jede Version wird als annotierter Git-Tag gesetzt (`v0.9.0-beta`)
- **Release-Script:** `./scripts/release.sh [patch|minor|major] [beta|stable]`

### Regeln
- Version **NUR** über die VERSION-Datei ändern, nie hardcoded in Code
- Nach Änderung: `release.sh` nutzen (committed, taggt, und zeigt Push-Befehl)
- PATCH = Bugfix, MINOR = neues Feature, MAJOR = Stable Release (1.0.0)

## API-Endpunkte (Wichtigste)

```
# Auth
POST /api/login                              # JWT Token holen
GET  /api/me                                 # Auth testen

# Seasons & Groups
POST /api/seasons                            # Saison + Gruppen erstellen
GET  /api/seasons                            # Alle Saisons
GET  /api/seasons/{id}/groups                # Gruppen einer Saison

# Teams
POST /api/seasons/{id}/teams                 # Einzelnes Team hinzufügen
POST /api/seasons/{id}/teams/bulk            # Mehrere Teams auf einmal
GET  /api/seasons/{id}/groups-with-teams     # Gruppen + Teams + Matches

# Gruppenphase
POST /api/groups/{id}/generate-schedule      # Round-Robin Spielplan generieren
POST /api/groups/{id}/matches                # Match manuell anlegen
PATCH /api/matches/{id}                      # Ergebnis eintragen
GET  /api/groups/{id}/standings              # Tabelle berechnen
POST /api/matches/import                     # Bulk-Import (n8n) mit Swap-Erkennung

# KO-Phase
POST /api/seasons/{id}/ko-bracket/generate   # KO-Bracket erstellen (einmalig)
GET  /api/seasons/{id}/ko-bracket            # Bracket abrufen
PATCH /api/ko-matches/{id}                   # KO-Ergebnis → Sieger-Weiterleitung

# News
POST /api/news                               # Artikel erstellen
GET  /api/news                               # Alle Artikel (default: nur published)
PATCH /api/news/{id}                         # Artikel aktualisieren
DELETE /api/news/{id}                        # Artikel löschen

# Traffic Stats
POST /api/track                              # Page View tracken (öffentlich, kein Auth)
GET  /api/admin/stats?days=7                 # Besucherstatistiken (Auth erforderlich)

# System
GET  /api/version                            # App-Version & Status (public, kein Auth)
```

## Wichtige Code-Patterns

### Match-Ergebnis eintragen mit Auto-Status

```python
# Gruppenphase (api.py:186)
if match.home_goals is not None and match.away_goals is not None:
    if match.status == "scheduled":
        match.status = "played"
```

### KO-Sieger automatisch weiterleiten

```python
# KO-Phase (api.py:523-544)
if winner_id and match.next_match_id:
    next_match = db.get(KOMatch, match.next_match_id)
    if match.next_match_slot == "home":
        next_match.home_team_id = winner_id
    else:
        next_match.away_team_id = winner_id
```

### Tabelle berechnen (Punkte, Tordifferenz, Tore)

```python
# api.py:252-303
table.sort(
    key=lambda x: (
        x["points"],
        x["goals_for"] - x["goals_against"],
        x["goals_for"]
    ),
    reverse=True
)
```

## Datenfluss (vereinfacht)

```
onlineliga.de
     ↓
    n8n                    ← Ergebnis-Import, Normalisierung
     ↓ (HTTP)
  Backend API              ← Validierung, Berechnung, Persistenz
     ↓
  SQLite DB (biw.db)
     ↓
  Frontend                 ← Read-only Darstellung
     ↓
  Teilnehmer
```

n8n schreibt **niemals direkt** in die DB, nur via API.

## Dokumentation

Fachliche und technische Details siehe:
- `docs/LOGIC.md` - Fachliche Logik (Turnierphasen, Automatismen, Weiterkommen)
- `docs/ARCHITECTURE.md` - System-Architektur (Schichten, Schnittstellen, Verantwortungen)
- `docs/DATA_MODEL.md` - Logisches Datenmodell (Tabellen, Beziehungen, Constraints)
- `docs/CHANGELOG.md` - Änderungsprotokoll (wird bei jeder Änderung aktualisiert)

Diese Dokumente sind **technologie-agnostisch** und Single Source of Truth für alle Implementierungen.

## Frontend-Struktur

- `index.html` - Read-only Public View (Gruppen, Tabellen, KO-Bracket, News)
- `admin.html` - Admin-Interface (Saison anlegen, Teams, Ergebnisse, News)

Frontend ist vollständig statisch und kann auf Apache2, GitHub Pages oder Netlify gehostet werden.

## Testing-Workflow

```bash
# 1. Backend starten
cd backend && uvicorn app.main:app --reload

# 2. Admin-UI öffnen
# → http://127.0.0.1:5500/admin.html

# 3. Neue Saison anlegen
# → Login mit den Credentials aus backend/.env
# → "Neue Saison" → Teilnehmerzahl eingeben
# → Gruppen werden automatisch erstellt

# 4. Teams hinzufügen
# → Bulk-Import via Textarea (ein Name pro Zeile)

# 5. Spielplan generieren
# → Pro Gruppe "Spielplan generieren"

# 6. Ergebnisse eintragen
# → Match anklicken → Tore eingeben → speichern

# 7. Tabelle ansehen
# → Public View: http://127.0.0.1:5500/index.html
```

## n8n-Integration

n8n-Flows liegen unter `n8n-flows/` (versioniert).

n8n authentifiziert sich via `X-API-Key` Header (Key aus `backend/.env`).

Typische n8n-Workflows:
- Ergebnis-Import von onlineliga.de
- Matchday-Abschluss-Erkennung
- Auto-Exports (CSV/XLSX/JSON)
- Discord-Webhooks

### Ergebnis-Import Flow (n8n → Backend)

**Node-Kette:** Scrape/Fetch → Aggregate → HTTP Request

1. **Vorherige Node** liefert einzelne Items mit Feldern: `Heim`, `Gast`, `Heimtore`, `Gasttore`, `Saison`, `Spieltag`
2. **Aggregate Node** (Transform Data): Bündelt alle Items zu einem Array
   - Operation: `Aggregate All Item Data`
   - Output Field Name: `payload`
3. **HTTP Request Node**:
   - Method: `POST`
   - URL: `https://beta.biw-pokal.de/api/matches/import`
   - Header: `X-API-Key` = API-Key
   - Body: JSON → `={{ $json.payload }}`

**Input-Format** (JSON Array):
```json
[{
  "Heim": "VFB_Münster",
  "Gast": "FC Honda",
  "Heimtore": "2",
  "Gasttore": "0",
  "Saison": "test",
  "Spieltag": "SP2"
}]
```

**Response-Format**:
```json
{
  "imported": 15,
  "skipped": 5,
  "swapped": 2,
  "errors": [
    {"heim": "Fronx Finest", "gast": "Grootmania", "reason": "no_match"}
  ]
}
```

**Skip-Gründe**: `not_found` (Team unbekannt), `no_match` (Paarung nicht im Spielplan), `already_played` (bereits eingetragen)
