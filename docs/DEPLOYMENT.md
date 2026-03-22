# BIW Pokal - Deployment Guide

Produktions-Deployment mit Docker Compose auf einem Root-Server.

---

## 🚀 Schnellstart

```bash
# 1. Repository klonen
git clone <dein-repo> /var/www/biw-pokal
cd /var/www/biw-pokal

# 2. Environment konfigurieren
cp .env.example .env
nano .env  # Passwörter ändern!

# 3. Starten
docker-compose up -d

# 4. Logs prüfen
docker-compose logs -f
```

**Fertig!**
- Frontend: `http://deine-domain.de`
- Backend API: `http://deine-domain.de/api`
- n8n: `http://deine-domain.de:5678`

---

## 📋 Voraussetzungen

### Server
- Linux (Ubuntu 22.04 / Debian 11 empfohlen)
- 2 GB RAM minimum (4 GB empfohlen)
- 20 GB Speicher
- Root-Zugriff

### Software
```bash
# Docker installieren
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Docker Compose installieren (falls nicht dabei)
apt install docker-compose-plugin

# Prüfen
docker --version
docker compose version
```

---

## 🔧 Setup Schritt für Schritt

### 1. Server vorbereiten

```bash
# Updates installieren
apt update && apt upgrade -y

# Firewall konfigurieren
ufw allow 22    # SSH
ufw allow 80    # HTTP
ufw allow 443   # HTTPS
ufw enable

# Optional: Non-root User erstellen
adduser biw
usermod -aG docker biw
su - biw
```

### 2. Projekt hochladen

**Option A: Git**
```bash
cd /var/www
git clone <dein-repo> biw-pokal
cd biw-pokal
```

**Option B: SCP/SFTP**
```bash
# Lokal:
scp -r biw-pokal/ user@server:/var/www/
```

### 3. Environment konfigurieren

```bash
cd /var/www/biw-pokal
cp .env.example .env
nano .env
```

**Wichtig: Ändere alle Secrets!**
```bash
ADMIN_PASSWORD=dein-sicheres-passwort
API_KEY=dein-geheimer-api-key-32-zeichen-lang
JWT_SECRET=dein-jwt-secret-mindestens-32-zeichen
N8N_PASSWORD=dein-n8n-passwort
```

### 4. Frontend API-URL anpassen

Für Production musst du die API-URL im Frontend anpassen:

```bash
# In allen HTML-Dateien:
# Von: const API = 'http://127.0.0.1:8000';
# Zu:  const API = '';  (leerer String = relative URLs)

find frontend -name "*.html" -exec sed -i "s|const API = 'http://127.0.0.1:8000'|const API = ''|g" {} \;
```

Oder manuell in:
- `frontend/index.html`
- `frontend/turnier.html`
- `frontend/ko.html`
- `frontend/archiv.html`
- `frontend/admin.html`

### 5. Container starten

```bash
docker-compose up -d
```

**Das startet:**
- ✅ Backend (FastAPI) auf Port 8000
- ✅ Postgres Datenbank
- ✅ Frontend (Nginx) auf Port 80
- ✅ n8n auf Port 5678

### 6. Tabellen initialisieren

Beim ersten Start werden die DB-Tabellen automatisch erstellt (via SQLAlchemy `create_all`).

**Optional: Testdaten einfügen**
```bash
docker-compose exec backend python seed.py
```

### 7. Logs prüfen

```bash
# Alle Services
docker-compose logs -f

# Nur Backend
docker-compose logs -f backend

# Nur Postgres
docker-compose logs -f postgres
```

---

## 🔒 SSL/HTTPS einrichten

### Mit Let's Encrypt (Certbot)

```bash
# Certbot installieren
apt install certbot python3-certbot-nginx

# Zertifikat erstellen
certbot certonly --standalone -d deine-domain.de

# Zertifikate nach ./ssl kopieren
mkdir -p ssl
cp /etc/letsencrypt/live/deine-domain.de/fullchain.pem ssl/cert.pem
cp /etc/letsencrypt/live/deine-domain.de/privkey.pem ssl/key.pem

# nginx.conf anpassen (SSL-Block auskommentieren)
nano nginx.conf

# Container neu starten
docker-compose restart frontend
```

### Auto-Renewal

```bash
# Cronjob für Renewal
crontab -e

# Füge hinzu:
0 0 1 * * certbot renew --quiet && docker-compose restart frontend
```

---

## 🗄️ Datenbank-Backup

### Manuelles Backup

```bash
# Backup erstellen
docker-compose exec postgres pg_dump -U biw_user biw_pokal > backup_$(date +%Y%m%d).sql

# Backup wiederherstellen
docker-compose exec -T postgres psql -U biw_user biw_pokal < backup_20260204.sql
```

### Automatisches Backup

```bash
# Backup-Script erstellen
nano /root/backup-biw.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/biw-pokal"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

cd /var/www/biw-pokal
docker-compose exec -T postgres pg_dump -U biw_user biw_pokal > $BACKUP_DIR/biw_$DATE.sql

# Alte Backups löschen (älter als 30 Tage)
find $BACKUP_DIR -name "biw_*.sql" -mtime +30 -delete
```

```bash
chmod +x /root/backup-biw.sh

# Cronjob (täglich um 2 Uhr)
crontab -e
# Füge hinzu:
0 2 * * * /root/backup-biw.sh
```

---

## 🔄 Updates

```bash
cd /var/www/biw-pokal

# Code aktualisieren
git pull

# Container neu bauen und starten
docker-compose down
docker-compose up -d --build

# Prüfen
docker-compose ps
```

---

## 🗃️ Schema-Migrationen

Nach jedem Deployment, das Model-Änderungen enthält (neue Spalten, Tabellen), **muss** das Migrations-Script ausgeführt werden – **bevor** der Backend-Service neu gestartet wird.

### Wann nötig?

Immer wenn `backend/app/models.py` geändert wurde (neue `Column(...)` Definitionen).

In Dev wird die SQLite-DB bei Schema-Änderungen einfach gelöscht – auf Prod darf das nicht passieren. Das Script holt fehlende Spalten nach, ohne Daten zu verlieren.

### Ausführen

```bash
# Im laufenden Backend-Container:
docker-compose exec backend python scripts/migrate_prod.py

# Oder direkt auf dem Server (außerhalb Docker):
cd backend
python scripts/migrate_prod.py
```

### Beispiel-Ausgabe

```
=======================================================
  BIW Pokal – Produktions-DB Migration
=======================================================

── Pflicht-Migrationen ──────────────────────────────────────
  +  groups.completed  (Gruppe als abgeschlossen markiert)
     → hinzugefügt ✓
  ✓  ko_matches.bracket_type  (Bracket-Zugehörigkeit)

  1 Spalte(n) hinzugefügt, 1 bereits vorhanden.

── Vollständigkeitsprüfung (Model vs. DB) ───────────────────
  ✓  seasons  (5 Spalten)
  ✓  groups  (5 Spalten)
  ...

=======================================================
  Migration abgeschlossen.
=======================================================
```

### Neue Spalten ins Script aufnehmen

Wenn neue Model-Spalten hinzugefügt werden, `REQUIRED_MIGRATIONS` in `backend/scripts/migrate_prod.py` ergänzen:

```python
{
    "table": "tabellen_name",
    "column": "spalten_name",
    "sql": "ALTER TABLE tabellen_name ADD COLUMN IF NOT EXISTS spalten_name TYP DEFAULT wert NOT NULL",
    "description": "kurze Beschreibung",
},
```

Danach auch `EXPECTED_COLUMNS` im gleichen Script aktualisieren.

---

## 📊 Monitoring

### Container-Status

```bash
docker-compose ps
docker stats
```

### Logs ansehen

```bash
# Live-Logs
docker-compose logs -f backend

# Letzte 100 Zeilen
docker-compose logs --tail=100 backend
```

### Health Checks

```bash
# Backend
curl http://localhost:8000/health

# Frontend
curl http://localhost/

# Postgres
docker-compose exec postgres pg_isready -U biw_user
```

---

## 🛠️ Troubleshooting

### Backend startet nicht

```bash
# Logs prüfen
docker-compose logs backend

# Häufige Probleme:
# - DATABASE_URL falsch
# - Postgres noch nicht bereit (warte 10s und versuche neu)
```

### Frontend zeigt keine Daten

```bash
# API-URL im Frontend prüfen
grep "const API" frontend/index.html

# CORS-Fehler? Prüfe Backend-Logs
docker-compose logs backend
```

### Postgres Connection Error

```bash
# Container neu starten
docker-compose restart postgres

# Datenbank prüfen
docker-compose exec postgres psql -U biw_user -d biw_pokal -c "\dt"
```

### n8n startet nicht

```bash
# Logs prüfen
docker-compose logs n8n

# Volume-Permissions prüfen
docker-compose exec n8n ls -la /home/node/.n8n
```

---

## 🚨 Wichtige Hinweise

### Sicherheit

- ✅ **Ändere alle Passwörter** in `.env`
- ✅ **Aktiviere SSL/HTTPS** für Production
- ✅ **Firewall** nur nötige Ports öffnen (22, 80, 443)
- ✅ **Regelmäßige Backups** einrichten
- ✅ **Updates** regelmäßig einspielen

### Performance

- Für mehr als 100 gleichzeitige User: Server-Upgrade auf 4GB RAM
- Postgres-Tuning in `docker-compose.yml` anpassen
- Nginx-Caching aktivieren

### Skalierung

Für High-Traffic:
```yaml
# In docker-compose.yml
backend:
  deploy:
    replicas: 3
```

---

## 📞 Support

Bei Problemen:
1. Logs prüfen: `docker-compose logs -f`
2. Health Checks: `curl http://localhost:8000/health`
3. Container neu starten: `docker-compose restart`
4. GitHub Issues: `<dein-repo>/issues`

---

## 🎉 Fertig!

Dein BIW Pokal läuft jetzt produktiv!

**URLs:**
- 🌐 Frontend: `https://deine-domain.de`
- 🔌 API: `https://deine-domain.de/api`
- 🔐 Admin: `https://deine-domain.de/admin.html`
- 🤖 n8n: `http://deine-domain.de:5678`

---

## Dashboard Deployment

### Übersicht

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
