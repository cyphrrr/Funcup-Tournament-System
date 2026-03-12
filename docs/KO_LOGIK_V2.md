# KO-Bracket-Logik v2 — Regelwerk

**Stand:** 08.03.2026
**Status:** Spezifikation (noch nicht implementiert)
**Geltungsbereich:** Nur Saisons mit `status != "archived"`

---

## Designprinzipien

1. **Keine Freilose** — jedes Bracket hat exakt 8 oder 16 Teams
2. **Auffüllen statt Lücken** — Teams aus niedrigeren Platzierungen rücken auf
3. **Ziel: Achtelfinale (16)** als Standard, Viertelfinale (8) als Fallback
4. **8 ist das absolute Minimum** — unter 8 Teams wird kein Bracket generiert
5. **Aufrücker-Ranking** über Onlineliga Google Sheets (niedrigerer Ø = besser)
6. **Platzierungsgrenzen:** Meisterrunde nur Erste+Zweite, Lucky Loser nur Zweite+Dritte, Loser nur Dritte+Vierte
7. **Spiel um Platz 3** — jedes Bracket enthält automatisch ein Spiel zwischen den Halbfinal-Verlierern

---

## Bracket-Hierarchie

| Priorität | Bracket | Natürlicher Pool | Aufrücker aus | Pflicht |
|-----------|---------|-----------------|---------------|---------|
| 1 | Meisterrunde | Gruppenerste | Gruppenzweite | Ja (immer) |
| 2 | Lucky Loser | übrige Gruppenzweite | Gruppendritte | Ja (wenn ≥8 Teams) |
| 3 | Loser | übrige Gruppendritte | Gruppenvierte | Optional (nur bei exakt 16) |

---

## Algorithmus

### Eingabe

```
G     = Anzahl Gruppen der Saison
E[G]  = Gruppenerste (sortiert nach Gruppenname A, B, C, ...)
Z[G]  = Gruppenzweite
D[G]  = Gruppendritte
V[N]  = Gruppenvierte (N = Anzahl Gruppen mit ≥4 Teams)

ranking(team) = Onlineliga Ø-Wert aus Google Sheets (niedriger = besser)
```

### Schritt 1 — Meisterrunde

```
pool = E (alle Gruppenersten)

IF len(pool) >= 16:
    meister = die 16 besten aus pool (nach Ranking)
    übrige Erste → Lucky-Loser-Pool
ELSE:
    bedarf = 16 - len(pool)
    aufrücker = Z sortiert nach Ranking (beste zuerst)

    IF len(pool) + len(Z) >= 16:
        meister = pool + aufrücker[:bedarf]
        übrige_zweite = aufrücker[bedarf:]
    ELSE:
        # FALLBACK auf 8er-Bracket
        IF len(pool) >= 8:
            meister = pool[:8] (die 8 besten Ersten)
            übrige Erste → Lucky-Loser-Pool
            übrige_zweite = Z (alle)
        ELSE:
            bedarf_8 = 8 - len(pool)
            IF bedarf_8 <= len(Z):
                meister = pool + aufrücker[:bedarf_8]
                übrige_zweite = aufrücker[bedarf_8:]
            ELSE:
                FEHLER: "Nicht genug Teams für Meisterrunde"
```

### Schritt 2 — Lucky Loser

```
pool = übrige_zweite (Gruppenzweite die NICHT in Meisterrunde sind)

IF len(pool) >= 16:
    lucky_loser = pool[:16]
    übrige Zweite → Loser-Pool (als "Dritte" behandelt? Nein → verworfen)
ELSE:
    bedarf = 16 - len(pool)
    aufrücker = D sortiert nach Ranking

    IF len(pool) + len(D) >= 16:
        lucky_loser = pool + aufrücker[:bedarf]
        übrige_dritte = aufrücker[bedarf:]
    ELSE:
        # FALLBACK auf 8er-Bracket
        bedarf_8 = 8 - len(pool)
        IF bedarf_8 <= 0:
            lucky_loser = pool[:8]
            übrige_dritte = D (alle)
        ELSE IF bedarf_8 <= len(D):
            lucky_loser = pool + aufrücker[:bedarf_8]
            übrige_dritte = aufrücker[bedarf_8:]
        ELSE:
            lucky_loser = NICHT GENERIERT
            übrige_dritte = D (alle)
```

### Schritt 3 — Loser (optional)

```
pool = übrige_dritte (Gruppendritte die NICHT in Lucky Loser sind)
aufrücker = V sortiert nach Ranking

IF len(pool) + len(V) >= 16:
    bedarf = 16 - len(pool)
    loser = pool + aufrücker[:bedarf]
ELSE:
    loser = NICHT GENERIERT
```

**Hinweis:** Loser-Bracket wird NUR bei exakt 16 Teams generiert (kein 8er-Fallback).

---

## Seeding innerhalb eines Brackets

Gespiegeltes Seeding, 1 vs 16, 2 vs 15, etc.

**Reihenfolge der Teams im Bracket:**
1. Zuerst die "natürlichen" Teams (z.B. Gruppenerste), sortiert nach Gruppenname (A, B, C, ...)
2. Dann die Aufrücker, sortiert nach Onlineliga-Ranking (beste zuerst)

**Beispiel Meisterrunde bei 41 Teams:**
```
Position  1: Erster Gruppe A      (Seed 1)
Position  2: Erster Gruppe B      (Seed 2)
...
Position 11: Erster Gruppe K      (Seed 11)
Position 12: Bester Zweiter       (Seed 12)  ← Aufrücker
Position 13: Zweitbester Zweiter  (Seed 13)  ← Aufrücker
Position 14: ...                  (Seed 14)  ← Aufrücker
Position 15: ...                  (Seed 15)  ← Aufrücker
Position 16: Fünftbester Zweiter  (Seed 16)  ← Aufrücker

Paarungen (gespiegelt):
  Seed 1  vs Seed 16
  Seed 2  vs Seed 15
  Seed 3  vs Seed 14
  Seed 4  vs Seed 13
  Seed 5  vs Seed 12
  Seed 6  vs Seed 11
  Seed 7  vs Seed 10
  Seed 8  vs Seed 9
```

---

## Szenarien-Validierung

### 41 Teams (11 Gruppen: 8×4er, 3×3er)

```
E=11, Z=11, D=11, V=8

Meister:  11 < 16 → bedarf 5 Zweite → 11+11=22 ≥ 16 ✓
          = 11 Erste + 5 Zweite = 16 ✓  (AF-Start)

Lucky L:  6 Zweite übrig, bedarf 10 Dritte → 6+11=17 ≥ 16 ✓
          = 6 Zweite + 10 Dritte = 16 ✓  (AF-Start)

Loser:    1 Dritter + 8 Vierte = 9 < 16
          → NICHT GENERIERT

Platz 3:  ✓ Meister + Lucky Loser (je 1 Spiel)

KO-Teilnehmer: 32/41 = 78%
```

### 64 Teams (16 Gruppen à 4)

```
E=16, Z=16, D=16, V=16

Meister:  16 Erste = 16 ✓ (keine Aufrücker)
Lucky L:  16 Zweite = 16 ✓ (keine Aufrücker)
Loser:    16 Dritte = 16 ✓ (keine Aufrücker)

Platz 3:  ✓ alle 3 Brackets (je 1 Spiel)

KO-Teilnehmer: 48/64 = 75%
```

### 48 Teams (12 Gruppen à 4)

```
E=12, Z=12, D=12, V=12

Meister:  12 Erste + 4 Zweite = 16 ✓
Lucky L:  8 Zweite + 8 Dritte = 16 ✓
Loser:    4 Dritte + 12 Vierte = 16 ✓

Platz 3:  ✓ alle 3 Brackets (je 1 Spiel)

KO-Teilnehmer: 48/48 = 100% (!)
```

### 51 Teams (13 Gruppen: 12×4er, 1×3er)

```
E=13, Z=13, D=13, V=12

Meister:  13 Erste + 3 Zweite = 16 ✓
Lucky L:  10 Zweite + 6 Dritte = 16 ✓
Loser:    7 Dritte + 12 Vierte = 19 ≥ 16
          = 7 Dritte + 9 Vierte = 16 ✓

Platz 3:  ✓ alle 3 Brackets (je 1 Spiel)

KO-Teilnehmer: 48/51 = 94%
```

### 20 Teams (5 Gruppen à 4)

```
E=5, Z=5, D=5, V=5

Meister:  5+5=10 < 16 → Fallback 8
          5 Erste + 3 Zweite = 8 ✓  (VF-Start)

Lucky L:  2 Zweite, bedarf 14 → 2+5=7 < 16 → Fallback 8
          2+5=7 < 8 → NICHT GENERIERT

Loser:    → NICHT GENERIERT

Platz 3:  ✓ Meister (1 Spiel); Lucky Loser + Loser entfallen

KO-Teilnehmer: 8/20 = 40%
```

### 32 Teams (8 Gruppen à 4)

```
E=8, Z=8, D=8, V=8

Meister:  8+8=16 ✓
          8 Erste + 8 Zweite = 16 ✓  (AF-Start)

Lucky L:  0 Zweite übrig → bedarf 16 Dritte → 0+8=8 < 16 → Fallback 8
          0+8=8 ✓  (VF-Start, 8 Gruppendritte)

Loser:    0 Dritte + 8 Vierte = 8 < 16
          → NICHT GENERIERT

Platz 3:  ✓ Meister + Lucky Loser (je 1 Spiel); Loser entfällt

KO-Teilnehmer: 24/32 = 75%
```

### 12 Teams (3 Gruppen à 4)

```
E=3, Z=3, D=3, V=3

Meister:  3+3=6 < 16 → Fallback 8
          3+3=6 < 8 → FEHLER

→ Keine automatische KO-Generierung möglich
→ Admin muss manuelles Bracket erstellen (create-empty Endpoint)
```

---

## Spiel um Platz 3

Jedes der 3 Brackets (Meister, Lucky Loser, Loser) enthält ein Spiel um Platz 3. Die beiden Halbfinal-Verlierer spielen gegeneinander.

### Datenmodell

Drei zusätzliche Spalten auf `ko_matches`:

| Spalte | Typ | Beschreibung |
|--------|-----|--------------|
| `is_third_place` | Integer (0/1) | 1 = Spiel um Platz 3 |
| `loser_next_match_id` | FK → ko_matches | Verlierer-Weiterleitung vom Halbfinale |
| `loser_next_match_slot` | String | `"home"` / `"away"` |

### Generierung

- Automatisch bei Bracket-Erstellung in `create_bracket_matches()`
- `round = total_rounds` (gleiche Runde wie Finale), `position = 2`
- Beide Halbfinal-Matches erhalten `loser_next_match_id` → Platz-3-Match
- Slot-Zuweisung: HF Position 1 (ungerade) → `home`, Position 2 (gerade) → `away`
- Nur bei Brackets mit ≥ 2 Runden (mind. 4 Teams = VF-Bracket)

### Ergebnis-Weiterleitung

Beim Eintragen eines Halbfinal-Ergebnisses (PATCH + n8n-Import):
- Sieger → Finale (via `next_match_id`, wie bisher)
- Verlierer → Platz-3-Spiel (via `loser_next_match_id`)
- Bei Unentschieden + Tiebreaker: gleiche Logik, Verlierer = das andere Team

### Frontend

- Eigene Spalte neben dem Finale, visuell abgetrennt (gestrichelte Linie links)
- Volle Admin-Funktionalität (Ergebnis eintragen, Team-Zuweisung)
- Auch in `archiv.html` Kompaktansicht dargestellt

### Sonderfall: bestehende Brackets

Bereits generierte Brackets (vor diesem Feature) haben kein Platz-3-Match. Diese können manuell über den Admin nicht angelegt werden — sie entfallen für die betroffene Saison. Ab der nächsten Bracket-Generierung automatisch enthalten.

---

## Abhängigkeiten

| Komponente | Status | Beschreibung |
|-----------|--------|-------------|
| `ranking_service.py` | ✅ implementiert | Google Sheets Ranking, 10min Cache |
| `ko_bracket_generator.py` | ✅ implementiert | Neue Logik ohne Freilose, inkl. Platz-3-Generierung |
| `routers/ko.py` PATCH | ✅ erweitert | Sieger + Verlierer-Weiterleitung |
| `routers/matches.py` Import | ✅ erweitert | Verlierer-Weiterleitung bei n8n-Import |
| `admin.html` / `ko-phase.js` | ✅ erweitert | Aufrücker-Info + Platz-3-Verwaltung |
| `ko.html` | ✅ erweitert | Bracket-Darstellung inkl. Platz-3-Spalte |
| `archiv.html` | ✅ erweitert | Kompakte Bracket-Ansicht inkl. Platz 3 |

---

## Entscheidungen

- [x] **Keine Freilose:** Brackets haben exakt 8 oder 16 Teams, Aufrücker füllen auf
- [x] **Aufrücker-Ranking:** WM/EM-Methode (Punkte → TD → Tore → OL-Ranking)
- [x] **Freispiel-Wertung:** 3er-Gruppen erhalten fiktives Freispiel für Vergleichbarkeit
- [x] **Preview-Endpoint:** Dry-Run vor Generierung (`/ko-brackets/preview`)
- [x] **Spiel um Platz 3:** In allen 3 Brackets automatisch generiert, eigene Spalte im Frontend

---

## Offene Fragen

- [ ] Soll der Admin die Aufrücker-Auswahl manuell überschreiben können?
