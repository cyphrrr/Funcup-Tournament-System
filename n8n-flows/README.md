# n8n Flows

Dieses Verzeichnis enthält **exportierte n8n‑Workflows**, die das BIW‑Pokal‑System automatisieren.

## Inhalte

- Saison‑Setup
- Gruppenphase‑Import
- KO‑Phase‑Import
- Ergebnis‑Exporte
- Discord‑Benachrichtigungen

## Prinzipien

- Keine Secrets im Repo
- IDs & Tokens abstrahieren
- Flows sind **referenziell**, nicht environmentspezifisch

---

## Ergebnis‑Import Workflow

Importiert Spielergebnisse von onlineliga.de über `POST /api/matches/import`.

### Node‑Kette

```
Scrape/Fetch → Aggregate → HTTP Request → (optional) IF → Discord Webhook
```

### 1. Vorherige Node (Scrape/Fetch)

Liefert einzelne Items mit diesen Feldern:

| Feld | Beispiel | Beschreibung |
|------|----------|--------------|
| `Heim` | `"VFB_Münster"` | Heim‑Teamname |
| `Gast` | `"FC Honda"` | Gast‑Teamname |
| `Heimtore` | `"2"` | Tore Heim (String) |
| `Gasttore` | `"0"` | Tore Gast (String) |
| `Saison` | `"test"` | Saisonname (case‑insensitive) |
| `Spieltag` | `"SP2"` | Spieltag‑Kennung |

### 2. Aggregate Node

n8n verarbeitet Items einzeln, der Endpoint erwartet ein JSON‑Array.

- **Type**: Aggregate (Transform Data)
- **Operation**: Aggregate All Item Data
- **Output Field Name**: `payload`

### 3. HTTP Request Node

| Setting | Wert |
|---------|------|
| Method | `POST` |
| URL | `https://beta.biw-pokal.de/api/matches/import` |
| Send Headers | Yes |
| Header | `X-API-Key` = (aus Credential) |
| Body Content Type | JSON |
| JSON | `={{ $json.payload }}` |

### Backend‑Verhalten

Das Backend übernimmt die gesamte Validierung:

- **Team‑Auflösung**: Name → ID (case‑insensitive)
- **Swap‑Erkennung**: Vertauschte Heim/Gast werden automatisch korrigiert
- **Filterung**: Unbekannte Teams, fehlende Paarungen und bereits gespielte Matches werden übersprungen
- **Response**: `{ imported, skipped, swapped, errors[] }`

### 4. Optional: IF Node

Bedingung: `{{ $json.imported }} > 0` → Discord‑Webhook nur bei tatsächlichen Imports auslösen.

---

> n8n ist der Orchestrator – nicht die Business‑Logik.
