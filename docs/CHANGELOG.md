# FUNCUP TOURNAMENT SYSTEM — Changelog

Änderungen seit Einführung des 3-Bracket-Systems (KO-Logik v2).

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
