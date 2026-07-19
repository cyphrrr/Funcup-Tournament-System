# FUNCUP TOURNAMENT SYSTEM — Changelog

Änderungen seit Einführung des 3-Bracket-Systems (KO-Logik v2).

---

## 2026-07-19 — Admin: „KO-Runde neu auslosen" (One-Click)

- Neuer Endpoint `POST /api/seasons/{id}/ko-brackets/redraw` (auth): löscht bestehende KO-Brackets/-Matches und generiert sie **in einer Transaktion** neu — schlägt die Generierung fehl, bleibt das alte Bracket unangetastet
- **Guard:** bei bereits eingetragenen KO-Ergebnissen antwortet der Endpoint mit 409 (`{"error":"results_exist","played_matches":N}`); erst `{"force":true}` überschreibt
- Admin-Panel: neuer Button **„🎲 Neu auslosen"** neben „Brackets zurücksetzen" — mit Bestätigungsdialog und zweiter Warnstufe, falls Ergebnisse verloren gehen würden
- Hintergrund: Neu auslosen war bisher nur zweistufig (Reset → Generieren) und ohne Schutz vor Ergebnisverlust möglich
- Tests: neues `test_ko_redraw.py` (6 Tests); Design: `docs/superpowers/specs/2026-07-19-ko-redraw-design.md`

---

## 2026-07-19 — KO-Auslosung: keine Same-Group-Paarungen in Runde 1

- **Fix:** Teams aus derselben Gruppe konnten in Runde 1 direkt wieder aufeinandertreffen (Saison 54: JungeFohlen88 [E1] vs FC Wissel 2020 [E2], die am letzten Gruppenspieltag gegeneinander spielten). Ursache: `seed_teams()` spiegelt rein positionell ohne Gruppen-Trennung; ein Aufrücker konnte auf den eigenen Gruppensieger gelost werden
- Neu: `resolve_same_group_conflicts()` läuft nach dem Seeding in **allen drei Brackets** (Generate + Preview). Bei Konflikt wird das Away-Team mit dem der nächstgelegenen Paarung getauscht — minimale Abweichung, nicht betroffene Paarungen bleiben unverändert. Nicht lösbare Konflikte (kein konfliktfreier Tauschpartner) bleiben bestehen
- Tests: neues `test_ko_seeding.py` (7 Tests: Pure-Function + Generate/Preview-Integration im 9×4-Szenario)

---

## 2026-07-15 — Wappen-Konsolidierung: eine Quelle (Team.logo_url)

- **Strukturfix:** Team-Wappen wurden an zwei Stellen gespeichert (`Team.logo_url` + `UserProfile.crest_url`), mit Override-Priorität und getrennten Lesepfaden — Admin-Änderungen wirkten nicht auf die Tabellen. Jetzt ist **`Team.logo_url` die einzige Quelle**; egal ob per URL oder Upload gesetzt, alle Funktionen lesen von dort
- `GET /api/teams/crests` liefert nur noch `Team.logo_url` (kein `crest_url`-Override mehr)
- Owner-Self-Service (`POST/DELETE /api/upload/crest`) und Admin-Upload (`POST /api/admin/teams/{id}/crest`) schreiben beide `Team.logo_url`; Setzen/Löschen per URL über `PATCH /api/teams/{id}`. Owner **und** Admin nutzen dasselbe Feld
- Einmal-Migration (idempotent, beim Start): `UserProfile.crest_url` → `Team.logo_url` (aktueller Anzeigezustand bleibt erhalten), danach `crest_url` stillgelegt
- Admin-Modal: **eine** Wappen-Steuerung (URL/Upload/Entfernen), separates Logo-URL-Feld entfernt
- URL-Validierung beim Setzen (`PATCH`) + `crestImg`-Escaping; Dashboards/Team-Profil rendern relative Upload-Pfade und externe URLs korrekt
- Uploads unter `team-{id}.webp?v=<hash>` (Cache-Busting); alte Admin-Endpoints `PUT`/`DELETE .../crest` entfernt (durch `PATCH` abgedeckt)
- Tests: `test_admin_crest.py` (angepasst), neues `test_crest_backfill.py`; Design: `docs/superpowers/specs/2026-07-15-wappen-konsolidierung-design.md`

---

## 2026-07-15 — Fix: Wappen-Änderungen sofort sichtbar + Konsistenz

- Frontend-Wappen-Cache (`sessionStorage`, 10 Min TTL) entfernt: er überlebte Reloads inkl. Hard-Refresh und zeigte bis zu 10 Min veraltete Wappen. Jeder Seitenaufruf lädt jetzt frisch (In-Memory-Guard gegen Doppel-Fetch pro Seite)
- `GET /api/teams/crests` filtert jetzt auf `UserProfile.is_active` (konsistent mit dem Team-Profil): ein soft-gelöschtes Profil kann kein bereits entferntes Wappen wieder einblenden
- Test: `test_crests_ignores_inactive_profile_override`

## 2026-07-15 — Admin-Wappenverwaltung (hochgeladene Wappen)

- Admins können das per Discord-Owner hochgeladene Wappen (`UserProfile.crest_url`) eines Teams jetzt im Team-Edit-Modal **sehen, per URL/Datei ersetzen und löschen** — bisher konnte nur der Owner selbst sein Wappen ändern
- Hintergrund: `crest_url` überschreibt in den Tabellen (`/teams/crests`) die admin-verwaltete `Team.logo_url`. Bei einem falschen/missbräuchlichen Upload war das über die UI nicht korrigierbar
- Neue admin-geschützte Endpoints: `PUT /api/admin/teams/{id}/crest` (Direkt-URL), `POST …/crest` (Datei-Upload → WebP), `DELETE …/crest` (→ Fallback auf `logo_url`)
- URL-Validierung server-seitig (nur `http(s)://` / `/uploads/…`, keine attributsprengenden Zeichen); `crestImg` escaped die URL zusätzlich (Härtung gegen Attribut-Injection)
- Upload hängt einen Content-Hash als `?v=` an die crest_url → Austausch ist **sofort sichtbar** (kein Browser-/CDN-Cache-Problem mehr)
- Ohne verknüpften Discord-User: Crest-Sektion ausgeblendet, Hinweis auf die Logo-URL
- Tests: `backend/tests/test_admin_crest.py` (16); Design: `docs/superpowers/specs/2026-07-15-admin-crest-management-design.md`

---

## 2026-07-15 — Fix: Team-Wappen (logo_url) im Admin-Panel entfernbar

- `PATCH /api/teams/{id}` konnte ein per URL verlinktes Wappen (`Team.logo_url`) nicht mehr löschen: Der Guard `if update.logo_url is not None` ignorierte das vom Frontend beim Leeren gesendete `logo_url: null`, der Link blieb dauerhaft in der DB (überstand Speichern/Reload/Re-Login)
- Fix: `logo_url` wird jetzt über `model_fields_set` behandelt — wird das Feld mitgeschickt (auch `null`/`""`), wird es gesetzt; Leerstring wird zu `None` normalisiert, damit `/teams/crests` es nicht als leeres Wappen ausliefert
- Weggelassene Felder bleiben unangetastet (echtes PATCH-Verhalten für partielle Updates)
- Regressionstests: `backend/tests/test_update_team.py` (4 Tests: null-Clear, Leerstring-Clear, Weglassen erhält, Neu-Setzen)

---

## 2026-07-14 — Discord-Bot: `/gruppen` und `/spielplan`

- Neuer Befehl `/gruppen`: postet die Gruppen-Zusammensetzung (Gruppen + Teams) der aktiven, sonst geplanten Saison öffentlich im Channel — gedacht für den Überblick nach der Auslosung
- Neuer Befehl `/spielplan`: zeigt ein Auswahlmenü (jede Gruppe einzeln + „Alle Gruppen") und postet den nach Spieltagen gruppierten Spielplan öffentlich
- Beide Befehle nur für Rollen „Organisation"/„Teilnehmer" (konsistent mit `/spieltag`), keine Backend-Änderung (nutzen `GET /api/seasons/{id}/groups-with-teams`)
- Eigenständige Cogs `bot/cogs/gruppen.py` und `bot/cogs/spielplan.py`; `spieltag.py` unverändert
- Erste Bot-Unit-Tests unter `bot/tests/` (13 Tests für die reinen Helfer)
- Design: `docs/superpowers/specs/2026-07-14-bot-gruppen-spielplan-design.md`
- Fix: `/spielplan` „Alle Gruppen" verteilt den Spielplan jetzt auf mehrere Embeds, statt an Discords 25-Field-Limit zu scheitern (`400 Invalid Form Body`)
- Fix: `/spielplan` postet den Spielplan jetzt via Interaction-Followup statt `channel.send`; funktioniert damit auch ohne „Send Messages"-Recht des Bots im Channel (verhindert `403 Missing Access`)
- Fix: `/spieltag` postet ebenfalls via Interaction-Followup statt `channel.send` (gleicher `403 Missing Access`-Schutz)

---

## 2026-04-22 — KO-Logik V3 (Lucky Loser Vierte-Fallback)

- Lucky Loser kann nun im Fallback-Fall mit den besten Viertplatzierten auf 16 aufgefüllt werden
- Vierte werden nach Pokal-Leistung sortiert (Punkte → TD → Tore → Gegentore), nicht OL-Ranking
- Greift nur wenn Zweite+Dritte < 16 aber +Vierte ≥ 16
- Betroffene Szenarien: 38, 32, 24 Teams (deutlich höhere KO-Teilnahme)
- Loser-Bracket berücksichtigt bereits vergebene Vierte (kein doppelter Einsatz)
- Preview zeigt Fallback-Info-Banner und "↑ Fallback"-Badge für betroffene Teams
- `aufruecker_info` enthält neues Feld `lucky_loser_vierte_fallback`
- 3 neue E2E-Tests (38, 32, 24 Teams), 2 bestehende Tests aktualisiert
- Spezifikation: `docs/KO_LOGIK_V3.md`

---

## 2026-03-12 — Spiel um Platz 3

- 3 neue Spalten auf `ko_matches`: `is_third_place`, `loser_next_match_id`, `loser_next_match_slot`
- Automatische Generierung bei Bracket-Erstellung (`create_bracket_matches()`)
- Verlierer-Weiterleitung bei PATCH (`/ko-matches/{id}`) und n8n-Import (`/matches/import`)
- Frontend-Darstellung: eigene Spalte neben dem Finale (`ko.html` + Archiv-Kompaktansicht)
- Admin-Panel: volle Verwaltung inkl. Ergebnis-Eingabe und Team-Zuweisung (`ko-phase.js`)
- DB-Migration: `backend/scripts/migrate_third_place.py` (SQLite), `migrate_prod.py` (PostgreSQL)
- Primäre Spezifikation: `docs/KO_LOGIK_V2.md`

## 2026-03-11 — KO-Logik v3 (WM/EM-Ranking)

- Aufrücker-Ranking nach WM/EM-Methode (Punkte → TD → Tore → Gegentore → OL-Ranking)
- Freispiel-Wertung für 3er-Gruppen (+3 Pkt, +2:0 Tore) für Vergleichbarkeit
- `get_qualified_teams_v2()`: neuer Algorithmus mit normalisierter Gruppenphase
- 9/9 pytest bestehen

## 2026-03-08 — KO-Logik v2 (Keine Freilose, Aufrücker-System)

- Brackets haben exakt 8 oder 16 Teams — keine Freilose mehr
- Aufrücker aus niedrigeren Platzierungen füllen fehlende Slots auf
- Preview-Endpoint: `GET /api/seasons/{id}/ko-brackets/preview`
- Spezifikation: `docs/KO_LOGIK_V2.md`
