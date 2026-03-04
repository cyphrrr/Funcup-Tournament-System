# Frontend

Read‑only Webapp für Teilnehmer und Zuschauer.

## Aufgaben

- Anzeige von:
  - Spielplänen
  - Ergebnissen
  - Gruppen
  - KO‑Baum
  - Spieltags‑Posts

## Prinzipien

- Keine Business‑Logik
- Nur API‑Zugriffe
- Statisch auslieferbar

## Theme-System

Alle öffentlichen Seiten nutzen `js/themes.js` für das Theming:

- **6 Farbpaletten**: Stadion bei Flutlicht, Vereinsheim, Retro Scoreboard, Pitch Green, Stadium Electric, Derby Night
- Jedes Theme hat eine **Light- und Dark-Variante**
- **Default**: Stadion bei Flutlicht (Dark)
- **Dropdown** im Footer zum Wechseln, **Toggle** im Header für Light/Dark
- Theme wird in `localStorage` gespeichert (`biw_theme`, `biw_dark_mode`)
- Synchrones Script-Laden verhindert Flash of Wrong Theme

`admin.html` ist nicht betroffen (eigenes Dark-Theme).

---

> Das Frontend ist austauschbar. Die Daten nicht.
