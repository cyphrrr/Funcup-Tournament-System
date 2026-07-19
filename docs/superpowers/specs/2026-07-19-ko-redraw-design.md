# Design: KO-Runde neu auslosen (Admin-Panel)

**Datum:** 2026-07-19
**Status:** Approved (Ansatz B)

## Problem

„Neu auslosen" ist im Admin-Panel nur als Zwei-Schritt-Prozess möglich
(Brackets zurücksetzen → Automatisch generieren). Die Schritte sind nicht
atomar: schlägt das Generieren fehl, steht die Saison ohne Bracket da.
Außerdem gibt es keinen Schutz davor, versehentlich bereits eingetragene
KO-Ergebnisse zu verwerfen.

Anlass: Nach dem Same-Group-Fix (v0.20.4-beta) musste das Bracket der
Saison 54 neu ausgelost werden; dabei fiel die fehlende Funktion auf.

## Entscheidung: Ansatz B — eigener Backend-Endpoint

Verworfen: (A) Frontend ruft reset + generate nacheinander (nicht atomar),
(C) `force`-Flag am bestehenden generate-Endpoint (ändert Semantik für
andere Nutzer des Endpoints).

## Backend

`POST /api/seasons/{season_id}/ko-brackets/redraw` (auth-geschützt)

- Body (optional): `{"force": bool}` — Default `false`
- Ablauf in **einer Transaktion**: alle `KOMatch`/`KOBracket` der Saison
  löschen (ohne Commit), dann `generate_ko_brackets_v2()` — dessen
  End-Commit schreibt beides zusammen. Schlägt die Generierung fehl
  (ValueError → 400), wird zurückgerollt: das alte Bracket bleibt intakt.
- **Guard:** Existieren KO-Matches mit `status='played'`, antwortet der
  Endpoint mit **409** und strukturiertem Detail
  `{"error": "results_exist", "played_matches": N}` — außer `force=true`.
- Fehlerfälle: 404 unbekannte Saison, 400 archivierte Saison,
  400 Gruppen nicht abgeschlossen (aus generate übernommen).

## Frontend (`frontend/js/admin/ko-phase.js`)

- Neuer Button **„🎲 Neu auslosen"** neben „⚠️ Brackets zurücksetzen"
  (sichtbar wenn `brackets_generated`).
- Klick → `confirm()`. Bei 409 → zweiter, deutlicher Dialog
  („N Ergebnisse gehen verloren — trotzdem neu auslosen?") → erneuter
  Call mit `force: true`.
- Bestehende Buttons bleiben unverändert.

## Tests

Neues `backend/tests/test_ko_redraw.py` (Router-Funktion direkt, wie
`test_ko_source_labels.py`):

1. Redraw erzeugt frisches Bracket (alte Matches weg, neue Paarungen ohne
   Same-Group-Konflikt)
2. 409 bei eingetragenen Ergebnissen, Bracket bleibt unverändert
3. `force=true` überschreibt trotz Ergebnissen
4. 400 bei archivierter Saison
5. 404 bei unbekannter Saison
6. Atomarität: schlägt Generierung fehl (Gruppe unvollständig), bleibt
   das alte Bracket bestehen
