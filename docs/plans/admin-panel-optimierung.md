# Admin Panel Optimierung — Umsetzungsplan

> Erstellt: 2026-03-03 | Basierend auf Code-Review von `admin.html` (3.058 Zeilen) und `api.py` (2.850 Zeilen)

---

## Phase 1: Sicherheit (Kritisch)

**Empfohlenes Model:** Sonnet — klare, isolierte Fixes

### 1.1 Discord-Write-Endpoints absichern
**Dateien:** `backend/app/api.py`
**Problem:** 4 Endpoints erlauben unauthentifizierte Schreibzugriffe auf User-Daten.
**Fix:** `Depends(get_current_user)` oder API-Key-Check hinzufügen:
- `POST /discord/users/ensure` (Zeile ~1177)
- `PATCH /discord/users/{id}/participation` (Zeile ~1284)
- `PATCH /discord/users/{id}/profile` (Zeile ~1331)
- `POST /discord/users/{id}/claim-team` (Zeile ~1558)

**Achtung:** Der Discord-Bot nutzt diese Endpoints. Sicherstellen, dass der Bot den API-Key mitsendet (`X-API-Key` Header). Auch `bot/utils/api_client.py` prüfen.

### 1.2 XSS in onclick-Handlern fixen
**Dateien:** `frontend/admin.html`
**Problem:** Teamnamen werden unzureichend escaped in dynamisch generierte `onclick`-Attribute injiziert.
**Betroffene Stellen:**
- Zeile ~971: `searchTeamForManual()` — Teamname in onclick
- Zeile ~2207: `searchTeamsForModal()` — Teamname in onclick

**Fix:** Statt Inline-onclick mit String-Interpolation → Event-Delegation oder `data-*` Attribute + `addEventListener`.

### 1.3 Duplikat-Team-Check
**Dateien:** `backend/app/api.py`
**Problem:** Ein Team kann mehrfach in dieselbe Saison eingetragen werden.
**Fix:** Vor `db.add(SeasonTeam(...))` prüfen:
```python
existing = db.query(SeasonTeam).filter_by(season_id=season_id, team_id=team_id).first()
if existing:
    raise HTTPException(400, "Team bereits in dieser Saison")
```
**Stellen:** `add_team_to_season` (Zeile ~309), `bulk_add_teams` (Zeile ~352)

---

## Phase 2: Toten Code entfernen

**Empfohlenes Model:** Sonnet — mechanisches Aufräumen

### 2.1 Frontend Dead Code
**Datei:** `frontend/admin.html`
Folgende Funktionen/Variablen entfernen:
- `initDarkMode()` (Zeile ~2124-2144) — referenziert `#dark-mode-toggle` das nicht existiert
- `registerDiscordUser()` (Zeile ~2260-2289) — referenziert nicht existierende DOM-IDs
- `userSearchTimeout` (Zeile ~2148) — deklariert, nie benutzt
- `renderManualAdditions()` (Zeile ~953-956) — leere Funktion
- Sinnloses `setTimeout` in der Debounce-Funktion (Zeile ~3036)

### 2.2 Backend Dead Code
**Datei:** `backend/app/api.py`
- Alte `PATCH /ko-matches/{id}` Route (Zeile ~793) entfernen — wird von neuerer Route (Zeile ~2370) überschrieben
- Prüfen welche Endpoints noch vom Frontend/Bot genutzt werden (ggf. `loadDiscordUsers` Legacy-Alias)

---

## Phase 3: Performance

**Empfohlenes Model:** Opus — komplexe Query-Optimierung erfordert Verständnis der Datenstrukturen

### 3.1 N+1 Queries in `all-time-standings` beheben
**Datei:** `backend/app/api.py` (Zeile ~1053-1171)
**Problem:** Für jedes Team 4 separate Queries → bei 100 Teams = 400+ Queries.
**Fix:** Alle Matches in 2 Bulk-Queries laden (Group + KO), dann in Python aggregieren:
```python
all_matches = db.query(Match).filter(Match.status == "played").all()
all_ko = db.query(KOMatch).filter(KOMatch.status == "played").all()
# In-memory Aggregation pro Team
```

### 3.2 Weitere N+1 Hotspots
- `get_team_detail` (Zeile ~180): Pro Match 2 Extra-Queries → JOINs oder eager loading
- `list_discord_users` (Zeile ~1815): Pro User Team-Query → `joinedload(UserProfile.team)`
- `get_participation_report` (Zeile ~1643): Gleicher Ansatz
- `get_season_ko_brackets` (Zeile ~2263): Teams pro Match einzeln geladen + `max(round)` in innerer Schleife

### 3.3 Frontend API-Calls parallelisieren
**Datei:** `frontend/admin.html`
- `loadDashboard()` (Zeile ~1365): Saisons sequentiell laden → `Promise.all()`
- `loadSeasons()` (Zeile ~1641): Gleicher Fix
- `loadMatchesForSeason()` (Zeile ~1397): Doppelter Fetch des gleichen Endpoints vermeiden

### 3.4 Bulk-Commit bei `bulk_add_teams`
**Datei:** `backend/app/api.py` (Zeile ~351-384)
**Problem:** `db.commit()` in der Schleife bei jedem Team.
**Fix:** Alle Teams sammeln, einmal committen.

---

## Phase 4: Stabilität & Validierung

**Empfohlenes Model:** Sonnet — klar definierte Regeln

### 4.1 Season-Status-Validierung
**Datei:** `backend/app/api.py` (Zeile ~92)
**Fix:** Erlaubte Übergänge definieren:
```python
VALID_TRANSITIONS = {
    "planned": ["active"],
    "active": ["archived"],
    "archived": []  # kein Zurück
}
```
Auch prüfen: Keine Teams/Matches/Schedules für `archived` Saisons änderbar.

### 4.2 Delete-Season-Cascade vervollständigen
**Datei:** `backend/app/api.py` (Zeile ~118-136)
**Fix:** `KOBracket`-Rows ebenfalls löschen (werden aktuell vergessen).

### 4.3 Untyped Dict-Bodies durch Pydantic-Schemas ersetzen
**Datei:** `backend/app/api.py`
**Betroffene Endpoints:**
- `PATCH /ko-matches/{id}` (Zeile ~2373): `update: dict` → Schema
- `POST /seasons/{id}/ko-brackets/create-empty` (Zeile ~2662): `body: dict` → Schema
- `PATCH /ko-matches/{id}/set-team` (Zeile ~2747): `body: dict` → Schema
- `PATCH /ko-matches/{id}/set-bye` (Zeile ~2802): `body: dict` → Schema

### 4.4 OAuth-State Memory-Leak
**Datei:** `backend/app/api.py` (Zeile ~1984)
**Fix:** TTL hinzufügen — States nach 10 Minuten automatisch löschen (z.B. mit `cachetools.TTLCache`).

---

## Phase 5: Wartbarkeit — Backend aufteilen

**Empfohlenes Model:** Opus — Architektur-Entscheidungen, viele Dateien gleichzeitig

### 5.1 `api.py` in FastAPI-Router aufteilen
**Zielstruktur:**
```
backend/app/
├── main.py              # App-Init, Router-Registration
├── routers/
│   ├── auth.py          # Login, JWT, Me
│   ├── seasons.py       # CRUD Saisons + Gruppen
│   ├── teams.py         # Team-Management, Search
│   ├── matches.py       # Gruppenphase, Standings, Matchdays
│   ├── ko.py            # KO-Bracket (nur neues 3-Bracket-System)
│   ├── news.py          # News CRUD
│   ├── users.py         # Discord/User-Profile, Participation
│   └── uploads.py       # Crest-Upload
├── services/
│   ├── standings.py     # Tabellen-Berechnung (aus matches.py extrahiert)
│   ├── all_time.py      # Ewige Tabelle (optimierte Queries)
│   └── user_response.py # UserProfileResponse-Builder (aktuell 10x copy-pasted)
├── models.py
├── schemas.py
├── auth.py
└── db.py
```

### 5.2 UserProfileResponse-Helper extrahieren
**Problem:** Identischer Response-Bau an ~10 Stellen copy-pasted.
**Fix:** Eine `build_user_response(user, db)` Funktion in `services/user_response.py`.

---

## Phase 6: Wartbarkeit — Frontend aufteilen

**Empfohlenes Model:** Opus — Refactoring über viele Dateien mit Abhängigkeiten

### 6.1 JavaScript modularisieren
**Zielstruktur:**
```
frontend/
├── admin.html           # Nur HTML + CSS
├── js/
│   ├── config.js        # API-URL (existiert bereits)
│   ├── api.js           # Einheitlicher fetchAPI()-Wrapper (einziges Pattern)
│   ├── auth.js          # Login/Logout/Token
│   ├── admin/
│   │   ├── dashboard.js
│   │   ├── anmeldungen.js
│   │   ├── ergebnisse.js
│   │   ├── ko-phase.js
│   │   ├── teams.js
│   │   ├── saisons.js
│   │   ├── news.js
│   │   └── setup.js
│   └── utils.js         # escapeHtml, Debounce, etc.
```

### 6.2 API-Call-Pattern vereinheitlichen
Alle drei bestehenden Patterns (`fetch()`, `authFetch()`, `fetchAPI()`) durch ein einziges `fetchAPI()` ersetzen das:
- Auth-Header automatisch setzt
- JSON parsed
- Fehler einheitlich behandelt (Toast/Alert)
- 401 → automatisch Logout

### 6.3 Fehlerbehandlung standardisieren
Aktuell ignorieren viele fetch-Calls Fehler komplett. Einheitliches Pattern:
```javascript
try {
    const data = await fetchAPI('/endpoint');
    // Verarbeitung
} catch (err) {
    showError(err.message);
}
```

---

## Verifizierung

Nach jeder Phase:
1. Backend starten: `cd backend && uvicorn app.main:app --reload`
2. Frontend öffnen: `http://localhost:5500/admin.html`
3. Kompletten Admin-Workflow testen:
   - Login → Dashboard lädt
   - Saison anlegen → Teams hinzufügen → Spielplan generieren
   - Ergebnisse eintragen → Tabelle prüfen
   - KO-Bracket generieren → KO-Ergebnis eintragen
   - News erstellen/bearbeiten/löschen
   - Anmeldungen-Tab funktioniert
4. Tests ausführen: `cd backend && python -m pytest tests/`
5. Bot-Kommunikation testen (falls API-Key-Auth hinzugefügt)

---

## Reihenfolge & Aufwand

| Phase | Priorität | Geschätzter Aufwand | Model |
|-------|-----------|-------------------|-------|
| 1. Sicherheit | Kritisch | Klein | Sonnet |
| 2. Dead Code | Hoch | Klein | Sonnet |
| 3. Performance | Hoch | Mittel | Opus |
| 4. Validierung | Mittel | Mittel | Sonnet |
| 5. Backend-Split | Niedrig | Groß | Opus |
| 6. Frontend-Split | Niedrig | Groß | Opus |

**Empfehlung:** Phasen 1-4 zuerst umsetzen (jeweils als eigene Session). Phasen 5-6 sind größere Refactorings die bei Bedarf angegangen werden können.
