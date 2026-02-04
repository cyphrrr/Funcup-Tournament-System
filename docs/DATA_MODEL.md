# BIW Pokal – DATA_MODEL.md

Dieses Dokument beschreibt das **logische Datenmodell** des BIW‑Pokals.
Es ist **technologie‑agnostisch** und kann auf SQL, ORMs (Prisma, SQLAlchemy, TypeORM) oder JSON‑Stores abgebildet werden.

Quelle:
- `LOGIC.md`
- `ARCHITECTURE.md`

---

## 1. Grundsätze

- Alle Entitäten sind **saisonspezifisch** oder **saisonsensitiv**
- Fremdschlüssel sind explizit
- Keine impliziten Beziehungen
- Historische Daten bleiben unverändert

---

## 2. Tabellen / Entitäten

### 2.1 seasons

Repräsentiert eine Pokalsaison.

| Feld | Typ | Beschreibung |
|----|----|----|
| id | PK | Eindeutige ID |
| name | string | z. B. "Saison 50" |
| status | enum | planned / active / archived |
| created_at | datetime | Erstellzeitpunkt |

---

### 2.2 groups

Gruppen innerhalb einer Saison.

| Feld | Typ | Beschreibung |
|----|----|----|
| id | PK | Eindeutige ID |
| season_id | FK → seasons.id | Zugehörige Saison |
| name | string | A–L |
| sort_order | int | Reihenfolge |

**Constraint:**
- `(season_id, name)` ist eindeutig

---

### 2.3 teams

Teilnehmende Teams.

| Feld | Typ | Beschreibung |
|----|----|----|
| id | PK | Eindeutige ID |
| name | string | Anzeigename |
| external_id | string | onlineliga‑ID |

---

### 2.4 season_teams

Zuordnung Team ↔ Saison ↔ Gruppe.

| Feld | Typ | Beschreibung |
|----|----|----|
| id | PK | Eindeutige ID |
| season_id | FK → seasons.id | Saison |
| team_id | FK → teams.id | Team |
| group_id | FK → groups.id | Gruppe |

**Constraints:**
- `(season_id, team_id)` eindeutig

---

### 2.5 matchdays

Logische Spieltage (Trigger‑Einheit).

| Feld | Typ | Beschreibung |
|----|----|----|
| id | PK | Eindeutige ID |
| season_id | FK → seasons.id | Saison |
| name | string | SP1, SP2, Viertelfinale |
| phase | enum | group / ko |
| completed | boolean | abgeschlossen |

---

### 2.6 matches

Einzelne Spiele.

| Feld | Typ | Beschreibung |
|----|----|----|
| id | PK | Eindeutige ID |
| season_id | FK → seasons.id | Saison |
| matchday_id | FK → matchdays.id | Spieltag |
| group_id | FK → groups.id (nullable) | Gruppe |
| round | enum | group / sp4 / sp5 / sp6 |
| home_team_id | FK → teams.id | Heimteam |
| away_team_id | FK → teams.id | Auswärtsteam |
| home_goals | int | Tore Heim |
| away_goals | int | Tore Gast |
| kickoff_at | datetime | Anstoß |
| status | enum | scheduled / played |

---

### 2.7 posts

Automatisierte Spieltags‑Posts.

| Feld | Typ | Beschreibung |
|----|----|----|
| id | PK | Eindeutige ID |
| season_id | FK → seasons.id | Saison |
| matchday_id | FK → matchdays.id | Spieltag |
| title | string | Titel |
| content | text | Inhalt |
| published_at | datetime | Veröffentlichungszeit |

---

## 3. Abgeleitete Daten (nicht persistieren)

Diese Werte werden **berechnet**, nicht gespeichert:

- Tabellenstände
- Tordifferenzen
- KO‑Weiterkommen
- Ranglisten

---

## 4. Beziehungen (Übersicht)

```
Season
 ├─ Groups
 ├─ Matchdays
 ├─ Matches
 ├─ Posts
 └─ SeasonTeams
      └─ Team
```

---

## 5. Migrationsstrategie

- Bestehende Saisons → Import als `archived`
- Neue Saison → nativ
- Keine rückwirkende Neuberechnung

---

## 6. Ziel

Ein **stabiles, klares Datenmodell**,

- das jede Saison isoliert
- Automatisierung erlaubt
- Frontend‑agnostisch ist
- langfristig wartbar bleibt

---

_Ende von DATA_MODEL.md_
