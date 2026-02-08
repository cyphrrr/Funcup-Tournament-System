# BIW Pokal Import Tools

Automatisierter Import von Gruppenphasen-Daten (Saison 12-50) von biw-pokal.de

## 📦 Komponenten

1. **`biw_scraper.py`** - Web Scraper für HTML-Kalender
2. **`biw_importer.py`** - API Import in FastAPI Backend
3. **`requirements.txt`** - Python Dependencies

## 🚀 Installation

```bash
# Virtuelle Umgebung erstellen
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# oder: venv\Scripts\activate  # Windows

# Dependencies installieren
pip install -r requirements.txt
```

## 📊 Phase 1: Daten Scraping

### Basis-Nutzung

```bash
# Alle Saisons scrapen (12-50)
python biw_scraper.py
```

### Output-Struktur

```
output/
├── biw_data_12-50.json      # Hauptdaten
├── errors_12-50.json        # Fehlerlog
└── summary_12-50.txt        # Zusammenfassung
```

### JSON-Struktur

```json
{
  "metadata": {
    "scraped_at": "2026-02-07T...",
    "start_season": 12,
    "end_season": 50,
    "total_errors": 0
  },
  "seasons": [
    {
      "season": 12,
      "groups": [
        {
          "group": "A",
          "matches": [
            {
              "date": "23. Juli 2022",
              "time": "10:00",
              "home_team": "BV Tremonia",
              "away_team": "Sport-Club Krefeld",
              "home_goals": 1,
              "away_goals": 1,
              "matchday": 1,
              "status": "played"
            }
          ],
          "table": [
            {
              "team_name": "BV Tremonia",
              "played": 3,
              "wins": 2,
              "draws": 1,
              "losses": 0,
              "goals_for": 6,
              "goals_against": 1,
              "goal_diff": 5,
              "points": 7
            }
          ],
          "errors": []
        }
      ]
    }
  ]
}
```

## 🔄 Phase 2: API Import (Optional)

### Voraussetzungen

- FastAPI Backend läuft auf `http://localhost:8000`
- Endpoints verfügbar:
  - `POST /api/seasons`
  - `POST /api/seasons/{id}/groups`
  - `POST /api/teams`
  - `POST /api/seasons/{id}/teams`
  - `POST /api/seasons/{id}/matches`

### Import durchführen

```bash
# Standard Import (localhost)
python biw_importer.py output/biw_data_12-50.json

# Custom API URL
python biw_importer.py output/biw_data_12-50.json --api-url https://beta.biw-pokal.de

# Mit Skip existing (falls Saison 10-11 schon da sind)
python biw_importer.py output/biw_data_12-50.json --skip-existing
```

### Import-Log

Logs werden geschrieben nach:
- Console (live progress)
- `biw_import.log` (vollständiges Log)

## 🛠️ Konfiguration & Anpassung

### Scraper-Optionen

In `biw_scraper.py` kannst du anpassen:

```python
# Season Range ändern
scraper = BIWScaper(start_season=12, end_season=20)

# Request Timeouts
response = self.session.get(url, timeout=10)

# Rate Limiting
time.sleep(0.5)  # Pause zwischen Gruppen
time.sleep(1)    # Pause zwischen Saisons
```

### Importer-Optionen

```python
# API Base URL
importer = BIWImporter(base_url="http://localhost:8000")

# Rate Limiting
time.sleep(0.1)  # Pause zwischen Matches
time.sleep(1)    # Pause zwischen Saisons
```

## 🔍 Fehlerbehandlung

### Scraper Fehler-Typen

1. **Network Errors** - 404, Timeout, Connection
2. **Parse Errors** - Ungültige HTML-Struktur
3. **Data Errors** - Fehlende Felder

Alle Fehler werden geloggt in:
- `biw_scraper.log`
- `output/errors_12-50.json`

### Importer Fehler-Typen

1. **API Connection** - Backend nicht erreichbar
2. **Validation Errors** - Ungültige Daten
3. **Duplicate Errors** - Einträge existieren bereits

Alle Fehler werden geloggt in:
- `biw_import.log`
- Console output

## 📈 Workflow-Beispiel

### Kompletter Import-Prozess

```bash
# 1. Daten scrapen
python biw_scraper.py

# 2. Scraping-Ergebnisse prüfen
cat output/summary_12-50.txt
cat output/errors_12-50.json  # Falls Fehler

# 3. JSON validieren (optional)
python -m json.tool output/biw_data_12-50.json > /dev/null
echo "JSON is valid ✓"

# 4. Backend starten (in separatem Terminal)
cd /path/to/backend
uvicorn main:app --reload

# 5. Import durchführen
python biw_importer.py output/biw_data_12-50.json

# 6. Import-Log prüfen
tail -f biw_import.log
```

## 🧪 Testing & Validation

### Einzelne Saison testen

```python
# In biw_scraper.py main() ändern:
scraper = BIWScaper(start_season=12, end_season=12)
```

### Dry-Run (ohne API-Calls)

Kommentiere in `biw_importer.py` die tatsächlichen API-Calls aus:

```python
# response = self.session.post(url, json=payload)
# print(f"Would POST to {url}: {payload}")
```

## 📋 Daten-Qualität Checks

Nach dem Scraping prüfen:

```bash
# Anzahl Saisons
jq '.seasons | length' output/biw_data_12-50.json

# Gruppen pro Saison
jq '.seasons[] | {season: .season, groups: (.groups | length)}' output/biw_data_12-50.json

# Matches pro Saison
jq '.seasons[] | {season: .season, matches: ([.groups[].matches[]] | length)}' output/biw_data_12-50.json

# Unique Teams
jq '[.seasons[].groups[].matches[] | .home_team, .away_team] | unique | length' output/biw_data_12-50.json
```

## ⚠️ Known Issues & Workarounds

### Issue 1: Inkonsistente Team-Namen

**Problem:** Team-Namen können Schreibfehler enthalten

**Workaround:** Nach Import manuelles Team-Mapping über Admin-Interface

### Issue 2: Fehlende Matchday-Nummern

**Problem:** Ältere Saisons haben keine Spieltag-Angaben

**Lösung:** Script verwendet Default-Wert 1 und loggt Warning

### Issue 3: Zeitzone-Probleme

**Problem:** Datumsformat kann variieren

**Lösung:** Script verwendet String-Speicherung, Parsing im Backend

## 🔧 Troubleshooting

### "No matches found"

```bash
# Manuell URL prüfen
curl https://biw-pokal.de/calendar/biw-21-a/

# HTML-Struktur inspizieren
python -c "
from biw_scraper import BIWScaper
s = BIWScaper()
html = s.fetch_calendar(21, 'a')
print(html[:1000])
"
```

### "API Connection Failed"

```bash
# Backend erreichbar?
curl http://localhost:8000/api/health

# Logs prüfen
tail -f biw_import.log
```

### "Duplicate team" Fehler

Normal! Teams sind global und werden wiederverwendet.

## 📝 Logs & Debugging

### Log-Level erhöhen

```python
logging.basicConfig(level=logging.DEBUG)
```

### Netzwerk-Traffic anzeigen

```python
import http.client
http.client.HTTPConnection.debuglevel = 1
```

## 🎯 Performance

### Scraping-Zeit

- ~1-2 Sekunden pro Gruppe
- ~10-30 Sekunden pro Saison
- **Gesamt: ~15-30 Minuten für alle 39 Saisons**

### Import-Zeit

- ~100-200ms pro Match
- ~1-5 Sekunden pro Gruppe
- **Gesamt: ~10-20 Minuten für alle Daten**

## 📞 Support

Bei Problemen:

1. Logs prüfen (`biw_scraper.log`, `biw_import.log`)
2. Error JSON prüfen (`output/errors_12-50.json`)
3. HTML-Struktur validieren (manuell URL aufrufen)
4. API-Responses testen (curl/Postman)

## 📄 License

Internal tool for BIW Pokal migration
