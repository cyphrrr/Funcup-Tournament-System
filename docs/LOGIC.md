# BIW Pokal – LOGIC.md

Dieses Dokument beschreibt die **fachliche Logik** des BIW‑Pokals unabhängig von Technik, Frameworks oder Tools.
Es ist die **Single Source of Truth** für Implementierung (Backend), Automatisierung (n8n) und Darstellung (Frontend).

---

## 1. Grundprinzip

- Der BIW‑Pokal ist ein **saisonenbasiertes Turnier**.
- Jede Saison ist **vollständig isoliert** von anderen Saisons.
- Alle Daten (Gruppen, Teams, Spiele, Spieltage, Posts) existieren **nur im Kontext einer Saison**.

---

## 2. Entitäten

### 2.1 Season
Repräsentiert eine Pokalsaison.

**Attribute:**
- id
- name (z. B. "Saison 50")
- status (`planned | active | archived`)
- created_at

---

### 2.2 Group
Repräsentiert eine Gruppe innerhalb einer Saison.

**Regeln:**
- Gruppen sind **saisonspezifisch**.
- Gruppe "A" in Saison 50 ≠ Gruppe "A" in Saison 32.

**Attribute:**
- id
- season_id
- name (A–L)
- order

---

### 2.3 Team
Repräsentiert ein teilnehmendes Team.

**Regeln:**
- Ein Team kann in mehreren Saisons teilnehmen.
- Gruppenzuordnung ist **pro Saison eindeutig**.

**Attribute:**
- id
- name
- external_id (z. B. onlineliga.de)

---

### 2.4 Match
Repräsentiert ein einzelnes Spiel.

**Regeln:**
- Ein Match gehört **genau einer Saison**.
- Ein Match gehört entweder:
  - einer Gruppe (Gruppenphase)
  - oder einer KO‑Runde

**Attribute:**
- id
- season_id
- group_id (nullable)
- round (`group | sp4 | sp5 | sp6`)
- home_team_id
- away_team_id
- home_goals
- away_goals
- kickoff_at
- status (`scheduled | played`)

---

### 2.5 Matchday
Logische Zusammenfassung von Matches.

**Regeln:**
- Matchdays sind die **Trigger‑Einheit** für Automatisierung.
- Ein Matchday gilt als **abgeschlossen**, wenn alle Matches `played` sind.

**Attribute:**
- id
- season_id
- name (z. B. "SP3", "Viertelfinale")
- phase (`group | ko`)
- completed (boolean)

---

### 2.6 Post
Repräsentiert einen öffentlichen Spieltags‑Post.

**Regeln:**
- Ein Post ist **immutable**, sobald veröffentlicht.
- Posts werden automatisiert erzeugt.

**Attribute:**
- id
- season_id
- matchday_id
- title
- content
- published_at

---

## 3. Turnierphasen

### 3.1 Gruppenphase (SP1–SP3)

**Rahmenbedingungen:**
- Maximale Teilnehmerzahl pro Saison: **64 Teams**
- Maximale Teams pro Gruppe: **4** (fix)
- Gruppenphase findet **ausschließlich in ingame‑Woche 39–41** statt

**Ableitung der Gruppen:**
- Gruppen werden **automatisch** aus der Teilnehmerzahl abgeleitet
- Formel:
  ```
  gruppen_anzahl = ceil(teilnehmerzahl / 4)
  ```
- Gruppennamen werden **dynamisch** vergeben (A, B, C, …)
- Gruppen sind **keine Stammdaten**, sondern ein **Ergebnis der Saison‑Konfiguration**

**Verteilung:**
- Teams werden möglichst gleichmäßig auf Gruppen verteilt
- Beispiel bei 22 Teams:
  - Gruppen A–F
  - Verteilung: 4, 4, 4, 4, 3, 3

**Weiterkommen:**
- Qualifikation für die KO‑Phase (z. B. Platz 1–2) ist saisonal konfigurierbar

---

### 3.2 KO‑Phase (ab SP4)

**Rahmenbedingungen:**
- KO‑Phase beginnt **ab ingame‑Woche 42**
- Läuft bis **Woche 1 der Folgesaison**
- Direkte Ausscheidung

**Freilose (Byes):**
- Wenn die Anzahl qualifizierter Teams **keine Zweierpotenz** ist,
  werden **Freilose** vergeben
- Freilose sind ein **regulärer Zustand**, kein Sonderfall
- Teams mit Freilos steigen erst in einer späteren Runde ein

**Runden (typisch):**
- SP4 (z. B. Viertelfinale)
- SP5 (Halbfinale)
- SP6 (Finale)

---

## 4. Automatismen (n8n)

### 4.1 Ergebnis‑Import

**Trigger:**
- manuell oder zeitgesteuert

**Ablauf:**
1. Ergebnisse von onlineliga.de abrufen
2. n8n sendet Array an `POST /api/matches/import`
3. Backend verarbeitet pro Ergebnis:
   - Saison + Spieltag auflösen
   - Team‑Namen auf IDs mappen (case‑insensitive)
   - Match im Spielplan suchen
   - Falls Heim/Gast vertauscht: automatisch Swap + Tore tauschen
   - Ergebnis eintragen, Status → `played`

**Filterung (Backend):**
- **Unbekannte Teams** werden übersprungen (Friendly‑Gegner außerhalb des Pokals)
- **Nicht existierende Paarungen** werden übersprungen (Friendlies mit falscher Zuordnung)
- **Bereits gespielte Matches** werden nicht überschrieben
- **Vertauschte Heim/Gast** werden automatisch korrigiert (Ingame‑Friendlies)

---

### 4.2 Matchday‑Abschluss

**Bedingung:**
- Alle Matches eines Matchdays sind `played`

**Aktionen:**
- Matchday → `completed = true`
- Post erzeugen
- Discord‑Webhook auslösen

---

### 4.3 Auto‑Export

**Formate:**
- Excel
- CSV
- JSON

**Scope:**
- pro Matchday
- pro Saison

---

## 5. Frontend‑Prinzipien

- Frontend ist **read‑only**.
- Keine Business‑Logik im UI.
- Darstellung basiert ausschließlich auf API‑Daten.

---

## 6. Historische Saisons

- Vergangene Saisons sind **read‑only**.
- Keine Neuberechnung.
- Nur Anzeige und Archiv.

---

## 7. Ziel

Ein **offenes, nachvollziehbares, automatisierbares Turnier‑System**,

- unabhängig von CMS
- ohne Paywalls
- versionierbar über GitHub
- steuerbar über n8n

---

_Ende von LOGIC.md_
