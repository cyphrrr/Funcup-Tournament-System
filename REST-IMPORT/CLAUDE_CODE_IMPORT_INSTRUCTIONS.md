# BIW Pokal - Import Anweisungen für Claude Code

## Übersicht

Dieses Dokument beschreibt, wie der WordPress-zu-Backend-Import durchgeführt wird.
Das Python-Script `wp_to_backend_import.py` ersetzt den n8n-Workflow und importiert
alle Turnierdaten (Saison 10-50) direkt von der WordPress REST API ins FastAPI Backend.

---

## Voraussetzungen

### Backend-Server
- **Host:** 192.168.178.51
- **Service:** funcup-backend.service
- **Datenbank:** `/root/claude-projects/Funcup-Tournament-System/backend/biw.db`

### WordPress API
- **URL:** https://biw-pokal.de/wp-json/sportspress/v2/
- **Auth:** Basic Auth (Credentials im Script)

---

## Schritt-für-Schritt Import

### Schritt 1: Datenbank zurücksetzen

**WICHTIG:** Vor dem Import muss die Datenbank leer sein!

```bash
# 1. Backend-Service stoppen
sudo systemctl stop funcup-backend.service

# 2. Datenbank löschen
rm /root/claude-projects/Funcup-Tournament-System/backend/biw.db

# 3. Backend-Service neu starten (erstellt leere DB)
sudo systemctl start funcup-backend.service

# 4. Warten bis Service bereit ist
sleep 5

# 5. Prüfen ob Service läuft
sudo systemctl status funcup-backend.service
```

### Schritt 2: Verbindung prüfen

```bash
# Backend erreichbar?
curl -s http://192.168.178.51:8000/api/seasons | head -c 100

# WordPress API erreichbar?
curl -s "https://biw-pokal.de/wp-json/sportspress/v2/seasons?per_page=5" | head -c 200
```

### Schritt 3: Import-Script ausführen

```bash
# In das Projektverzeichnis wechseln
cd /root/claude-projects/Funcup-Tournament-System

# Script ausführen
python3 wp_to_backend_import.py
```

### Schritt 4: Import validieren

Nach Abschluss des Imports:

```bash
# Anzahl Seasons prüfen (sollte 41 sein)
curl -s http://192.168.178.51:8000/api/seasons | jq 'length'

# Stichprobe: Season 10 prüfen
curl -s http://192.168.178.51:8000/api/seasons/1/groups-with-teams | jq '.[] | {group: .group.name, teams: (.teams | length), matches: (.matches | length)}'

# Stichprobe: Season 50 prüfen
curl -s http://192.168.178.51:8000/api/seasons/41/groups-with-teams | jq '.[] | {group: .group.name, teams: (.teams | length), matches: (.matches | length)}'
```

---

## Erwartete Ergebnisse

| Metrik | Erwarteter Wert |
|--------|-----------------|
| Seasons | 41 (Saison 10-50) |
| Groups pro Season | 5-16 (abhängig von Teilnehmerzahl) |
| Teams gesamt | ~1000-1500 |
| Matches gesamt | ~3000-4000 |

---

## Fehlerbehandlung

### Backend nicht erreichbar
```bash
# Service-Status prüfen
sudo systemctl status funcup-backend.service

# Logs prüfen
sudo journalctl -u funcup-backend.service -n 50

# Service neu starten
sudo systemctl restart funcup-backend.service
```

### WordPress API Fehler
```bash
# Rate Limiting? Warten und erneut versuchen
# Auth-Fehler? Credentials im Script prüfen
```

### Import abgebrochen
Das Script ist fortsetzbar. Bei Abbruch:
1. Prüfen welche Seasons bereits importiert wurden
2. Im Script `SEASON_START` auf die nächste Season setzen
3. Script erneut starten

---

## Script-Konfiguration

Die wichtigsten Einstellungen in `wp_to_backend_import.py`:

```python
# WordPress REST API
WP_BASE_URL = "https://biw-pokal.de/wp-json/sportspress/v2"
WP_AUTH = ("Geschäftsführer", "WxuJ J9fp IC6d ogbP hxbQ SDAZ")

# Backend API
BACKEND_URL = "http://192.168.178.51:8000"
BACKEND_API_KEY = "biw-n8n-secret-key-change-me"

# Import-Einstellungen
SEASON_START = 10
SEASON_END = 50
PARTICIPANT_COUNT = 64  # Für 16 Groups (A-P)
REQUEST_DELAY = 0.1     # Sekunden zwischen Requests
```

---

## Einzelne Season testen

Um nur eine Season zu testen (z.B. Saison 50):

```python
# Im Script ändern:
SEASON_START = 50
SEASON_END = 50
```

---

## Log-Datei

Der Import schreibt Logs nach `wp_import.log` im aktuellen Verzeichnis.

```bash
# Live-Logs verfolgen
tail -f wp_import.log

# Fehler suchen
grep -i error wp_import.log
```

---

## Kompletter Einzeiler für Claude Code

Falls du alles in einem Rutsch ausführen willst:

```bash
# ACHTUNG: Löscht alle Daten und importiert neu!
sudo systemctl stop funcup-backend.service && \
rm -f /root/claude-projects/Funcup-Tournament-System/backend/biw.db && \
sudo systemctl start funcup-backend.service && \
sleep 5 && \
cd /root/claude-projects/Funcup-Tournament-System/REST-IMPORT && \
python3 wp_to_backend_import.py
```

---

## Nach dem Import

1. **Frontend testen:** https://beta.biw-pokal.de
2. **Tabellen prüfen:** Stimmen die Punkte/Tore?
3. **Alle Seasons durchklicken:** Sind alle Daten da?

Bei Problemen: Log-Datei prüfen und ggf. einzelne Season neu importieren.
