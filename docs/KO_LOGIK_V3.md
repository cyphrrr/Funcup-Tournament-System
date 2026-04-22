# KO-Bracket-Logik v3 — Regelwerk

**Stand:** 22.04.2026
**Status:** Spezifikation
**Vorgänger:** KO_LOGIK_V2 (08.03.2026)
**Geltungsbereich:** Nur Saisons mit `status != "archived"`

---

## Änderung gegenüber V2

**Einzige Änderung:** Lucky Loser darf im Fallback-Fall mit den besten Viertplatzierten auf 16 aufgefüllt werden.

Alle anderen Regeln aus V2 bleiben unverändert (Meisterrunde, Loser-Bracket, Seeding, Spiel um Platz 3, Freilos-Verbot, 8/16-Constraint).

---

## Designprinzipien

1. **Keine Freilose** — jedes Bracket hat exakt 8 oder 16 Teams
2. **Auffüllen statt Lücken** — Teams aus niedrigeren Platzierungen rücken auf
3. **Ziel: Achtelfinale (16)** als Standard, Viertelfinale (8) als Fallback
4. **8 ist das absolute Minimum** — unter 8 Teams wird kein Bracket generiert
5. **Aufrücker-Ranking** über Onlineliga Google Sheets (niedrigerer Ø = besser)
6. **Platzierungsgrenzen:** Meisterrunde nur Erste+Zweite, Lucky Loser Zweite+Dritte (+Vierte als Fallback), Loser nur Dritte+Vierte
7. **Spiel um Platz 3** — jedes Bracket enthält automatisch ein Spiel zwischen den Halbfinal-Verlierern
8. **NEU: Lucky-Loser-Vierte-Fallback** — wenn Zweite+Dritte nicht für 16 reichen, werden die besten Viertplatzierten nach Pokal-Leistung aufgefüllt

---

## Bracket-Hierarchie

| Priorität | Bracket | Natürlicher Pool | Aufrücker aus | Fallback-Aufrücker | Pflicht |
|-----------|---------|-----------------|---------------|-------------------|---------|
| 1 | Meisterrunde | Gruppenerste | Gruppenzweite (OL-Ranking) | — | Ja (immer) |
| 2 | Lucky Loser | übrige Gruppenzweite | Gruppendritte (OL-Ranking) | **Gruppenvierte (Pokal-Leistung)** | Ja (wenn ≥8 Teams) |
| 3 | Loser | übrige Gruppendritte | Gruppenvierte (OL-Ranking) | — | Optional (nur bei exakt 16) |

---

## Algorithmus

### Eingabe

```
G     = Anzahl Gruppen der Saison
E[G]  = Gruppenerste (sortiert nach Gruppenname A, B, C, ...)
Z[G]  = Gruppenzweite
D[G]  = Gruppendritte
V[N]  = Gruppenvierte (N = Anzahl Gruppen mit ≥4 Teams)

ranking(team)      = Onlineliga Ø-Wert aus Google Sheets (niedriger = besser)
pokal_leistung(team) = Gruppenphase-Statistik:
                       1. Punkte (absteigend)
                       2. Tordifferenz (absteigend)
                       3. Erzielte Tore (absteigend)
                       4. Gegentore (aufsteigend)
```

### Schritt 1 — Meisterrunde (unverändert zu V2)

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

### Schritt 2 — Lucky Loser (GEÄNDERT in V3)

```
pool = übrige_zweite (Gruppenzweite die NICHT in Meisterrunde sind)

IF len(pool) >= 16:
    lucky_loser = pool[:16]
    übrige Zweite → Loser-Pool
ELSE:
    bedarf = 16 - len(pool)
    aufrücker_dritte = D sortiert nach Ranking

    IF len(pool) + len(D) >= 16:
        # Normalfall: Dritte reichen
        lucky_loser = pool + aufrücker_dritte[:bedarf]
        übrige_dritte = aufrücker_dritte[bedarf:]
    ELSE:
        # ──────────────────────────────────────────────
        # NEU in V3: Vierte als Fallback-Aufrücker
        # ──────────────────────────────────────────────
        alle_verfuegbar = pool + D  # alle Zweiten + alle Dritten
        rest_bedarf = 16 - len(alle_verfuegbar)

        vierte_sorted = V sortiert nach Pokal-Leistung:
            1. Punkte (absteigend)
            2. Tordifferenz (absteigend)
            3. Erzielte Tore (absteigend)
            4. Gegentore (aufsteigend)

        IF len(alle_verfuegbar) + len(V) >= 16:
            # Vierte füllen auf 16 auf
            lucky_loser = alle_verfuegbar + vierte_sorted[:rest_bedarf]
            übrige_vierte = vierte_sorted[rest_bedarf:]
            übrige_dritte = []  # alle Dritten sind im Lucky Loser
        ELSE:
            # Selbst mit allen Vierten nicht genug für 16
            # → 8er-Fallback (ohne Vierte, wie V2)
            bedarf_8 = 8 - len(pool)
            IF bedarf_8 <= 0:
                lucky_loser = pool[:8]
                übrige_dritte = D (alle)
            ELSE IF bedarf_8 <= len(D):
                lucky_loser = pool + aufrücker_dritte[:bedarf_8]
                übrige_dritte = aufrücker_dritte[bedarf_8:]
            ELSE:
                lucky_loser = NICHT GENERIERT
                übrige_dritte = D (alle)
```

**Wichtig:** Die Viertplatzierten werden NUR herangezogen wenn:
1. Zweite + Dritte zusammen < 16, UND
2. Zweite + Dritte + Vierte zusammen ≥ 16

Ansonsten greift der bisherige 8er-Fallback (oder "NICHT GENERIERT").

**Ranking der Vierte-Fallback-Aufrücker:**
Anders als reguläre Aufrücker (OL-Ranking) werden die Viertplatzierten nach ihrer **Pokal-Leistung** in der Gruppenphase sortiert. Die Sortierkriterien sind identisch mit den Standings-Kriterien:
1. Punkte (absteigend)
2. Tordifferenz (absteigend)
3. Erzielte Tore (absteigend)
4. Gegentore (aufsteigend)

### Schritt 3 — Loser (unverändert zu V2)

```
pool = übrige_dritte (Gruppendritte die NICHT in Lucky Loser sind)
aufrücker = V_übrig sortiert nach Ranking (OL)
            ↑ V_übrig = Vierte die NICHT als Fallback in Lucky Loser sind

IF len(pool) + len(V_übrig) >= 16:
    bedarf = 16 - len(pool)
    loser = pool + aufrücker[:bedarf]
ELSE:
    loser = NICHT GENERIERT
```

**Hinweis:** Loser-Bracket wird NUR bei exakt 16 Teams generiert (kein 8er-Fallback). Wenn Vierte bereits als Fallback in die Lucky-Loser-Runde gezogen wurden, stehen sie dem Loser-Bracket nicht mehr zur Verfügung.

---

## Seeding innerhalb eines Brackets (unverändert)

Gespiegeltes Seeding, 1 vs 16, 2 vs 15, etc.

**Reihenfolge der Teams im Bracket:**
1. Zuerst die "natürlichen" Teams (z.B. Gruppenerste), sortiert nach Gruppenname (A, B, C, ...)
2. Dann die Aufrücker, sortiert nach jeweiligem Ranking (OL-Ranking bzw. Pokal-Leistung für Vierte-Fallback)

---

## Szenarien-Validierung

### 38 Teams (10 Gruppen: 8×4er, 2×3er) ← NEU, Auslöser für V3

```
E=10, Z=10, D=10, V=8

Meister:  10 < 16 → bedarf 6 Zweite → 10+10=20 ≥ 16 ✓
          = 10 Erste + 6 Zweite = 16 ✓

Lucky L:  4 Zweite übrig + 10 Dritte = 14 < 16
          → V3-Fallback: 14 + 8 Vierte = 22 ≥ 16 ✓
          = 4 Zweite + 10 Dritte + 2 Vierte (beste nach Pokal-Leistung) = 16 ✓

Loser:    0 Dritte + 6 Vierte = 6 < 16
          → NICHT GENERIERT

Platz 3:  ✓ Meister + Lucky Loser (je 1 Spiel)

KO-Teilnehmer: 32/38 = 84% (vorher V2: 24/38 = 63%)
```

### 41 Teams (11 Gruppen: 8×4er, 3×3er) — kein Unterschied zu V2

```
E=11, Z=11, D=11, V=8

Meister:  11 + 5 Zweite = 16 ✓
Lucky L:  6 Zweite + 10 Dritte = 16 ✓  (kein Fallback nötig)
Loser:    1 Dritter + 8 Vierte = 9 < 16 → NICHT GENERIERT

KO-Teilnehmer: 32/41 = 78%
```

### 32 Teams (8 Gruppen à 4) — V3-Fallback greift

```
E=8, Z=8, D=8, V=8

Meister:  8 + 8 Zweite = 16 ✓

Lucky L:  0 Zweite + 8 Dritte = 8 < 16
          → V3-Fallback: 8 + 8 Vierte = 16 ≥ 16 ✓
          = 8 Dritte + 8 Vierte (nach Pokal-Leistung) = 16 ✓

Loser:    0 Dritte + 0 Vierte = 0 < 16
          → NICHT GENERIERT

KO-Teilnehmer: 32/32 = 100% (vorher V2: 24/32 = 75%)
```

### 64 Teams (16 Gruppen à 4) — kein Unterschied zu V2

```
E=16, Z=16, D=16, V=16

Meister:  16 ✓
Lucky L:  16 ✓ (kein Fallback)
Loser:    16 ✓

KO-Teilnehmer: 48/64 = 75%
```

### 48 Teams (12 Gruppen à 4) — kein Unterschied zu V2

```
E=12, Z=12, D=12, V=12

Meister:  12 + 4 Zweite = 16 ✓
Lucky L:  8 Zweite + 8 Dritte = 16 ✓ (kein Fallback)
Loser:    4 Dritte + 12 Vierte = 16 ✓

KO-Teilnehmer: 48/48 = 100%
```

### 20 Teams (5 Gruppen à 4) — V3-Fallback greift

```
E=5, Z=5, D=5, V=5

Meister:  5+5=10 < 16 → Fallback 8
          = 5 Erste + 3 Zweite = 8 ✓

Lucky L:  2 Zweite + 5 Dritte = 7 < 16
          → V3-Fallback: 7 + 5 Vierte = 12 < 16 → nicht genug
          → 8er-Fallback: bedarf_8 = 8 - 2 = 6, nur 5 Dritte → < 8
          → NICHT GENERIERT (wie V2)

KO-Teilnehmer: 8/20 = 40%
```

### 24 Teams (6 Gruppen à 4) — V3-Fallback greift

```
E=6, Z=6, D=6, V=6

Meister:  6+6=12 < 16 → Fallback 8 (6 Erste + 2 Zweite = 8 ✓)

Lucky L:  4 Zweite + 6 Dritte = 10 < 16
          → V3-Fallback: 10 + 6 Vierte = 16 ≥ 16 ✓
          = 4 Zweite + 6 Dritte + 6 Vierte (nach Pokal-Leistung) = 16 ✓

Loser:    0 Dritte + 0 Vierte = 0 → NICHT GENERIERT

KO-Teilnehmer: 24/24 = 100% (vorher V2: 8/24 = 33%)
```

---

## Spiel um Platz 3 (unverändert)

Jedes der 3 Brackets (Meister, Lucky Loser, Loser) enthält ein Spiel um Platz 3. Die beiden Halbfinal-Verlierer spielen gegeneinander.

### Datenmodell

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
- Sieger → Finale (via `next_match_id`)
- Verlierer → Platz-3-Spiel (via `loser_next_match_id`)

---

## Zusammenfassung der Ranking-Methoden

| Kontext | Ranking-Methode | Sortierkriterien |
|---------|----------------|-----------------|
| Meister-Aufrücker (Zweite) | WM/EM + OL-Ranking | Punkte → TD → Tore → OL-Ø |
| Lucky-Loser-Aufrücker (Dritte) | WM/EM + OL-Ranking | Punkte → TD → Tore → OL-Ø |
| **Lucky-Loser-Fallback (Vierte)** | **Pokal-Leistung** | **Punkte → TD → Tore → Gegentore** |
| Loser-Aufrücker (Vierte) | OL-Ranking | OL-Ø |

---

## Abhängigkeiten

| Komponente | Status | Beschreibung |
|-----------|--------|-------------|
| `ranking_service.py` | ✅ vorhanden | Google Sheets Ranking, 10min Cache |
| `ko_bracket_generator.py` | 🔧 ANPASSEN | Lucky-Loser-Fallback mit Vierten hinzufügen |
| `routers/ko.py` | ✅ unverändert | |
| `admin.html` / `ko-phase.js` | 🔧 ANPASSEN | Preview muss Vierte-Fallback-Info anzeigen |
| `test_ko_e2e.py` | 🔧 ANPASSEN | Neue Testfälle für 38 Teams, 32 Teams, 24 Teams |

---

## Migration

Keine DB-Migration nötig. Die Änderung betrifft ausschließlich die Generierungs-Logik in `ko_bracket_generator.py` und die Preview-Darstellung.
