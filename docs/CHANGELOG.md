# FUNCUP TOURNAMENT SYSTEM — Changelog

Änderungen seit Einführung des 3-Bracket-Systems (KO-Logik v2).

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
