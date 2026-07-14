# Design: Bot-Befehle `/gruppen` und `/spielplan`

**Datum:** 2026-07-14
**Status:** Approved (Design)

## Ziel

Zwei neue Slash-Commands für den Discord-Bot (`bot/`):

- **`/gruppen`** — zeigt alle Gruppen der aktuellen bzw. geplanten Saison mit ihren Teams.
  Nutzen: Überblick über die Gruppen, sobald die Auslosung gelaufen ist.
- **`/spielplan`** — zeigt den Spielplan. Bei Aufruf erscheint ein Auswahlmenü,
  über das man wählt, welche Gruppe (oder alle Gruppen) angezeigt werden soll.

## Nicht-Ziele (YAGNI)

- Keine Backend-Änderung: Beide Befehle nutzen den bestehenden Endpoint
  `GET /api/seasons/{id}/groups-with-teams` (im Bot: `api.get_groups_with_teams()`).
- Keine Tabellen/Standings in `/gruppen` — nur die Gruppen-Zusammensetzung.
- Kein gemeinsames Refactoring von `spieltag.py` — der Befehl bleibt unangetastet.

## Entscheidungen (aus Brainstorming)

| Frage | Entscheidung |
|-------|--------------|
| Sichtbarkeit der Ausgabe | **Öffentlich** im Channel posten (wie `/spieltag`). |
| `/spielplan` Auswahl | Einzelne Gruppe **plus** Option „Alle Gruppen". |
| Berechtigung | Wie `/spieltag`: nur Rollen **Organisation** oder **Teilnehmer**. |
| Code-Struktur | Jedes Cog **eigenständig** (eigene Kopie von Rollen-/Saison-Logik). `spieltag.py` bleibt unverändert. |

## Architektur

Zwei neue, in sich geschlossene Cog-Dateien, automatisch geladen durch
`load_cogs()` in `bot/main.py`:

- `bot/cogs/gruppen.py`
- `bot/cogs/spielplan.py`

Jedes Cog enthält seine eigene Kopie zweier kleiner Hilfsfunktionen (bewusst
dupliziert statt geteilt, um das laufende `/spieltag` nicht anzufassen):

- `has_permission(member) -> bool` — prüft Rolle gegen
  `{"organisation", "teilnehmer"}` (case-insensitive), analog `spieltag.py`.
- `resolve_season(seasons) -> dict | None` — wählt die anzuzeigende Saison:
  **erst `status == "active"`, sonst `status == "planned"`**, sonst `None`.

Reine (Discord-freie) Formatierungs-Helfer je Cog, damit sie testbar sind:

- `gruppen.py`: `build_gruppen_embed(season, groups_data, user)`
- `spielplan.py`:
  - `build_group_options(groups_data)` → Liste `SelectOption` (je Gruppe + „Alle Gruppen")
  - `build_spielplan_embed(season, groups_data, selection, user)` — `selection` ist
    entweder ein Gruppenname oder der Sentinel `"__all__"`.
  - `format_score(home_goals, away_goals)` — analog `spieltag.py`.

## Datenfluss

```
/gruppen
  Rollen-Check → get_seasons() → resolve_season()
  → get_groups_with_teams(season_id)
  → build_gruppen_embed()
  → ctx.followup.send(embed)          # öffentlich (defer ohne ephemeral)

/spielplan
  Rollen-Check → get_seasons() → resolve_season()
  → get_groups_with_teams(season_id)
  → build_group_options()
  → ephemerales Select-Menü anzeigen
  → [User wählt] → build_spielplan_embed()
  → interaction.channel.send(embed)   # öffentlich
  → ephemerale Nachricht auf "✅ Spielplan gepostet!" editieren
```

## Darstellung (Embeds)

### `/gruppen`
- Ein Embed, Titel `🏆 BIW Pokal — {season.name} · Gruppen`, Farbe Gold.
- Ein Field pro Gruppe (sortiert nach Gruppenname), Name `📋 Gruppe X`,
  Wert = Monospace-Block mit den Teamnamen (ein Team pro Zeile).
- Beschreibung: kurze Kennzahl, z. B. `{n} Gruppen · {m} Teams`.
- Sonderfälle:
  - Keine Saison (weder active noch planned) → „Aktuell ist kein Pokal geplant."
  - Gruppen existieren, aber ohne Teams → Hinweis „Auslosung noch nicht erfolgt."

### `/spielplan`
- Auswahlmenü (ephemeral): Option `Alle Gruppen` zuoberst, danach je Gruppe eine
  Option (`Gruppe A`, `Gruppe B`, …). Value: `__all__` bzw. der Gruppenname.
- Ergebnis-Embed, Titel `🏆 BIW Pokal — {season.name} · Spielplan{ · Gruppe X}`.
- Gruppierung nach **Spieltag**: pro Spieltag ein Field `Spieltag N`,
  Wert = Monospace-Zeilen `Heim  X : Y  Gast`, bei ungespielten Spielen `X : Y`
  leer und Marker `⏳`. Bei „Alle Gruppen" wird zusätzlich pro Gruppe getrennt
  (Field-Name z. B. `Gruppe A · Spieltag N`), um die Discord-Limits einzuhalten.
- Field-Wert > 1024 Zeichen wird gesplittet (Muster aus `aktuell.py`).

## Berechtigung & Fehlerbehandlung

- Fehlende Rolle → ephemerale Meldung „Du brauchst die Rolle **Organisation**
  oder **Teilnehmer** …" (Text analog `spieltag.py`), **kein** öffentlicher Post.
- Backend nicht erreichbar / leere Daten → freundliche ephemerale Fehlermeldung.
- Globaler Error-Handler in `main.py` greift zusätzlich.

## Tests

Der Bot hat bislang keine Test-Infrastruktur. Neue, eigenständige Unit-Tests
(reine dicts, kein Discord/Netzwerk) für die reinen Helfer:

- `resolve_season`: active bevorzugt, sonst planned, sonst None.
- `build_group_options`: „Alle Gruppen" zuoberst, je Gruppe eine Option, korrekte Values.
- `build_spielplan_embed`: richtige Spieltag-Gruppierung, `⏳` für ungespielt,
  korrekte Team-Namen-Auflösung.
- `build_gruppen_embed`: ein Field pro Gruppe, Teamnamen enthalten, „Auslosung
  noch nicht erfolgt" bei leeren Gruppen.

## Betroffene Dateien

- **Neu:** `bot/cogs/gruppen.py`
- **Neu:** `bot/cogs/spielplan.py`
- **Neu:** Test-Datei(en) für die Helfer (z. B. `bot/tests/` oder analog vorhandener Testpfade).
- **Unverändert:** `bot/cogs/spieltag.py`, Backend.
