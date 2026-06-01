# Nachzügler-Gruppenzuweisung — Design

**Datum:** 2026-06-02
**Status:** Approved (Brainstorming)

## Ziel

Solange in einer Saison **noch kein Spieltag gespielt** wurde, soll der Admin
nachträglich Anmeldungen ("Nachzügler") manuell einer **unvollständigen Gruppe**
(< 4 Teams) zuweisen können. Der Spielplan der betroffenen Gruppe passt sich
dabei automatisch an (Round-Robin wird neu generiert).

Hintergrund: `/dabei ja` im Discord setzt nur `Team.participating_next = True`
(globales Pool-Flag), schreibt aber nichts in eine bereits ausgeloste Saison.
Nachzügler landen damit im Anmelde-Pool, aber nicht in den laufenden Gruppen.
Dieses Feature schließt die Lücke für den Zeitraum vor dem ersten Spieltag.

## Entscheidungen (aus Brainstorming)

| Frage | Entscheidung |
|---|---|
| Sperr-Granularität | **Saisonweit** — sobald *irgendein* Match der Saison `status != "scheduled"` hat, ist die Zuweisung gesperrt. |
| Quelle des Nachzüglers | **Anmelde-Pool** — Teams mit `participating_next = True`, die noch nicht in der Saison sind. |
| Volle Gruppen | **Nur unvollständige** Gruppen (< 4) zuweisbar. Sind alle voll → kein Slot. 4er-Regel bleibt strikt. |
| UI-Ort | **Gruppen-/Saison-Ansicht** (Spielplan-View) — Per-Gruppe-Button. |
| Backend-Ansatz | **Dedizierter Endpoint** (Ansatz A), keine Wiederverwendung des reshuffelnden Sync-Endpoints. |
| Pool-Datenquelle Frontend | **(a)** bestehender `GET /api/teams?participating=true`, clientseitig gefiltert. |

## Architektur

### Backend — neuer Endpoint

`POST /api/seasons/{season_id}/groups/{group_id}/assign-latecomer`

- Auth: `Depends(get_current_user)` (JWT)
- Body: `{ "team_id": <int> }`
- Datei: `backend/app/routers/teams.py`
- Neues Schema: `AssignLatecomerPayload(team_id: int)` in `schemas.py`

**Ablauf (fail-fast):**

1. **Saison-Sperre (saisonweit):** Existiert in `season_id` ein Match mit
   `status != "scheduled"`? → `409` mit Detail `SAISON_GESPERRT`.
2. **Gruppe validieren:** `group_id` existiert in dieser Saison? → sonst `404`.
3. **Kapazität:** `count(SeasonTeam in group) >= 4` → `409` mit Detail `GRUPPE_VOLL`.
4. **Team validieren:** existiert, `participating_next is True`, und noch kein
   `SeasonTeam`-Eintrag in dieser Saison → sonst `400` (`TEAM_UNGUELTIG` bzw.
   `TEAM_BEREITS_IN_SAISON`).
5. **Zuweisen:** `SeasonTeam(season_id, team_id, group_id=group_id)` anlegen.
6. **Spielplan regenerieren (nur diese Gruppe):** alle `scheduled`-Matches der
   Gruppe löschen, dann `generate_round_robin(db, group_id, season_id, start_week=…)`.
7. **`season.participant_count` += 1.**
8. `db.commit()`, Response: aktualisierte Gruppe (Teams) + erzeugte Match-Anzahl.

**`start_week`-Ableitung:** Aus den vorhandenen Matches der Gruppe
`min(ingame_week)` (= Spieltag 1) verwenden, damit die Ingame-Wochen erhalten
bleiben. Gibt es keine Matches mit `ingame_week`, → `None` (wie Erstgenerierung
ohne Startwoche).

### Frontend — Spielplan-Ansicht

Datei: `frontend/js/admin/setup.js`, Funktion `loadScheduleForSeason()`.

Pro Gruppen-Card, unterhalb der Team-Chips:

- **Gruppe < 4 Teams UND Saison nicht gesperrt** → Zuweis-Bereich:
  `<select>` aus dem Anmelde-Pool + Button „Zuweisen". Bei Klick → POST auf den
  neuen Endpoint, danach `loadScheduleForSeason()` neu laden.
- **Gruppe voll (4 Teams)** → kein Zuweis-UI.
- **Saison gesperrt** (irgendein Match gespielt) → kein Zuweis-UI; optionaler
  einmaliger Hinweis oben: „Spieltag läuft bereits — Zuweisung gesperrt".

**Pool-Datenquelle (a):** `GET /api/teams?participating=true` laden, clientseitig
die Teams herausfiltern, die bereits einer Gruppe der Saison zugewiesen sind
(bekannt aus `groups-with-teams`). Kein zusätzlicher Endpoint nötig.

**Sperr-Status im Frontend:** abgeleitet aus den geladenen `groups-with-teams` —
existiert ein Match mit `status !== "scheduled"`, gilt die Saison als gesperrt.

## Tests

Backend-Tests (Stil wie `test_ko_e2e.py`):

1. **Happy path:** Saison, Gruppe mit 3 Teams, Pool-Team zuweisen → Team in
   Gruppe, Spielplan neu (4 Teams → 6 Matches / 3 Spieltage), `participant_count +1`.
2. **Sperre greift:** ein Match `played` → Zuweisung `409 SAISON_GESPERRT`,
   Gruppe unverändert.
3. **Gruppe voll:** 4 Teams → `409 GRUPPE_VOLL`.
4. **Ungültiges Team:** `participating_next = False` bzw. bereits in Saison → `400`.
5. **`start_week`-Erhalt:** Gruppe mit gesetzten `ingame_week` → neuer Plan
   beginnt bei derselben Startwoche.

## Edge Cases (vom Design abgedeckt)

- Andere Gruppen bleiben unangetastet (kein Reshuffle) — nur Zielgruppe wird neu geplant.
- Saisonweite Sperre garantiert: kein gespieltes Match in der Zielgruppe →
  Löschen der `scheduled`-Matches ist verlustfrei.
- Doppelklick/Race: serverseitige Re-Validierung von Sperre + Kapazität bei jedem Request.

## Außerhalb des Scopes (YAGNI)

- Teams zwischen Gruppen verschieben oder entfernen (nur *Hinzufügen*).
- Freie Team-Neuanlage beim Zuweisen (nur Anmelde-Pool).
- Automatisches Anlegen neuer Gruppen, wenn alle voll sind.
