# Dashboard Deployment – Schritt für Schritt

## Übersicht

Neue Datei: `dashboard.html` – Self-Service Portal mit Discord OAuth2 Login
Bot-Fix: `/wappen` Command-Link korrigieren

---

## Schritt 1: dashboard.html deployen

```bash
# Datei ins Frontend-Verzeichnis kopieren
cp dashboard.html ~/funcup/frontend/dashboard.html

# Prüfen ob die Datei da ist
ls -la ~/funcup/frontend/dashboard.html
```

Nginx braucht keinen Restart – statische Dateien werden direkt aus dem gemounteten Volume ausgeliefert.

**Test:** https://beta.biw-pokal.de/dashboard.html → Login-Screen sollte erscheinen.

---

## Schritt 2: Bot-Link in profil.py fixen

Datei: `~/funcup/bot/cogs/profil.py` (ca. Zeile 174)

**Vorher:**
```python
upload_url = f'{dashboard_url}/dashboard/wappen'
```

**Nachher:**
```python
upload_url = f'{dashboard_url}/dashboard.html'
```

Bot neu starten:
```bash
cd ~/funcup
docker compose restart bot
docker compose logs -f bot  # Prüfen ob sauber startet
```

---

## Schritt 3: OAuth2 Callback anpassen (Backend)

Der aktuelle Callback in `api.py` (Zeile ~1808) gibt JSON zurück.
Für das Frontend-Redirect muss er stattdessen zu `dashboard.html?token=<jwt>` weiterleiten.

Datei: `~/funcup/backend/app/api.py`

Im OAuth2-Callback-Handler (Funktion die `/api/auth/discord/callback` bedient):

**Vorher** (gibt JSON zurück):
```python
return {"access_token": token, "user": user_data}
```

**Nachher** (Redirect zum Dashboard):
```python
from fastapi.responses import RedirectResponse

# redirect_uri aus Query-Param oder Fallback
redirect_to = request.query_params.get("redirect", "/dashboard.html")
# Sicherstellen dass nur relative Pfade oder eigene Domain
if not redirect_to.startswith("/") and "biw-pokal.de" not in redirect_to:
    redirect_to = "/dashboard.html"

return RedirectResponse(url=f"{redirect_to}?token={token}")
```

**Wichtig:** Der `state`-Parameter im OAuth2-Flow muss den `redirect`-Wert durchreichen. Aktuell wird `state` für CSRF genutzt. Eine Möglichkeit:

```python
# Im Login-Endpoint (/api/auth/discord/login):
import json, secrets

redirect = request.query_params.get("redirect", "/dashboard.html")
state_data = {"csrf": secrets.token_urlsafe(32), "redirect": redirect}
state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()
# state in Session/Memory speichern + an Discord OAuth URL anhängen

# Im Callback-Endpoint:
state_data = json.loads(base64.urlsafe_b64decode(state).decode())
# CSRF prüfen, dann redirect nutzen
redirect_to = state_data.get("redirect", "/dashboard.html")
```

Backend neu starten:
```bash
cd ~/funcup
docker compose up -d --build backend
```

---

## Schritt 4: Discord Developer Portal prüfen

Sicherstellen dass die Redirect-URI eingetragen ist:

```
https://beta.biw-pokal.de/api/auth/discord/callback
```

Portal: https://discord.com/developers/applications → Deine App → OAuth2 → Redirects

---

## Schritt 5: Testen

1. **Login-Screen:** https://beta.biw-pokal.de/dashboard.html öffnen
2. **Discord Login:** Auf Button klicken → Discord-Autorisierung → Redirect zurück mit Token
3. **Profil laden:** Dashboard zeigt Avatar, Name, Teilnahme-Status
4. **Teilnahme togglen:** Schalter umlegen → Toast "Du bist dabei!"
5. **Profil-URL setzen:** URL eingeben + Speichern
6. **Wappen hochladen:** Bild auswählen → Preview erscheint
7. **Team claimen:** Suche eingeben → Team klicken → Bestätigen
8. **Bot-Link testen:** Im Discord `/wappen` → Link führt zum Dashboard

---

## Bekannte Voraussetzungen

- OAuth2 Env-Vars müssen in `.env` gesetzt sein:
  - `DISCORD_CLIENT_ID`
  - `DISCORD_CLIENT_SECRET`  
  - `DISCORD_REDIRECT_URI=https://beta.biw-pokal.de/api/auth/discord/callback`
  - `JWT_SECRET`
- Der `/api/teams/search` Endpoint muss existieren (für Team-Claim)
- Der `/api/discord/users/{id}/claim-team` Endpoint muss existieren
