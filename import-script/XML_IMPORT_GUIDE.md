# WordPress XML Import - Schnellanleitung

## 🎯 Workflow-Übersicht

```
WordPress XML (17MB)
        ↓
wordpress_xml_converter.py
        ↓
biw_data_xml_12-50.json (gleiche Struktur wie Scraper)
        ↓
biw_importer.py (unverändert!)
        ↓
FastAPI Backend
```

---

## 🚀 Quick Start

### 1. XML konvertieren

```bash
# Dependencies installieren (falls noch nicht)
pip install -r requirements.txt

# XML zu JSON konvertieren
python wordpress_xml_converter.py wordpress-export.xml

# Output:
# output/biw_data_xml_12-50.json   ← Hauptdaten
# output/errors_xml_12-50.json     ← Fehlerlog
# output/summary_xml_12-50.txt     ← Zusammenfassung
```

### 2. Daten prüfen

```bash
# Summary anschauen
cat output/summary_xml_12-50.txt

# JSON validieren
python -m json.tool output/biw_data_xml_12-50.json > /dev/null
echo "JSON is valid ✓"

# Fehler checken
cat output/errors_xml_12-50.json
```

### 3. In Backend importieren

```bash
# Backend muss laufen!
cd backend && uvicorn app.main:app --reload

# In neuem Terminal:
python biw_importer.py output/biw_data_xml_12-50.json
```

---

## 📊 Was der Converter macht

### Extrahiert aus WordPress XML:

- **Matches** (`<item>` mit `post_type="sp_event"`)
- **Saisons** (aus `<category domain="sp_season">`)
- **Gruppen** (aus `<category domain="sp_league">` wie "BIW-46-A")
- **Teams** (aus Match-Titeln: "Team A vs Team B")
- **Ergebnisse** (aus `sp_results` PHP-serialized data)
- **Spieltag** (aus `sp_day` wie "SP2")
- **Datum/Zeit** (aus `wp:post_date`)

### Berechnet automatisch:

- Tabellen (Punkte, Tordifferenz, etc.)
- Team-Statistiken
- Sortierung nach Regeln

### Ignoriert:

- Posts, Pages, Comments
- Teams (`sp_team` post type)
- Andere Custom Post Types
- Nicht-Event-Items

---

## 🔍 XML-Struktur erkannt

```xml
<item>
  <title>FC Schlake 04 vs FC Nicht-Schalke</title>
  <wp:post_type>sp_event</wp:post_type>
  <wp:post_date>2025-07-30 10:00:00</wp:post_date>
  
  <!-- Season & Group -->
  <category domain="sp_season">Saison 46</category>
  <category domain="sp_league">BIW-46-A</category>
  
  <!-- Teams (IDs) -->
  <wp:postmeta>
    <wp:meta_key>sp_team</wp:meta_key>
    <wp:meta_value>437</wp:meta_value>
  </wp:postmeta>
  
  <!-- Result (PHP serialized) -->
  <wp:postmeta>
    <wp:meta_key>sp_results</wp:meta_key>
    <wp:meta_value>a:3:{i:437;a:2:{s:5:"goals";s:1:"6";...}}</wp:meta_value>
  </wp:postmeta>
  
  <!-- Matchday -->
  <wp:postmeta>
    <wp:meta_key>sp_day</wp:meta_key>
    <wp:meta_value>SP2</wp:meta_value>
  </wp:postmeta>
</item>
```

---

## ⚠️ Bekannte Limitierungen

### 1. Team-Namen aus Titel extrahiert

**Problem:** WordPress speichert Team-IDs, nicht Namen  
**Lösung:** Converter liest Team-Namen aus Match-Titel ("Team A vs Team B")  
**Risiko:** Falls Titel-Format inkonsistent ist, schlägt Parsing fehl

### 2. PHP-serialized Results

**Problem:** WordPress nutzt PHP-Serialisierung für Ergebnisse  
**Lösung:** Regex-Parser für Pattern `i:TEAM_ID;a:2:{s:5:"goals";s:1:"X";`  
**Risiko:** Falls Format abweicht, werden Ergebnisse als "scheduled" markiert

### 3. Gruppen-Erkennung aus Liga-Namen

**Annahme:** Liga-Namen folgen Pattern `BIW-{SAISON}-{GRUPPE}`  
**Beispiel:** "BIW-46-A", "biw-21-d"  
**Fallback:** Wenn kein Match, wird Item übersprungen

---

## 🧪 Testing

### Minimal-Test (wenige Items)

```bash
# Nur erste 500 Zeilen der XML
head -n 500 wordpress-export.xml > test.xml
echo "</channel></rss>" >> test.xml

# Konvertieren
python wordpress_xml_converter.py test.xml

# Prüfen
cat output/summary_xml_*.txt
```

### Vollständiger Test

```bash
# Komplette 17MB XML
python wordpress_xml_converter.py wordpress-export.xml

# Erwartung: ~3000-5000 Matches (geschätzt)
```

---

## 📈 Performance

- **XML Parsing:** ~10-30 Sekunden für 17MB
- **JSON Speichern:** ~1-2 Sekunden
- **Gesamt:** < 1 Minute

Deutlich schneller als Scraping (15-30 Minuten)!

---

## 🔧 Troubleshooting

### "No matches parsed"

**Ursache:** XML enthält keine `sp_event` Items  
**Check:**
```bash
grep -c 'sp_event' wordpress-export.xml
```

### "Could not parse team names"

**Ursache:** Match-Titel folgt nicht Pattern "Team A vs Team B"  
**Check:**
```bash
grep '<title>' wordpress-export.xml | head -20
```

**Fix:** Passe Titel-Parser in Zeile ~175 an

### "Missing season or league"

**Ursache:** Items haben keine `sp_season` oder `sp_league` Category  
**Check:**
```bash
grep -A 5 'sp_event' wordpress-export.xml | grep 'category domain'
```

---

## 📝 Logs & Debugging

### Log-Dateien

- `xml_converter.log` - Vollständiges Conversion-Log
- `output/errors_xml_*.json` - Strukturierte Fehler
- `output/summary_xml_*.txt` - Statistiken

### Debug-Modus

```python
# In wordpress_xml_converter.py ändern (Zeile 19):
logging.basicConfig(level=logging.DEBUG)
```

---

## ✅ Validation Checklist

Nach Conversion prüfen:

```bash
# 1. JSON valide?
python -m json.tool output/biw_data_xml_12-50.json > /dev/null

# 2. Anzahl Saisons
jq '.seasons | length' output/biw_data_xml_12-50.json

# 3. Matches pro Saison
jq '.seasons[] | {season: .season, matches: ([.groups[].matches[]] | length)}' output/biw_data_xml_12-50.json

# 4. Unique Teams
jq '[.seasons[].groups[].matches[] | .home_team, .away_team] | unique | length' output/biw_data_xml_12-50.json

# 5. Fehler-Count
jq '.metadata.total_errors' output/biw_data_xml_12-50.json
```

---

## 🎯 Vergleich: Scraper vs XML

| Aspekt | Web Scraper | XML Converter |
|--------|-------------|---------------|
| **Speed** | 15-30 Min | < 1 Min |
| **Vollständigkeit** | Abhängig von HTML | 100% (was in DB ist) |
| **Fehleranfällig** | Ja (HTML-Änderungen) | Nein (stabiles Format) |
| **Requires** | Live-Website | XML-Export |
| **Output** | Identisch | Identisch |

**Empfehlung:** Nutze XML Converter, da du bereits den Export hast! ✅

---

## 🔄 Wiederverwendbarkeit

Der Converter erzeugt **exakt das gleiche JSON-Format** wie der Scraper.

Das bedeutet:
- ✅ `biw_importer.py` funktioniert ohne Änderungen
- ✅ Alle Validations-Scripts funktionieren
- ✅ Du kannst beide Quellen kombinieren (z.B. alte Saisons via XML, neue via Scraper)

---

## 💡 Best Practices

### 1. Erst konvertieren, dann prüfen

```bash
python wordpress_xml_converter.py export.xml
cat output/summary_xml_*.txt
# Wenn OK:
python biw_importer.py output/biw_data_xml_*.json
```

### 2. Fehler-Log immer checken

```bash
if [ -f output/errors_xml_*.json ]; then
  echo "⚠️  Es gab Fehler beim Konvertieren!"
  cat output/errors_xml_*.json
fi
```

### 3. JSON-Diff bei Updates

```bash
# Altes JSON sichern
cp output/biw_data_xml_12-50.json output/biw_data_xml_12-50.json.backup

# Neu konvertieren
python wordpress_xml_converter.py wordpress-export-neu.xml

# Diff checken
diff <(jq -S . output/biw_data_xml_12-50.json.backup) \
     <(jq -S . output/biw_data_xml_12-50.json)
```

---

**Version:** 1.0  
**Date:** 2026-02-07  
**Status:** Production-Ready ✅  
**Preferred Method:** XML Converter (schneller, vollständiger)
