# Wappen-Konsolidierung: eine Quelle statt logo_url + crest_url

**Datum:** 2026-07-15
**Status:** Design (approved)

## Problem

Ein Team-Wappen wird an **zwei** Stellen gespeichert, mit unterschiedlicher
Priorität und getrennten Lesepfaden:

- `Team.logo_url` — Admin-Feld; gelesen von Tabellen (Basis), Profil, KO, Paarungen.
- `UserProfile.crest_url` — Discord-Owner-Upload; **überschreibt** in
  `/teams/crests` die `logo_url`, wird aber nur dort gelesen.

Folgen: Ändert der Admin `logo_url`, bleibt in den Tabellen das `crest_url`-Wappen
sichtbar. Ein falscher Upload ist verwirrend zu korrigieren, weil zwei Felder
dieselbe Sache meinen. „Historisch gewachsen": `logo_url` war zuerst da,
`crest_url` kam mit dem Self-Service-Upload dazu und wurde als Override
draufgesetzt, ohne Vereinheitlichung.

## Ziel

**`Team.logo_url` ist die einzige Quelle für das Team-Wappen.** Ob per URL
eingegeben oder per Datei hochgeladen — beides landet in `Team.logo_url`, und
**alle** Funktionen lesen von dort. `UserProfile.crest_url` als Wappen-Override
entfällt.

Owner **und** Admin dürfen das Wappen setzen (gleiches Feld, last-writer-wins).

## Nicht-Ziele

- Kein Entfernen der Spalte `UserProfile.crest_url` in diesem Schritt (kein
  destruktives Drop; bleibt nach Migration leer/dormant).
- Keine Änderung an KO-/Paarungs-/Profil-Lesepfaden (nutzen bereits `logo_url`).

## Änderungen Backend

### 1. `/teams/crests` — Override entfernen
`get_team_crests` liefert nur noch `Team.logo_url` (der zweite Block über
`UserProfile.crest_url` fällt weg).

### 2. Einmal-Datenmigration (idempotent, beim Start)
In `run_auto_migrations`/Startup nach `create_all`:
- Für jede **aktive** `UserProfile` mit `crest_url` und `team_id`:
  `team.logo_url = profile.crest_url` (crest_url gewinnt aktuell → aktueller
  Anzeigezustand bleibt erhalten).
- Danach **alle** `crest_url` auf `NULL` setzen (Feld wird als Wappen-Quelle
  stillgelegt).
- Idempotent: nach dem ersten Lauf ist `crest_url` überall `NULL` → No-op.

### 3. Owner-Self-Service (`uploads.py`) → schreibt `Team.logo_url`
- `POST /upload/crest`: verarbeitet Bild wie bisher (→ WebP, `/uploads/crests/`),
  setzt aber `team.logo_url = /uploads/crests/{discord_id}.webp?v={hash8}` des
  verknüpften Teams. Kein verknüpftes Team → 400.
- `DELETE /upload/crest`: leert `team.logo_url` + löscht Datei.
- `GET /upload/crest/{discord_id}`: Redirect auf `team.logo_url`.
- Response-Feld heißt weiterhin `crest_url` (API-Kompatibilität), Wert = neue
  `logo_url`.

### 4. User-Profil-Ausgaben (`oauth.py`, `users.py`)
`crest_url` im Response wird aus dem verknüpften `team.logo_url` gespeist (statt
`UserProfile.crest_url`). Feldname bleibt für Kompatibilität.

### 5. `teams.py` — Admin-Endpoints vereinheitlichen
- Wappen per URL setzen/löschen: über bestehendes `PATCH /teams/{id}` (`logo_url`,
  inkl. `""/null`-Löschen — bereits umgesetzt). URL wird via `validate_crest_url`
  geprüft.
- Wappen-Upload (Datei) durch Admin: `POST /admin/teams/{id}/crest` bleibt, aber
  schreibt jetzt `Team.logo_url` (nicht mehr `UserProfile.crest_url`). Kein
  Owner/Profil mehr nötig — funktioniert für **jedes** Team.
- `PUT /admin/teams/{id}/crest` (URL) und `DELETE /admin/teams/{id}/crest` werden
  **entfernt** (durch `PATCH` abgedeckt).
- `crest_url` aus der Admin-Team-Liste (`discord_user.crest_url`) entfernen.

## Änderungen Frontend

### Admin-Modal (`admin.html`, `js/admin/teams.js`)
Die getrennten Steuerungen **Logo-URL-Feld** und **Wappen-Sektion** werden zu
**einer** „Wappen"-Steuerung zusammengelegt:
- Vorschau-Thumbnail (aus `team.logo_url`).
- URL-Eingabe → `PATCH /teams/{id}` (`logo_url`).
- Datei-Upload → `POST /admin/teams/{id}/crest`.
- „Entfernen" → `PATCH /teams/{id}` (`logo_url: null`).
- Nach jeder Aktion: Modal + Liste neu laden.

### Owner-Upload (Profil-Seite)
Backend-Wechsel ist transparent (weiterhin `POST /upload/crest`). Labels ggf.
klarstellen („Team-Wappen").

### `team-utils.js`
Bereits ohne Override-Logik; unverändert (Cache-Fix schon erfolgt).

## Migration bestehender Anzeige (Ahrem-Beispiel)
RW Ahrem: `logo_url` aktuell `NULL`, `crest_url` = falsche webp. Migration setzt
`logo_url` = falsche webp (Status quo bleibt), danach ist alles auf einem Feld.
Admin/Owner korrigiert dann das **eine** Feld auf das richtige Wappen — überall
sofort korrekt.

## Testing

- `test_crests_*`: `/teams/crests` liefert nur noch `logo_url`; Override-Tests
  entfernen/anpassen.
- Migration: aktive crest_url → logo_url; crest_url danach NULL; idempotent.
- Owner-Upload/-Delete schreiben `team.logo_url`; ohne Team → 400.
- Admin-Upload schreibt `team.logo_url` (auch für Teams ohne Discord-User).
- `test_admin_crest.py`: an neue Zielfelder anpassen (PUT/DELETE-Endpoints weg).

## Betroffene Dateien

- `backend/app/routers/teams.py` — crests-Override raus, Admin-Endpoints vereinheitlichen
- `backend/app/routers/uploads.py` — Owner-Flow → team.logo_url
- `backend/app/routers/oauth.py`, `users.py` — crest_url aus team.logo_url speisen
- `backend/app/migrations.py` (oder Startup) — Einmal-Backfill
- `backend/tests/test_admin_crest.py`, `test_update_team.py`, neuer Migrationstest
- `frontend/admin.html`, `frontend/js/admin/teams.js` — eine Wappen-Steuerung
- `docs/CHANGELOG.md`
