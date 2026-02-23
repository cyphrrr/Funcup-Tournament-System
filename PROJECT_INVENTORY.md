# BIW Pokal – Vollständige Projekt-Bestandsaufnahme

> Stand: 2026-02-23 | Letzter Commit: `ba140c0` (feat(admin): eigene KO-Phase Section mit 3-Bracket-Verwaltung)

---

## 1. Was ist das Projekt?

**BIW Pokal** ist ein offenes Turniersystem für Pokal- und Ligawettbewerbe (onlineliga.de). Es ersetzt WordPress + SportPress durch ein 3-Schichten-System:

1. **n8n** – Automation (Ergebnis-Import, Exports, Discord-Webhooks)
2. **FastAPI Backend** – Single Source of Truth (API + Geschäftslogik + DB)
3. **Statisches Frontend** – Read-only Webapp für Teilnehmer

Zusätzlich: **Discord Bot** für Teilnahme-Management und Team-Claims.

---

## 2. Tech Stack

| Schicht | Technologie | Details |
|---------|-------------|---------|
| Backend | Python 3.13, FastAPI 0.109, SQLAlchemy 2.0 | `uvicorn` als ASGI-Server |
| Datenbank | SQLite (dev) / PostgreSQL 15 (prod) | Über `DATABASE_URL` gesteuert |
| Frontend | Vanilla HTML/JS/CSS | Kein Framework, statisch auslieferbar |
| Discord Bot | py-cord >= 2.6, aiohttp | Slash Commands, Cog-basiert |
| Automation | n8n | Workflows unter `n8n-flows/` versioniert |
| Auth | JWT (Browser) + API-Key (n8n) | Parallel, `get_current_user()` akzeptiert beides |
| Deployment | Docker Compose, Nginx Reverse Proxy | PostgreSQL, SSL via Let's Encrypt |
| Bilder | Pillow | Wappen-Upload mit Resize (max 512×512) |
| Ranking | Google Sheets CSV | Tiebreaker bei KO-Unentschieden |

---

## 3. Verzeichnisstruktur

```
Funcup-Tournament-System/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI App-Init, CORS, Router, Static Files
│   │   ├── api.py               # ALLE API-Endpoints (~2.654 Zeilen, 65+ Endpoints)
│   │   ├── models.py            # SQLAlchemy Models (9 Tabellen)
│   │   ├── schemas.py           # Pydantic Schemas (~334 Zeilen)
│   │   ├── auth.py              # JWT + API-Key Auth
│   │   ├── db.py                # Engine + SessionLocal
│   │   ├── ko_bracket_generator.py  # 3-Bracket KO-Generierung
│   │   ├── ranking_service.py   # Google Sheets Ranking-Integration
│   │   ├── discord_oauth.py     # Discord OAuth2 Flow (Authlib)
│   │   └── image_utils.py       # Wappen-Upload (Pillow)
│   ├── scripts/
│   │   └── migrate_prod.py      # Prod-DB-Migration (fehlende Spalten)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── biw.db                   # Dev-Datenbank (SQLite)
│
├── frontend/
│   ├── index.html               # Public Home (Gruppen, News, KO-Preview)
│   ├── admin.html               # Admin-Panel (~2.683 Zeilen, 8 Sections)
│   ├── turnier.html             # Turnier-Übersicht
│   ├── ko.html                  # KO-Bracket Visualisierung
│   ├── archiv.html              # Vergangene Saisons
│   ├── ewige-tabelle.html       # Ewige Tabelle (alle Saisons)
│   ├── team.html                # Team-Profil
│   ├── regeln.html              # Turnierregeln
│   ├── datenschutz.html         # Datenschutz
│   ├── impressum.html           # Impressum
│   ├── js/
│   │   └── config.js            # API-URL Auto-Detection (localhost vs prod)
│   └── img/                     # Bilder/Assets
│
├── bot/
│   ├── main.py                  # Discord Bot Entry (py-cord)
│   ├── cogs/
│   │   ├── teilnahme.py         # /dabei, /status Commands
│   │   └── profil.py            # /profil, /wappen Commands
│   ├── utils/
│   │   └── api_client.py        # Async HTTP Client für Backend
│   ├── Dockerfile
│   └── requirements.txt
│
├── docs/
│   ├── LOGIC.md                 # Fachliche Logik (Turnierphasen)
│   ├── ARCHITECTURE.md          # System-Architektur (3 Schichten)
│   └── DATA_MODEL.md            # Logisches Datenmodell
│
├── n8n-flows/                   # Exportierte n8n Workflow-JSONs
├── scripts/
│   └── migrate_ko_brackets.py   # Migration: KO-Bracket-System
├── import_seasons.py            # Historische Saison-Imports
├── import-script/               # Legacy Import-Tools
├── import-neu/                  # Neue Import-Tools
├── REST-IMPORT/                 # REST-API Import-Doku
├── uploads/                     # User-Uploads (Wappen)
│
├── docker-compose.yml           # Prod: Backend + Postgres + Frontend + Bot
├── docker-compose.sqlite.yml    # SQLite-Alternative
├── docker-compose.dev.yml       # Entwicklung
├── nginx.conf                   # Reverse Proxy Config
├── Makefile                     # Build/Deploy Shortcuts
├── .env.example                 # Env-Template (alle Variablen)
├── .env                         # Aktive Konfiguration (secret)
├── CLAUDE.md                    # Claude Code Instruktionen
├── .claude.md                   # Projekt-Notizen
├── DEPLOYMENT.md                # Produktions-Deployment-Guide
└── README.md                    # Projekt-Übersicht
```

---

## 4. Datenmodell (models.py)

### 9 Tabellen

```
seasons
├── id (PK), name, participant_count, status ("planned"|"active"|"archived"), created_at
│
groups
├── id (PK), season_id (FK→seasons), name ("A","B",...), sort_order
│
teams
├── id (PK), name, logo_url?, onlineliga_url?
│
season_teams
├── id (PK), season_id (FK→seasons), team_id (FK→teams), group_id (FK→groups)?
│
matches
├── id (PK), season_id (FK), group_id (FK), home_team_id (FK), away_team_id (FK)
├── home_goals?, away_goals?, status ("scheduled"|"played"), matchday?, ingame_week?
│
ko_brackets
├── id (PK), season_id (FK), bracket_type ("meister"|"lucky_loser"|"loser")
├── status ("pending"|"active"|"completed"), generated_at?, created_at
├── UNIQUE(season_id, bracket_type)
│
ko_matches
├── id (PK), season_id (FK), bracket_type, round, position
├── home_team_id (FK)?, away_team_id (FK)?, home_goals?, away_goals?
├── is_bye (0|1), status ("pending"|"scheduled"|"played"), ingame_week?
├── next_match_id (FK→ko_matches)?, next_match_slot ("home"|"away")?
│
news
├── id (PK), title, content, author, published (0|1), created_at
│
user_profiles
├── id (PK), discord_id (UNIQUE), discord_username?, discord_avatar_url?
├── team_id (FK→teams)?, profile_url?, participating_next (bool), crest_url?
├── access_token?, refresh_token?, token_expires_at?
├── created_at, updated_at
```

### Beziehungen
- `Season` 1→N `Group` 1→N `SeasonTeam` N→1 `Team`
- `Season` 1→N `Match` (via group_id)
- `Season` 1→N `KOBracket` 1→N `KOMatch`
- `KOMatch` → `KOMatch` (self-ref via next_match_id)
- `UserProfile` N→1 `Team` (optional, via team_id)

---

## 5. API-Endpoints (api.py – vollständig)

### Auth
| Method | Route | Auth | Beschreibung |
|--------|-------|------|-------------|
| POST | `/api/login` | – | JWT Token holen |
| GET | `/api/me` | JWT/Key | Auth-Test |

### Seasons & Groups
| Method | Route | Auth | Beschreibung |
|--------|-------|------|-------------|
| POST | `/api/seasons` | JWT/Key | Saison erstellen (auto Gruppen, optional `group_count`) |
| GET | `/api/seasons` | – | Alle Saisons |
| GET | `/api/seasons/{id}` | – | Einzelne Saison |
| PATCH | `/api/seasons/{id}` | JWT/Key | Saison updaten (name, status) |
| DELETE | `/api/seasons/{id}` | JWT/Key | Saison löschen (kaskadierend) |
| GET | `/api/seasons/{id}/groups` | – | Gruppen einer Saison |
| GET | `/api/seasons/{id}/groups-with-teams` | – | Gruppen + Teams + Matches |

### Teams
| Method | Route | Auth | Beschreibung |
|--------|-------|------|-------------|
| GET | `/api/teams/search` | – | Suche via `?search=` oder `?name=`, `?limit=` |
| GET | `/api/teams/{id}` | – | Team-Detail mit Stats + letzten 5 Spielen |
| PATCH | `/api/teams/{id}` | JWT/Key | Team-Daten updaten |
| POST | `/api/seasons/{id}/teams` | JWT/Key | Team zu Saison hinzufügen (auto Gruppe) |
| POST | `/api/seasons/{id}/teams/bulk` | JWT/Key | Bulk-Import (Liste von Namen) |

**WICHTIG:** `/teams/search` muss VOR `/teams/{team_id}` registriert sein (FastAPI Route-Shadowing-Bug, gefixt in Commit `52d6fef`).

### Gruppenphase
| Method | Route | Auth | Beschreibung |
|--------|-------|------|-------------|
| POST | `/api/groups/{id}/matches` | JWT/Key | Match manuell anlegen |
| PATCH | `/api/matches/{id}` | JWT/Key | Ergebnis eintragen (auto status→"played") |
| POST | `/api/groups/{id}/generate-schedule` | JWT/Key | Round-Robin Spielplan generieren |
| GET | `/api/groups/{id}/standings` | – | Tabelle berechnen (live) |

### KO-Phase (Legacy Single-Bracket)
| Method | Route | Auth | Beschreibung |
|--------|-------|------|-------------|
| GET | `/api/seasons/{id}/ko-plan` | – | Logischer KO-Plan (ohne Persistenz) |
| POST | `/api/seasons/{id}/ko-bracket/generate` | JWT/Key | Einzelnes KO-Bracket persistieren |
| GET | `/api/seasons/{id}/ko-bracket` | – | Einzelnes Bracket abrufen |

### KO-Phase (3-Bracket-System – aktiv genutzt)
| Method | Route | Auth | Beschreibung |
|--------|-------|------|-------------|
| POST | `/api/seasons/{id}/ko-brackets/generate` | JWT/Key | 3 Brackets generieren (meister/lucky_loser/loser) |
| GET | `/api/seasons/{id}/ko-brackets` | – | Alle Brackets einer Saison (mit Runden + Matches) |
| GET | `/api/seasons/{id}/ko-brackets/status` | – | Status-Übersicht (matches_played/total pro Bracket) |
| POST | `/api/seasons/{id}/ko-brackets/reset` | JWT/Key | Alle KO-Brackets + Matches löschen |
| POST | `/api/seasons/{id}/ko-brackets/create-empty` | JWT/Key | Leeres Bracket-Gerüst (bracket_type, team_count) |
| PATCH | `/api/ko-matches/{id}` | JWT/Key | KO-Ergebnis eintragen + Sieger-Weiterleitung |
| PATCH | `/api/ko-matches/{id}/set-team` | JWT/Key | Manuell Team in Slot setzen (home/away) |
| PATCH | `/api/ko-matches/{id}/set-bye` | JWT/Key | Match als Freilos markieren + weiterleiten |

### News
| Method | Route | Auth | Beschreibung |
|--------|-------|------|-------------|
| POST | `/api/news` | JWT/Key | Artikel erstellen |
| GET | `/api/news` | – | Liste (default: nur published) |
| GET | `/api/news/{id}` | – | Einzelner Artikel |
| PATCH | `/api/news/{id}` | JWT/Key | Artikel updaten |
| DELETE | `/api/news/{id}` | JWT/Key | Artikel löschen |

### Matchday-Verwaltung
| Method | Route | Auth | Beschreibung |
|--------|-------|------|-------------|
| GET | `/api/seasons/{id}/matchdays` | – | Max Spieltag einer Saison |
| GET | `/api/seasons/{id}/matchday/{n}` | – | Alle Matches eines Spieltags |
| GET | `/api/groups/{id}/matchdays` | – | Max Spieltag einer Gruppe |
| GET | `/api/groups/{id}/matchday/{n}` | – | Matches eines Gruppen-Spieltags |
| GET | `/api/matches/batch` | – | Mehrere Matches auf einmal (Komma-IDs) |
| GET | `/api/ko-matches/batch` | – | Mehrere KO-Matches auf einmal |

### Statistiken & Ranking
| Method | Route | Auth | Beschreibung |
|--------|-------|------|-------------|
| GET | `/api/all-time-standings` | – | Ewige Tabelle (alle Saisons aggregiert) |
| GET | `/api/ranking/team/{name}` | – | Google Sheets Ranking für ein Team |
| GET | `/api/ranking/all` | – | Alle Rankings aus Google Sheets |

### Discord Bot Integration
| Method | Route | Auth | Beschreibung |
|--------|-------|------|-------------|
| POST | `/api/discord/users/ensure` | – | Upsert User (bei jedem Bot-Command) |
| GET | `/api/discord/users/{discord_id}` | – | User-Profil abrufen |
| PATCH | `/api/discord/users/{discord_id}/participation` | – | Teilnahme setzen |
| PATCH | `/api/discord/users/{discord_id}/profile` | – | Profil-URL speichern |
| PATCH | `/api/discord/users/{discord_id}` | JWT/Key | Admin: User updaten |
| POST | `/api/discord/users/register` | JWT/Key | Admin: User registrieren |
| POST | `/api/discord/users/{discord_id}/claim-team` | – | Self-Service Team-Claim |
| PATCH | `/api/discord/users/{discord_id}/admin-set-team` | JWT/Key | Admin: Team zuweisen |
| GET | `/api/discord/participation-report` | JWT/Key | Teilnahme-Report |
| GET | `/api/discord/users` | JWT/Key | Alle User listen (Filter: search, has_team) |
| DELETE | `/api/discord/users/{discord_id}` | JWT/Key | User löschen |

### Discord OAuth2
| Method | Route | Auth | Beschreibung |
|--------|-------|------|-------------|
| GET | `/api/auth/discord/login` | – | OAuth2 Login-Redirect |
| GET | `/api/auth/discord/callback` | – | OAuth2 Callback |

### File Upload
| Method | Route | Auth | Beschreibung |
|--------|-------|------|-------------|
| POST | `/api/upload/crest` | – | Wappen hochladen (Pillow resize) |
| DELETE | `/api/upload/crest` | – | Wappen löschen |
| GET | `/api/upload/crest/{discord_id}` | – | Wappen abrufen |

### Health
| Method | Route | Auth | Beschreibung |
|--------|-------|------|-------------|
| GET | `/health` | – | Health Check (kein /api Prefix!) |

---

## 6. Zentrale Geschäftslogik

### Automatische Gruppengenerierung (api.py, create_season)
```python
# Manuell wenn group_count übergeben, sonst automatisch
if season.group_count is not None and season.group_count > 0:
    group_count = season.group_count
else:
    group_count = (participant_count + 3) // 4  # Max 4 Teams pro Gruppe
```
Teams werden bei Hinzufügen automatisch in die kleinste Gruppe verteilt.

### Match-Ergebnis mit Auto-Status
```python
if match.home_goals is not None and match.away_goals is not None:
    if match.status == "scheduled":
        match.status = "played"
```

### KO-Sieger-Weiterleitung
```python
if winner_id and match.next_match_id:
    next_match = db.get(KOMatch, match.next_match_id)
    if match.next_match_slot == "home":
        next_match.home_team_id = winner_id
    else:
        next_match.away_team_id = winner_id
```

### Tabellen-Sortierung
```python
table.sort(key=lambda x: (x["points"], x["goals_for"] - x["goals_against"], x["goals_for"]), reverse=True)
# Punkte: Sieg=3, Unentschieden=1, Niederlage=0
```

### 3-Bracket KO-System (ko_bracket_generator.py)
- **Meister-Bracket**: Gruppenrste qualifizieren sich
- **Lucky-Loser-Bracket**: Gruppenzweite
- **Loser-Bracket**: Gruppendritte
- Gespiegeltes Seeding (Stärkster vs. Schwächster)
- Freilose bei nicht-Zweierpotenzen automatisch berechnet
- Tiebreaker bei Unentschieden: Google Sheets Ranking (niedrigerer Ø = besser)

### Team-Claim Validierung (5 Schritte)
1. User muss existieren (404)
2. User muss Profil-URL gesetzt haben (403)
3. Team muss existieren (404)
4. User darf noch kein Team haben (409)
5. Team darf nicht von anderem User geclaimed sein (409)

---

## 7. Frontend-Architektur

### API-URL-Erkennung (js/config.js)
```javascript
// Lokal: http://localhost:8000 oder http://192.168.x.x:8000
// Produktion: window.location.origin (Nginx Proxy leitet /api/* weiter)
```

### Seiten-Übersicht
| Seite | Zweck | API-Calls |
|-------|-------|-----------|
| `index.html` | Public Home | seasons, groups-with-teams, standings, news, ko-bracket |
| `admin.html` | Admin-Panel | ALLE Endpoints (CRUD für alles) |
| `turnier.html` | Turnier-Detail | seasons/{id}, groups, standings, matchdays |
| `ko.html` | KO-Bracket | ko-brackets, ko-matches |
| `archiv.html` | Archiv | seasons (archived), standings |
| `ewige-tabelle.html` | Ewige Tabelle | all-time-standings |
| `team.html` | Team-Profil | teams/{id} |

### admin.html Sections (Sidebar-Navigation)
1. **Dashboard** – Statistik-Übersicht, Schnellaktionen
2. **Ergebnisse** – Gruppenphase-Ergebnisse eintragen, Spielplan generieren
3. **KO-Phase** – Eigene Section: 3 Brackets (Meister/Lucky Loser/Loser), Status, Auto/Manuell-Generierung, Inline-Edit mit Winner-Select, Team-Setzen, Freilose, Reset
4. **Teams** – Teams verwalten, Bulk-Import, Logo/URL bearbeiten
5. **Saisons** – Saison erstellen/löschen, Status ändern
6. **Discord Users** – Teilnahme-Report, User-Verwaltung, Team-Zuordnung
7. **News** – Artikel CRUD mit Match-Inserter (Gruppen + KO)
8. **Saison-Setup** – 4-Tab-Wizard (Saison, Teams, Gruppen, Spielplan)

---

## 8. Discord Bot (bot/)

### Architektur
- **py-cord** (Fork von discord.py) für Slash Commands
- **Cog-basiert**: Modular erweiterbar
- **Async HTTP Client** (`utils/api_client.py`) kommuniziert mit Backend

### Commands
| Command | Cog | Beschreibung |
|---------|-----|-------------|
| `/dabei ja\|nein` | teilnahme.py | Teilnahme am nächsten Pokal setzen |
| `/status` | teilnahme.py | Eigenen Status anzeigen (Team, Profil, Teilnahme) |
| `/profil <url>` | profil.py | Onlineliga Profil-URL speichern |
| `/wappen` | profil.py | Link zum Wappen-Upload Dashboard |

### Flow: User-Lifecycle
1. Jeder Bot-Command ruft zuerst `/discord/users/ensure` (Upsert)
2. User setzt Profil-URL via `/profil`
3. User claimed Team via Team-Select UI (Autocomplete-Suche)
4. Admin kann Team manuell zuweisen via Admin-Panel

---

## 9. Deployment

### Lokal
```bash
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000
cd frontend && python -m http.server 5500
```

### Produktion (Docker)
```bash
docker compose up -d          # Backend + Postgres + Frontend + Bot
# Frontend: https://beta.biw-pokal.de (Nginx auf 9988/9977)
# Backend intern: http://biw-backend:8000
# Postgres intern: biw-postgres:5432
```

### Docker Services
| Service | Container | Ports | Abhängigkeiten |
|---------|-----------|-------|----------------|
| backend | biw-backend | 8000 (intern) | postgres (healthy) |
| postgres | biw-postgres | 5432 (intern) | – |
| frontend | biw-frontend | 9988:80, 9977:443 | backend |
| bot | biw-bot | – | backend (healthy) |

### Environment-Variablen (.env.example)
```
ADMIN_USER, ADMIN_PASSWORD, API_KEY, JWT_SECRET
POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
DISCORD_BOT_TOKEN, DISCORD_GUILD_ID, DASHBOARD_URL
DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET, DISCORD_REDIRECT_URI
UPLOAD_DIR, MAX_FILE_SIZE, CREST_MAX_WIDTH, CREST_MAX_HEIGHT
```

---

## 10. Auth-System (auth.py)

### Zwei parallele Mechanismen
1. **JWT Bearer Token** – Browser/Admin-UI, 24h Gültigkeit, HS256
   - Login: `POST /api/login` → `{"access_token": "..."}`
   - Nutzung: `Authorization: Bearer <token>`

2. **API-Key Header** – n8n Automation
   - Nutzung: `X-API-Key: <key>`
   - Identifiziert als "api-user"

### Dependency
- `get_current_user()` – Erfordert JWT ODER API-Key (401 sonst)
- `get_optional_user()` – Optional, gibt None zurück wenn nicht authentifiziert

---

## 11. Bekannte Bugs & Fixes

| Problem | Status | Commit |
|---------|--------|--------|
| `/teams/search` als team_id interpretiert (422) | **Gefixt** | `52d6fef` |
| Backend .env nicht gefunden bei bestimmten Pfaden | **Gefixt** | `e518511` |
| POSTGRES_* Env-Vars in migrate_prod.py | **Gefixt** | `84a8b5e` |
| 5-Team Saison erstellt 2 Gruppen statt 1 | **Workaround**: Saison mit 4 erstellen, 5. manuell hinzufügen | – |

---

## 12. Sicherheitsregeln

- **NIEMALS** Datenbank-Dateien löschen (`rm *.db` verboten)
- **NIEMALS** systemctl restart ohne explizite Anweisung
- Vor destruktiven Aktionen immer Backup: `cp biw.db biw.db.backup.$(date +%Y%m%d_%H%M%S)`
- DB-Schema-Probleme via Migration lösen, nicht via Reset
- Default-Credentials in `.env.example` müssen vor Production geändert werden

---

## 13. Git-History (letzte 25 Commits)

```
ba140c0 feat(admin): eigene KO-Phase Section mit 3-Bracket-Verwaltung
6f42edb feat(admin): KO-Phase auf 3-Bracket-System umstellen
5854a1c docs: add comprehensive project inventory for context continuity
3613782 feat(api): extend endpoints for admin season setup
da4a740 feat(admin): Saison-Setup Panel mit 4 Tabs
52d6fef fix: move /teams/search route before /teams/{team_id}
e518511 fix: search both backend/.env and root/.env for database config
84a8b5e fix: support POSTGRES_* env vars in migrate_prod.py
00873a0 chore: update .claude.md with security rules and project structure
478ed87 feat: add prod DB migration script for missing columns
6391957 style: add background to KO bracket tab bar in admin panel
3ad702c fix: restore dark sidebar after dark-mode-only conversion
bb70d84 style: convert admin panel to dark mode only
5739d3b style: improve KO bracket readability
1fc48ff feat: Manuelles KO-Bracket-Bauen im Admin Panel
2ae9493 fix: Status-Feld von 'exists' zu 'brackets_generated' korrigiert
f47e824 feat: KO-Phase Frontend auf 3 parallele Brackets umgebaut
140f025 feat: Google Sheets Ranking-Integration als KO-Match Tiebreaker
7967518 fix: discord_id in /dabei und /status Commands definieren
df56dbb feat: KO-Bracket API-Endpoints implementiert
eba36b4 feat: 3-Bracket KO-System Datenmodell
5fffef7 feat: Discord User-Verwaltung im Admin Panel
07f4ac9 feature: Profile URL Validierung beim Team-Claim
b59f90a refactor: Zentrale _ensure_user() Hilfsmethode für Auto-Registration
17931bf feat: Discord Bot Auto-Registrierung + Enhanced /claim Command
```

---

## 14. Aktueller Stand / Offene Punkte

- **KO-Phase Admin** komplett auf 3-Bracket-System umgestellt (`ba140c0`): Eigene Section mit Status, Auto/Manuell-Generierung, Inline-Edit, Team-Setzen, Freilose
- Admin-Panel hat 8 Sections (Dashboard, Ergebnisse, KO-Phase, Teams, Saisons, Discord Users, News, Saison-Setup)
- Production-Deployment auf `beta.biw-pokal.de` läuft via Docker
- n8n-Workflows sind unter `n8n-flows/` versioniert aber nicht im Detail dokumentiert
- Legacy Single-Bracket Endpoints (`/ko-bracket`) existieren noch im Backend, werden aber nicht mehr vom Frontend genutzt
