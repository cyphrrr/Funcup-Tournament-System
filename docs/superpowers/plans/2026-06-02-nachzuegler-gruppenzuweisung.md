# Nachzügler-Gruppenzuweisung Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Solange in einer Saison noch kein Spieltag gespielt wurde, kann der Admin ein Team aus dem Anmelde-Pool nachträglich einer unvollständigen Gruppe (< 4) zuweisen; der Spielplan dieser Gruppe wird neu generiert.

**Architecture:** Neuer JWT-geschützter Endpoint `POST /api/seasons/{season_id}/groups/{group_id}/assign-latecomer` in `backend/app/routers/teams.py`. Die Kernlogik liegt in einer testbaren Modulfunktion `_assign_latecomer(db, season_id, group_id, team_id)`, die `HTTPException` wirft und gegen eine In-Memory-DB direkt testbar ist (Stil `test_ko_e2e.py`, kein laufender Server). Nur die Zielgruppe wird via `generate_round_robin` neu geplant; die Ingame-Startwoche bleibt erhalten. Frontend ergänzt pro unvollständiger Gruppe einen Auswahl-Selektor in `loadScheduleForSeason()`.

**Tech Stack:** FastAPI, SQLAlchemy, SQLite (In-Memory für Tests), Vanilla JS. Tests laufen via `docker exec biw-backend-dev sh -c 'cd /app && python tests/<file>.py'` (kein pytest installiert — Standalone-`__main__`-Runner).

---

## Spec

Quelle: `docs/superpowers/specs/2026-06-02-nachzuegler-gruppenzuweisung-design.md`

Entscheidungen (verbindlich):
- **Sperre saisonweit:** Existiert *irgendein* Match der Saison mit `status != "scheduled"` → `409 SAISON_GESPERRT`.
- **Quelle:** Anmelde-Pool — `Team.participating_next == True`, noch kein `SeasonTeam` in dieser Saison.
- **Kapazität:** Nur Gruppen mit `< 4` Teams; sonst `409 GRUPPE_VOLL`.
- **Regeneration:** Nur Zielgruppe; `start_week = min(ingame_week)` der bestehenden Matches, sonst `None`.
- **YAGNI:** Kein Verschieben/Entfernen, keine Neuanlage, kein Auto-Anlegen neuer Gruppen.

## File Structure

| Datei | Verantwortung | Änderung |
|---|---|---|
| `backend/app/schemas.py` | Request-Body-Schema | Modify: neues `AssignLatecomerPayload` |
| `backend/app/routers/teams.py` | Endpoint + Kernlogik | Modify: Import `generate_round_robin`, Helper `_assign_latecomer`, Route |
| `backend/tests/test_assign_latecomer.py` | Backend-E2E-Tests | Create: Standalone-Runner mit 6 Tests |
| `frontend/js/admin/setup.js` | Spielplan-UI | Modify: Pool-Laden + Per-Gruppe-Selektor in `loadScheduleForSeason()`, neue `assignLatecomer()` |

### Verifizierte Fakten (aus Codebase)

- `generate_round_robin(db, group_id, season_id, start_week=None)` — `backend/app/routers/matches.py:254`. Legt `scheduled`-Matches an, **committet nicht** (Caller committet). Gibt `{"group_id", "matches_created", "matchdays"}` zurück. `ingame_week = start_week + matchday - 1` falls `start_week` gesetzt, sonst `None`.
- Modelle (`backend/app/models.py`): `Season.participant_count` (Int, nullable=False), `Team.participating_next` (Bool, default False), `SeasonTeam(season_id, team_id, group_id)`, `Match(season_id, group_id, home_team_id, away_team_id, status, matchday, ingame_week)`, `Group(season_id, name, sort_order)`.
- `teams.py` Imports vorhanden: `from .. import models, schemas`, `from ..db import get_db`, `from ..auth import get_current_user`, `from fastapi import APIRouter, Depends, HTTPException`. Auth-Pattern: `_: str = Depends(get_current_user)`.
- `groups-with-teams` (`seasons.py:118`) Response-Form: Liste von `{"group": {"id", "name"}, "teams": [{"id","name"}], "matches": [{... "status" ...}]}`. **Achtung:** id/name liegen unter `g.group`, `teams`/`matches` flach. Das bestehende `loadScheduleForSeason` liest fälschlich `g.name` (→ "Gruppe undefined"); wird in Task 5 mit korrigiert.
- Pool-Endpoint: `GET /api/teams?participating=true` (public, kein Auth) gibt Team-Liste; Items haben `id`, `name`.
- Test-Runner-Konvention: kein pytest. Datei definiert `def test_*()`, am Ende `if __name__ == "__main__":` mit Tests-Liste, fängt `AssertionError`/`Exception`, `sys.exit(1)` bei Fehlern. Lauf: `docker exec biw-backend-dev sh -c 'cd /app && python tests/test_assign_latecomer.py'`.

---

## Task 1: Request-Schema `AssignLatecomerPayload`

**Files:**
- Modify: `backend/app/schemas.py` (nach `class BulkTeamCreate`, ~Zeile 66)

- [ ] **Step 1: Schema hinzufügen**

In `backend/app/schemas.py`, direkt nach der `BulkTeamCreate`-Klasse einfügen:

```python
class AssignLatecomerPayload(BaseModel):
    team_id: int
```

- [ ] **Step 2: Import-Sanity prüfen**

Run: `docker exec biw-backend-dev sh -c 'cd /app && python -c "from app.schemas import AssignLatecomerPayload; print(AssignLatecomerPayload(team_id=5).team_id)"'`
Expected: `5`

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas.py
git commit -m "feat: AssignLatecomerPayload schema für Nachzügler-Zuweisung"
```

---

## Task 2: Kernlogik-Helper `_assign_latecomer` (TDD)

Die Logik wird als testbare Modulfunktion implementiert. Tests in Task 3/4 treiben sie. Reihenfolge hier: erst Test-Gerüst + erster (Happy-Path-)Test schreiben, fehlschlagen lassen, dann Helper implementieren.

**Files:**
- Create: `backend/tests/test_assign_latecomer.py`
- Modify: `backend/app/routers/teams.py` (Import oben; Helper + Route am Dateiende)

- [ ] **Step 1: Test-Datei mit Helpers + erstem Test anlegen (failing)**

Create `backend/tests/test_assign_latecomer.py`:

```python
"""
End-to-End Tests für Nachzügler-Gruppenzuweisung.

Funktioniert gegen In-Memory SQLite DB (kein laufender Server nötig).
Testet die Kernlogik _assign_latecomer direkt (wirft HTTPException).

Tests:
1. test_happy_path: Gruppe mit 3 Teams + Pool-Team → 4 Teams, 6 Matches, participant_count +1
2. test_saison_gesperrt: ein Match 'played' → 409, Gruppe unverändert
3. test_gruppe_voll: 4 Teams → 409 GRUPPE_VOLL
4. test_team_nicht_im_pool: participating_next=False → 400
5. test_team_bereits_in_saison: Team schon SeasonTeam → 400
6. test_start_week_erhalt: bestehende ingame_week=39 → neuer Plan startet bei 39
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app import models
from app.routers.teams import _assign_latecomer
from app.routers.matches import generate_round_robin


def create_test_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def setup_season_with_group(db, teams_in_group: int, generate_schedule: bool = True,
                            start_week: int = 39, pool_team: bool = True):
    """Erstellt Saison mit einer Gruppe (teams_in_group Teams) + optional ein Pool-Team.

    Rückgabe: (season, group, pool_team_or_None)
    """
    season = models.Season(name="Test Saison", participant_count=teams_in_group, status="active")
    db.add(season)
    db.flush()

    group = models.Group(season_id=season.id, name="A", sort_order=0)
    db.add(group)
    db.flush()

    for i in range(teams_in_group):
        team = models.Team(name=f"Team_{i + 1}", participating_next=True)
        db.add(team)
        db.flush()
        db.add(models.SeasonTeam(season_id=season.id, team_id=team.id, group_id=group.id))
    db.flush()

    if generate_schedule and teams_in_group >= 2:
        generate_round_robin(db, group.id, season.id, start_week=start_week)
        db.flush()

    pool = None
    if pool_team:
        pool = models.Team(name="Nachzuegler", participating_next=True)
        db.add(pool)
        db.flush()

    db.commit()
    return season, group, pool


def test_happy_path():
    db = create_test_db()
    season, group, pool = setup_season_with_group(db, teams_in_group=3)

    result = _assign_latecomer(db, season.id, group.id, pool.id)

    # Pool-Team ist jetzt in der Gruppe
    sts = db.query(models.SeasonTeam).filter(models.SeasonTeam.group_id == group.id).all()
    assert len(sts) == 4, f"erwartet 4 Teams, ist {len(sts)}"
    assert pool.id in [st.team_id for st in sts]

    # Spielplan neu: 4 Teams Round-Robin = 6 Matches, 3 Spieltage
    matches = db.query(models.Match).filter(models.Match.group_id == group.id).all()
    assert len(matches) == 6, f"erwartet 6 Matches, ist {len(matches)}"
    assert result["matches_created"] == 6

    # participant_count erhöht
    db.refresh(season)
    assert season.participant_count == 4, f"erwartet 4, ist {season.participant_count}"


if __name__ == "__main__":
    print("=" * 70)
    print("NACHZÜGLER-GRUPPENZUWEISUNG — END-TO-END TESTS")
    print("=" * 70)

    tests = [
        ("test_happy_path", test_happy_path),
    ]

    failed = []
    for test_name, test_fn in tests:
        try:
            test_fn()
            print(f"✓ {test_name} bestanden")
        except AssertionError as e:
            print(f"✗ {test_name}: {e}")
            failed.append(test_name)
        except Exception as e:
            import traceback
            print(f"✗ {test_name}: EXCEPTION")
            traceback.print_exc()
            failed.append(test_name)

    print("\n" + "=" * 70)
    if failed:
        print(f"✗ {len(failed)}/{len(tests)} Test(s) fehlgeschlagen:")
        for name in failed:
            print(f"  - {name}")
        sys.exit(1)
    print(f"✓ Alle {len(tests)} Tests bestanden!")
    print("=" * 70)
```

- [ ] **Step 2: Test laufen lassen — muss fehlschlagen (ImportError)**

Run: `docker exec biw-backend-dev sh -c 'cd /app && python tests/test_assign_latecomer.py'`
Expected: FAIL — `ImportError: cannot import name '_assign_latecomer' from 'app.routers.teams'`

- [ ] **Step 3: Import von `generate_round_robin` in teams.py ergänzen**

In `backend/app/routers/teams.py`, nach den bestehenden Imports (nach `from ..auth import get_current_user`) einfügen:

```python
from .matches import generate_round_robin
```

(Kein Zirkelimport: `matches.py` importiert `teams.py` nicht.)

- [ ] **Step 4: Helper `_assign_latecomer` implementieren**

Am **Ende** von `backend/app/routers/teams.py` anfügen:

```python
def _assign_latecomer(db: Session, season_id: int, group_id: int, team_id: int):
    """Weist ein Pool-Team einer unvollständigen Gruppe zu und regeneriert
    den Spielplan dieser Gruppe. Wirft HTTPException bei Verstößen.
    Saisonweite Sperre: kein Match der Saison darf bereits gespielt sein.
    """
    # 1. Saison existiert + saisonweite Sperre
    season = db.get(models.Season, season_id)
    if not season:
        raise HTTPException(status_code=404, detail="SAISON_NICHT_GEFUNDEN")
    locked = db.query(models.Match).filter(
        models.Match.season_id == season_id,
        models.Match.status != "scheduled",
    ).first()
    if locked:
        raise HTTPException(status_code=409, detail="SAISON_GESPERRT")

    # 2. Gruppe gehört zur Saison
    group = db.query(models.Group).filter(
        models.Group.id == group_id,
        models.Group.season_id == season_id,
    ).first()
    if not group:
        raise HTTPException(status_code=404, detail="GRUPPE_NICHT_GEFUNDEN")

    # 3. Kapazität (< 4)
    count = db.query(models.SeasonTeam).filter(
        models.SeasonTeam.group_id == group_id
    ).count()
    if count >= 4:
        raise HTTPException(status_code=409, detail="GRUPPE_VOLL")

    # 4. Team aus Anmelde-Pool, noch nicht in Saison
    team = db.get(models.Team, team_id)
    if not team or not team.participating_next:
        raise HTTPException(status_code=400, detail="TEAM_UNGUELTIG")
    existing_st = db.query(models.SeasonTeam).filter_by(
        season_id=season_id, team_id=team_id
    ).first()
    if existing_st:
        raise HTTPException(status_code=400, detail="TEAM_BEREITS_IN_SAISON")

    # 5. Zuweisen
    db.add(models.SeasonTeam(season_id=season_id, team_id=team_id, group_id=group_id))
    db.flush()

    # 6. Spielplan nur dieser Gruppe regenerieren, Ingame-Startwoche erhalten
    existing_matches = db.query(models.Match).filter(
        models.Match.group_id == group_id
    ).all()
    ingame_weeks = [m.ingame_week for m in existing_matches if m.ingame_week is not None]
    start_week = min(ingame_weeks) if ingame_weeks else None
    db.query(models.Match).filter(
        models.Match.group_id == group_id
    ).delete(synchronize_session=False)
    result = generate_round_robin(db, group_id, season_id, start_week=start_week)

    # 7. participant_count
    season.participant_count = (season.participant_count or 0) + 1

    db.commit()

    teams = (
        db.query(models.Team)
        .join(models.SeasonTeam, models.SeasonTeam.team_id == models.Team.id)
        .filter(models.SeasonTeam.group_id == group_id)
        .all()
    )
    return {
        "group_id": group_id,
        "teams": [{"id": t.id, "name": t.name} for t in teams],
        "matches_created": result["matches_created"],
    }
```

- [ ] **Step 5: Test laufen lassen — muss bestehen**

Run: `docker exec biw-backend-dev sh -c 'cd /app && python tests/test_assign_latecomer.py'`
Expected: `✓ test_happy_path bestanden` und `✓ Alle 1 Tests bestanden!`

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/teams.py backend/tests/test_assign_latecomer.py
git commit -m "feat: _assign_latecomer Kernlogik + Happy-Path-Test"
```

---

## Task 3: Route + restliche Tests (Sperre, Kapazität, Team-Validierung, start_week)

**Files:**
- Modify: `backend/app/routers/teams.py` (Route nach dem Helper)
- Modify: `backend/tests/test_assign_latecomer.py` (5 weitere Tests + Runner-Liste)

- [ ] **Step 1: Weitere Tests ergänzen (failing für noch nicht geprüfte Pfade)**

In `backend/tests/test_assign_latecomer.py`, **vor** dem `if __name__ == "__main__":`-Block einfügen:

```python
def test_saison_gesperrt():
    db = create_test_db()
    season, group, pool = setup_season_with_group(db, teams_in_group=3)
    # Ein Match auf 'played' setzen → Saison gesperrt
    m = db.query(models.Match).filter(models.Match.group_id == group.id).first()
    m.status = "played"
    db.commit()

    try:
        _assign_latecomer(db, season.id, group.id, pool.id)
        assert False, "erwartete HTTPException SAISON_GESPERRT"
    except HTTPException as e:
        assert e.status_code == 409, f"erwartet 409, ist {e.status_code}"
        assert e.detail == "SAISON_GESPERRT", f"detail={e.detail}"

    # Gruppe unverändert (3 Teams)
    count = db.query(models.SeasonTeam).filter(models.SeasonTeam.group_id == group.id).count()
    assert count == 3, f"erwartet 3 Teams unverändert, ist {count}"


def test_gruppe_voll():
    db = create_test_db()
    season, group, pool = setup_season_with_group(db, teams_in_group=4)

    try:
        _assign_latecomer(db, season.id, group.id, pool.id)
        assert False, "erwartete HTTPException GRUPPE_VOLL"
    except HTTPException as e:
        assert e.status_code == 409, f"erwartet 409, ist {e.status_code}"
        assert e.detail == "GRUPPE_VOLL", f"detail={e.detail}"


def test_team_nicht_im_pool():
    db = create_test_db()
    season, group, pool = setup_season_with_group(db, teams_in_group=3, pool_team=False)
    # Team das NICHT im Pool ist (participating_next=False)
    fremd = models.Team(name="Fremd", participating_next=False)
    db.add(fremd)
    db.commit()

    try:
        _assign_latecomer(db, season.id, group.id, fremd.id)
        assert False, "erwartete HTTPException TEAM_UNGUELTIG"
    except HTTPException as e:
        assert e.status_code == 400, f"erwartet 400, ist {e.status_code}"
        assert e.detail == "TEAM_UNGUELTIG", f"detail={e.detail}"


def test_team_bereits_in_saison():
    db = create_test_db()
    season, group, pool = setup_season_with_group(db, teams_in_group=3)
    # Bereits zugewiesenes Team erneut zuweisen wollen
    bestehendes_st = db.query(models.SeasonTeam).filter(
        models.SeasonTeam.group_id == group.id
    ).first()

    try:
        _assign_latecomer(db, season.id, group.id, bestehendes_st.team_id)
        assert False, "erwartete HTTPException TEAM_BEREITS_IN_SAISON"
    except HTTPException as e:
        assert e.status_code == 400, f"erwartet 400, ist {e.status_code}"
        assert e.detail == "TEAM_BEREITS_IN_SAISON", f"detail={e.detail}"


def test_start_week_erhalt():
    db = create_test_db()
    season, group, pool = setup_season_with_group(db, teams_in_group=3, start_week=39)

    _assign_latecomer(db, season.id, group.id, pool.id)

    matches = db.query(models.Match).filter(models.Match.group_id == group.id).all()
    weeks = [m.ingame_week for m in matches]
    assert min(weeks) == 39, f"erwartet Startwoche 39, ist {min(weeks)}"
    # 4 Teams → 3 Spieltage → Wochen 39,40,41
    assert max(weeks) == 41, f"erwartet Endwoche 41, ist {max(weeks)}"
```

- [ ] **Step 2: Runner-Liste erweitern**

In `backend/tests/test_assign_latecomer.py` die `tests`-Liste im `__main__`-Block ersetzen durch:

```python
    tests = [
        ("test_happy_path", test_happy_path),
        ("test_saison_gesperrt", test_saison_gesperrt),
        ("test_gruppe_voll", test_gruppe_voll),
        ("test_team_nicht_im_pool", test_team_nicht_im_pool),
        ("test_team_bereits_in_saison", test_team_bereits_in_saison),
        ("test_start_week_erhalt", test_start_week_erhalt),
    ]
```

- [ ] **Step 3: Tests laufen lassen — alle 6 grün (Helper deckt diese Pfade bereits ab)**

Run: `docker exec biw-backend-dev sh -c 'cd /app && python tests/test_assign_latecomer.py'`
Expected: `✓ Alle 6 Tests bestanden!`

(Die Logik aus Task 2 deckt diese Pfade bereits ab — die Tests verifizieren das Verhalten umfassend.)

- [ ] **Step 4: Route registrieren**

Am **Ende** von `backend/app/routers/teams.py`, nach dem Helper, anfügen:

```python
@router.post("/seasons/{season_id}/groups/{group_id}/assign-latecomer")
def assign_latecomer(
    season_id: int,
    group_id: int,
    payload: schemas.AssignLatecomerPayload,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    """Weist ein Pool-Team (participating_next) einer unvollständigen Gruppe zu,
    solange die Saison noch nicht gespielt wurde. Regeneriert den Gruppen-Spielplan.
    """
    return _assign_latecomer(db, season_id, group_id, payload.team_id)
```

- [ ] **Step 5: Route-Registrierung verifizieren (Backend lädt, Route existiert)**

Run: `docker exec biw-backend-dev sh -c 'cd /app && python -c "from app.main import app; print([r.path for r in app.routes if \"assign-latecomer\" in r.path])"'`
Expected: `['/api/seasons/{season_id}/groups/{group_id}/assign-latecomer']`
(Falls Pfad ohne `/api`-Präfix erscheint, ist das je nach Router-Mount-Konfiguration ok — Hauptsache der Pfad mit `assign-latecomer` taucht auf.)

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/teams.py backend/tests/test_assign_latecomer.py
git commit -m "feat: assign-latecomer Endpoint + vollständige Backend-Tests"
```

---

## Task 4: Smoke-Test gegen laufenden Container (optional, manuell)

Verifiziert den Endpoint end-to-end über HTTP. Erfordert gültigen JWT.

**Files:** keine (manuelle Verifikation)

- [ ] **Step 1: JWT holen**

Run (Credentials aus `backend/.env`):
```bash
curl -s -X POST http://localhost:8000/api/login -H 'Content-Type: application/json' \
  -d '{"username":"<ADMIN_USER>","password":"<ADMIN_PW>"}'
```
Expected: JSON mit `access_token`.

- [ ] **Step 2: Zuweisung gegen eine reale unvollständige Gruppe testen**

Run (Platzhalter ersetzen):
```bash
curl -s -X POST "http://localhost:8000/api/seasons/<SID>/groups/<GID>/assign-latecomer" \
  -H 'Content-Type: application/json' -H "Authorization: Bearer <TOKEN>" \
  -d '{"team_id": <POOL_TEAM_ID>}'
```
Expected: `{"group_id": <GID>, "teams": [...4 Teams...], "matches_created": 6}` — oder ein erwarteter Fehler-`detail` (z.B. `SAISON_GESPERRT`), wenn die Saison schon läuft.

---

## Task 5: Frontend — Per-Gruppe-Selektor in `loadScheduleForSeason()`

**Files:**
- Modify: `frontend/js/admin/setup.js` — `loadScheduleForSeason()` (ab Zeile 586) + neue Funktion `assignLatecomer()`

- [ ] **Step 1: Pool laden + Sperr-/Verfügbarkeits-Status berechnen**

In `frontend/js/admin/setup.js`, in `loadScheduleForSeason()` **nach** `const groups = await res.json();` und der `if (!groups.length)`-Prüfung, **vor** `container.innerHTML = groups.map(...)`, einfügen:

```javascript
    // Anmelde-Pool laden (public Endpoint) und bereits zugewiesene Teams herausfiltern
    let availablePool = [];
    try {
      const poolRes = await fetch(`${API_URL}/api/teams?participating=true`);
      const pool = await poolRes.json();
      const assignedIds = new Set(groups.flatMap(g => (g.teams || []).map(t => t.id)));
      availablePool = pool.filter(t => !assignedIds.has(t.id));
    } catch (_) { availablePool = []; }

    // Saisonweite Sperre: irgendein Match nicht mehr 'scheduled'
    const seasonLocked = groups.some(g => (g.matches || []).some(m => m.status !== 'scheduled'));
```

- [ ] **Step 2: Card-Rendering anpassen — korrektes Gruppen-Objekt + Zuweis-UI**

In `loadScheduleForSeason()` den `container.innerHTML = groups.map(g => { ... })`-Block ersetzen. Die bestehende Map liest fälschlich `g.name` (id/name liegen unter `g.group`). Neue Version:

```javascript
    container.innerHTML = groups.map(g => {
      const grp = g.group || g;            // {id, name}
      const teams = g.teams || [];
      const matches = g.matches || [];
      const matchRows = matches.length
        ? matches.map(m => `
            <tr>
              <td>${m.matchday || '-'}</td>
              <td style="text-align:right">${m.home_team_name || m.home_team_id}</td>
              <td style="text-align:center;font-weight:600;color:var(--primary)">
                ${m.home_goals != null ? `${m.home_goals}:${m.away_goals}` : '–:–'}
              </td>
              <td>${m.away_team_name || m.away_team_id}</td>
              <td><span class="match-status ${m.status}">${m.status === 'played' ? '✅' : '🕐'}</span></td>
            </tr>`).join('')
        : '<tr><td colspan="5" style="color:var(--text-muted)">Kein Spielplan vorhanden</td></tr>';

      // Zuweis-UI nur bei unvollständiger Gruppe, ungesperrter Saison und verfügbarem Pool
      let assignUI = '';
      if (!seasonLocked && teams.length < 4 && availablePool.length) {
        const selId = `latecomer-select-${grp.id}`;
        const options = availablePool
          .map(t => `<option value="${t.id}">${t.name}</option>`)
          .join('');
        assignUI = `
          <div style="margin-top:.75rem;display:flex;gap:.5rem;align-items:center;flex-wrap:wrap">
            <select id="${selId}" style="padding:.3rem .5rem;border-radius:4px">
              <option value="">Nachzügler wählen…</option>
              ${options}
            </select>
            <button class="btn" onclick="assignLatecomer('${grp.id}', '${selId}')">Zuweisen</button>
          </div>`;
      }

      return `
        <div class="card">
          <h2>Gruppe ${grp.name}</h2>
          <div style="margin-bottom:.75rem;display:flex;gap:.5rem;flex-wrap:wrap">
            ${teams.map(t => `<span style="background:var(--bg-elevated);padding:.2rem .6rem;border-radius:4px;font-size:.85rem">${t.name}</span>`).join('')}
          </div>
          <table>
            <thead><tr><th>ST</th><th style="text-align:right">Heim</th><th style="text-align:center">Ergebnis</th><th>Gast</th><th>Status</th></tr></thead>
            <tbody>${matchRows}</tbody>
          </table>
          ${assignUI}
        </div>`;
    }).join('');
```

- [ ] **Step 3: Optionalen Sperr-Hinweis oben einfügen**

In `loadScheduleForSeason()`, direkt **nach** der `container.innerHTML = groups.map(...).join('');`-Zuweisung anfügen:

```javascript
    if (seasonLocked) {
      container.insertAdjacentHTML('afterbegin',
        '<div style="background:var(--bg-elevated);color:var(--text-muted);padding:.5rem .75rem;border-radius:4px;margin-bottom:.75rem;font-size:.85rem">🔒 Spieltag läuft bereits — Nachzügler-Zuweisung gesperrt.</div>');
    }
```

- [ ] **Step 4: `assignLatecomer()`-Funktion hinzufügen**

In `frontend/js/admin/setup.js`, direkt **nach** der `generateScheduleForSeason()`-Funktion (vor dem `document.addEventListener('keydown', ...)`-Block) einfügen:

```javascript
async function assignLatecomer(groupId, selectId) {
  const seasonId = document.getElementById('schedule-season-select').value;
  const sel = document.getElementById(selectId);
  const teamId = sel ? sel.value : '';
  if (!teamId) { toast('Bitte ein Team wählen', 'error'); return; }

  try {
    const res = await authFetch(`${API_URL}/api/seasons/${seasonId}/groups/${groupId}/assign-latecomer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ team_id: parseInt(teamId, 10) }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      toast(`Fehler: ${err.detail || res.status}`, 'error');
      return;
    }
    toast('Team zugewiesen, Spielplan neu generiert');
    loadScheduleForSeason();
  } catch (e) {
    toast(`Fehler: ${e.message}`, 'error');
  }
}
```

- [ ] **Step 5: Manuelle Verifikation im Browser**

1. Admin-UI öffnen (Frontend-Container `biw-frontend-dev`), einloggen.
2. Spielplan-Tab → Saison wählen, in der noch kein Match gespielt ist und mind. eine Gruppe < 4 Teams hat.
3. Erwartung: Unter der betroffenen Gruppe erscheint „Nachzügler wählen…“ + „Zuweisen". Volle Gruppen (4) zeigen keinen Selektor.
4. Team wählen → „Zuweisen" → Toast „Team zugewiesen…", Liste lädt neu, Gruppe hat 4 Teams + neuen 6-Match-Spielplan.
5. In einer Saison mit bereits gespieltem Match: oben steht der 🔒-Hinweis, kein Selektor.

Falls Schritt-3/5-Verhalten abweicht: Browser-Devtools-Konsole/Network prüfen (Pfad, 401/409).

- [ ] **Step 6: Commit**

```bash
git add frontend/js/admin/setup.js
git commit -m "feat: Nachzügler-Selektor pro Gruppe in Spielplan-Ansicht"
```

---

## Self-Review (durchgeführt)

**Spec-Coverage:**
- Saisonweite Sperre → Task 2 (Helper Schritt 1 der Logik) + Task 3 `test_saison_gesperrt` + Frontend `seasonLocked` (Task 5).
- Quelle Anmelde-Pool → Helper Team-Validierung + Frontend `participating=true`-Filter.
- Nur unvollständige Gruppen → Helper Kapazitäts-Check + Frontend `teams.length < 4`.
- Regeneration nur Zielgruppe + start_week-Erhalt → Helper Schritt 6 + Task 3 `test_start_week_erhalt`.
- participant_count +1 → Helper Schritt 7 + `test_happy_path`.
- UI-Ort Spielplan-View, Per-Gruppe-Button → Task 5.
- Pool-Datenquelle (a) clientseitig → Task 5 Step 1.
- YAGNI (kein Move/Remove/Neuanlage) → nicht implementiert. ✓

**Placeholder-Scan:** Keine TBD/TODO; jeder Code-Step enthält vollständigen Code. ✓

**Typ-Konsistenz:** `_assign_latecomer(db, season_id, group_id, team_id)` identisch in Helper, Route, Tests. Fehler-`detail`-Konstanten (`SAISON_GESPERRT`, `GRUPPE_VOLL`, `TEAM_UNGUELTIG`, `TEAM_BEREITS_IN_SAISON`) in Helper und Tests deckungsgleich. Frontend `assignLatecomer(groupId, selectId)` Signatur passt zum `onclick`-Aufruf. ✓

---

## Hinweise für den Ausführenden

- **Kein pytest** im Container — Tests sind Standalone-Skripte (`python tests/<file>.py`), Exit-Code 1 bei Fehler.
- **Kein venv/pip** — Backend läuft im Container `biw-backend-dev` (Python 3.13). Code ist gemountet; Änderungen an `.py` greifen nach Auto-Reload bzw. beim Neuimport im Test-Skript sofort.
- **Version/Changelog:** Nach Abschluss optional `docs/CHANGELOG.md` ergänzen und via `./scripts/release.sh patch beta` versionieren (separate Entscheidung mit dem User, nicht Teil der Tasks).
