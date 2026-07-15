# Admin-Wappenverwaltung (UserProfile.crest_url)

**Datum:** 2026-07-15
**Status:** Design (approved)
**Ansatz:** A — Admin verwaltet `UserProfile.crest_url` direkt

## Problem

Wappen in Tabellen werden über `GET /api/teams/crests` aufgelöst. Dort
überschreibt `UserProfile.crest_url` (per Discord-Owner hochgeladenes Wappen)
die `Team.logo_url` (Admin-verwaltet). Lädt ein Owner ein falsches/missbräuchliches
Bild hoch, zeigt es in **allen Tabellen**, während das Team-Profil
(`GET /api/teams/{id}`, liest nur `logo_url`) weiterhin das korrekte Wappen zeigt.

Der Admin hat aktuell **keinen** Zugriff auf `crest_url` — nur der Owner selbst
kann via `POST/DELETE /api/upload/crest` sein Wappen setzen/löschen. Das
Admin-Panel editiert ausschließlich `Team.logo_url`, was den Override nicht
berührt. Ergebnis: Ein falsches Upload-Wappen ist über die UI nicht korrigierbar.

Konkreter Auslöser: RW Ahrem (Team 138) hatte in `crest_url` eine Datei, deren
Inhalt byte-identisch mit Emmerichs Wappen war (Fehl-Upload). Isoliert, kein
Code-Bug im Upload-Pfad.

## Ziel

Ein Admin soll das hochgeladene Wappen eines Teams **sehen, ersetzen (per
Direkt-URL oder Datei-Upload) und löschen** können — direkt im bestehenden
Team-Edit-Modal.

## Nicht-Ziele (YAGNI)

- Keine neue Team-Override-Ebene/Spalte (Ansatz B verworfen).
- Kein Sperren gegen erneutes Owner-Upload (kein Lock-Flag).
- Keine globale Wappen-Galerie (nur Pro-Team-Ansicht im Modal).
- Keine Änderung der Override-Reihenfolge in `/teams/crests`.

## Architektur

Der Admin verwaltet das Feld, das ohnehin gewinnt: `UserProfile.crest_url`.
Voraussetzung ist ein verknüpfter Discord-User (die `UserProfile` des Teams).
Teams ohne Owner haben kein `crest_url` und werden über `logo_url` (bereits
admin-editierbar) versorgt.

Die Override-Logik in `GET /api/teams/crests` bleibt **unverändert**. Der Fix
besteht ausschließlich darin, dem Admin Kontrolle über `crest_url` zu geben.

## Backend

Neue Endpoints in `backend/app/routers/teams.py`, alle mit
`Depends(get_current_user)` (JWT-Admin). Sie operieren auf der verknüpften
`UserProfile` (`UserProfile.team_id == team_id`, aktiv bevorzugt — siehe
Auswahlregel unten).

### Auswahl der UserProfile

Wie in `get_team_detail`: bevorzugt `is_active == True`. Existiert keine aktive
Profile-Zeile, aber eine inaktive mit `crest_url`, wird diese für Anzeige/Delete
verwendet (damit auch ein „verwaistes" Override entfernbar bleibt). Für das
**Setzen** (URL/Upload) wird die aktive Profile verlangt; fehlt sie → 400.

### 1. Admin-Team-Liste erweitern

`GET /api/teams` (Funktion, die `allTeamsData` speist) ergänzt im
`discord_user`-Objekt das Feld `crest_url` (aus `profile.crest_url`). So kann das
Modal ohne Zusatz-Request das aktuelle Wappen anzeigen.

### 2. `PUT /api/admin/teams/{team_id}/crest` — per URL setzen

- Body: `{ "crest_url": "https://…" }`
- Validierung (server-seitig, Pflicht):
  - Muss mit `http://`, `https://` oder `/uploads/` beginnen.
  - Darf keine Zeichen enthalten, die aus dem `src`-Attribut ausbrechen:
    `"`, `'`, `<`, `>`, Backtick, Whitespace, sowie `\n`/`\r`.
  - Leerer/whitespace-only Wert → 400 (zum Löschen den DELETE-Endpoint nutzen).
- Setzt `profile.crest_url = crest_url`, `db.commit()`.
- Kein-Owner → 400 „Kein verknüpfter Discord-User, nutze die Logo-URL".

### 3. `POST /api/admin/teams/{team_id}/crest` — Datei-Upload

- multipart `file`.
- Wiederverwendung von `validate_image_file` + `process_crest_image` (image_utils).
- Speicherpfad: `uploads/crests/{discord_id}.webp` (überschreibt Owner-Datei —
  konsistent mit Owner-Flow).
- `crest_url = /uploads/crests/{discord_id}.webp?v={hash8}`, wobei `hash8` =
  erste 8 Hex-Zeichen des SHA256 des verarbeiteten WebP → **Cache-Busting**,
  Austausch sofort sichtbar.
- Setzt `profile.crest_url`, `db.commit()`.
- Kein-Owner → 400.

### 4. `DELETE /api/admin/teams/{team_id}/crest` — löschen

- Löscht die Datei `uploads/crests/{discord_id}.webp` (falls vorhanden und der
  crest_url auf eine lokale Upload-Datei zeigt; externe URLs → nur DB-Feld leeren).
- Setzt `profile.crest_url = None`, `db.commit()`.
- Danach fällt `/teams/crests` automatisch auf `Team.logo_url` zurück.
- Kein-Owner / kein crest_url → 404 „Kein Wappen vorhanden".

### Hardening

`crestImg` (`frontend/js/team-utils.js`) interpoliert die URL ungeescaped in
`<img src>`. Zusätzlich zur Backend-Validierung wird `crestImg` leicht gehärtet
(URL-Attributwert escapen), damit auch Altbestand sicher gerendert wird.

## Frontend

`admin.html` + `js/admin/teams.js`, neuer Abschnitt „Wappen" im Team-Edit-Modal:

- **Thumbnail** des effektiv angezeigten Wappens: `crest_url` (falls gesetzt),
  sonst `logo_url`, sonst Initialen-Platzhalter.
- Bei vorhandenem `crest_url`-Override: Label „Hochgeladenes Wappen (überschreibt
  Logo-URL)" plus:
  - URL-Eingabefeld + „URL speichern" → `PUT …/crest`
  - Datei-Auswahl + „Hochladen" → `POST …/crest` (multipart)
  - „Löschen" → `DELETE …/crest`
- Ohne verknüpften Discord-User: Crest-Sektion ausgeblendet, Hinweis „Kein
  Discord-User — Wappen über Logo-URL setzen".
- Bestehendes Logo-URL-Feld bleibt als Fallback-Ebene erhalten.
- Nach jeder Aktion: Modal-Daten neu laden (`loadAllTeams`) + Crest-Cache
  invalidieren (`sessionStorage`-Key `biw_crests` löschen), damit die Tabellen
  aktualisiert erscheinen.

## Testing

`backend/tests/test_admin_crest.py` (Muster wie `test_update_team.py`, Router-
Funktionen direkt gegen In-Memory-SQLite):

- URL setzen aktualisiert `crest_url`.
- URL-Validierung lehnt unsichere Werte ab (Quote, `<`, Whitespace, falsches Schema).
- Upload verarbeitet Bild, setzt `crest_url` mit `?v=`-Hash, schreibt Datei.
- Delete leert `crest_url` → `/teams/crests` liefert dann `logo_url`.
- Kein-Owner → 400 bei set/upload; 404 bei delete.

Frontend: manueller Smoke-Test (Modal öffnen, URL setzen, Upload, Delete, Tabelle
prüft Aktualisierung).

## Sicherheit

- Alle neuen Endpoints hinter JWT-Admin (`get_current_user`).
- Server-seitige URL-Validierung + `crestImg`-Escaping gegen Attribut-Injection.
- Upload nutzt die bestehende Bildvalidierung/-verarbeitung (Format, Größe, WebP).

## Betroffene Dateien

- `backend/app/routers/teams.py` — Liste erweitern + 3 neue Endpoints
- `backend/app/schemas.py` — Request/Response-Schemas für Crest-Set
- `frontend/admin.html` — Modal-Abschnitt „Wappen"
- `frontend/js/admin/teams.js` — Anzeige + set/upload/delete + Cache-Invalidierung
- `frontend/js/team-utils.js` — `crestImg`-Escaping
- `backend/tests/test_admin_crest.py` — neue Tests
- `docs/CHANGELOG.md` — Eintrag
