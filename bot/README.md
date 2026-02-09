# BIW Pokal Discord Bot

Discord Bot für das BIW Pokal Turniersystem mit Slash Commands für Teilnahme-Management.

## Features

- **Slash Commands** (Guild-spezifisch für schnelles Sync)
- **Teilnahme-Management** (`/dabei`, `/status`)
- **Profil-Verwaltung** (`/profil`, `/wappen`)
- **Async Backend-Kommunikation** via REST API
- **Docker-ready** mit Non-root User
- **Deutschsprachige Responses**

## Tech Stack

- **Framework:** py-cord 2.6+ (moderner Discord.py Fork)
- **HTTP Client:** aiohttp (async)
- **Architecture:** Cog-basiert (modular, erweiterbar)

## Slash Commands

| Command | Parameter | Beschreibung |
|---------|-----------|--------------|
| `/dabei` | `status: ja/nein` | Teilnahme am nächsten Pokal setzen |
| `/status` | - | Zeigt eigene Daten (Teilnahme, Team, Profil-URL) |
| `/profil` | `url: string` | Onlineliga Profil-URL speichern |
| `/wappen` | - | Link zum Web-Dashboard für Wappen-Upload |

## Environment Variables

```bash
# Discord Bot Token (aus Discord Developer Portal)
DISCORD_BOT_TOKEN=dein-bot-token-hier

# Discord Server (Guild) ID für schnelles Command-Sync
DISCORD_GUILD_ID=deine-server-id-hier

# Backend API URL (Docker-intern oder extern)
BACKEND_URL=http://backend:8000

# Dashboard URL für Wappen-Upload Link
DASHBOARD_URL=https://biw-pokal.de
```

## Setup (Lokal)

### 1. Dependencies installieren

```bash
cd bot
pip install -r requirements.txt
```

### 2. Environment konfigurieren

```bash
# .env erstellen (im Root-Verzeichnis)
cp ../.env.example ../.env

# Bot Token eintragen
nano ../.env
```

### 3. Bot starten

```bash
python main.py
```

## Setup (Docker)

### 1. Bot Token in .env setzen

```bash
# Im Root-Verzeichnis
nano .env

# DISCORD_BOT_TOKEN und DISCORD_GUILD_ID setzen
```

### 2. Docker Compose starten

```bash
# Im Root-Verzeichnis
docker-compose up -d bot

# Logs ansehen
docker-compose logs -f bot
```

## Discord Developer Portal Setup

### 1. Bot erstellen

1. Gehe zu https://discord.com/developers/applications
2. Klicke "New Application"
3. Vergib einen Namen (z.B. "BIW Pokal Bot")
4. Navigiere zu "Bot" Tab
5. Klicke "Add Bot"

### 2. Token kopieren

1. Im "Bot" Tab: Klicke "Reset Token"
2. Kopiere den Token
3. Füge ihn in `.env` als `DISCORD_BOT_TOKEN` ein

⚠️ **WICHTIG:** Token niemals öffentlich teilen oder committen!

### 3. Intents aktivieren

Im "Bot" Tab unter "Privileged Gateway Intents":
- ✅ **MESSAGE CONTENT INTENT**
- ✅ **SERVER MEMBERS INTENT**

### 4. Bot einladen

1. Navigiere zu "OAuth2" > "URL Generator"
2. Scopes: `bot`, `applications.commands`
3. Bot Permissions:
   - ✅ Send Messages
   - ✅ Embed Links
   - ✅ Read Message History
4. Kopiere die generierte URL
5. Öffne URL im Browser → Bot zu deinem Server hinzufügen

### 5. Guild ID finden

1. In Discord: Aktiviere "Entwicklermodus" (Einstellungen > App-Einstellungen > Erweitert)
2. Rechtsklick auf deinen Server → "Server-ID kopieren"
3. Füge ID in `.env` als `DISCORD_GUILD_ID` ein

## Projektstruktur

```
bot/
├── Dockerfile              # Container-Image Definition
├── requirements.txt        # Python Dependencies
├── main.py                # Bot Entry Point
├── cogs/                  # Command-Module (Cogs)
│   ├── __init__.py
│   ├── teilnahme.py      # /dabei, /status Commands
│   └── profil.py         # /profil, /wappen Commands
└── utils/                # Utility-Module
    ├── __init__.py
    └── api_client.py     # Async Backend HTTP Client
```

## API Client (Backend-Kommunikation)

Der Bot kommuniziert mit dem FastAPI Backend über REST:

```python
from utils.api_client import BackendAPIClient

api = BackendAPIClient()

# Team-Daten holen
user_data = await api.get_team_by_discord_id("123456789")

# Teilnahme setzen
success = await api.set_participation("123456789", True)

# Profil-URL setzen
success = await api.set_profile_url("123456789", "https://onlineliga.de/user/123")

# User-Status holen
status = await api.get_user_status("123456789")
```

## Cog-Struktur

Cogs sind modulare Command-Gruppen:

```python
import discord
from discord.ext import commands

class MeinCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="test", description="Test-Command")
    async def test(self, ctx: discord.ApplicationContext):
        await ctx.respond("Hallo!")

def setup(bot):
    bot.add_cog(MeinCog(bot))
```

Neue Cogs werden automatisch aus `cogs/` geladen.

## Logging

Der Bot loggt nach stdout (Docker-kompatibel):

```bash
# Docker Logs
docker-compose logs -f bot

# Log Levels
INFO  - Normale Operationen
WARN  - Warnungen (User nicht gefunden, etc.)
ERROR - Fehler (Backend nicht erreichbar, API Errors)
```

## Fehlerbehandlung

### Backend nicht erreichbar

```
❌ Backend nicht erreichbar: http://backend:8000
```

**Lösung:**
- Backend-Container läuft: `docker-compose ps`
- Backend-Health-Check: `curl http://localhost:8000/health`

### Command Sync langsam

Commands brauchen bis zu 1h für globales Sync.

**Lösung:** `DISCORD_GUILD_ID` in `.env` setzen für sofortiges Guild-Sync!

### Token ungültig

```
❌ Login fehlgeschlagen! Token ungültig.
```

**Lösung:**
- Token im Discord Developer Portal neu generieren
- `.env` aktualisieren
- Bot neu starten

## Erweiterung: Neue Commands hinzufügen

### 1. Neues Cog erstellen

```bash
touch bot/cogs/mein_command.py
```

### 2. Cog implementieren

```python
import discord
from discord.ext import commands

class MeinCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="test", description="Mein Test-Command")
    async def test(self, ctx: discord.ApplicationContext):
        await ctx.respond("✅ Test erfolgreich!", ephemeral=True)

def setup(bot):
    bot.add_cog(MeinCommand(bot))
```

### 3. Bot neu starten

```bash
# Docker
docker-compose restart bot

# Lokal
python main.py
```

Commands werden automatisch synchronisiert!

## Production Checklist

- [ ] `DISCORD_BOT_TOKEN` sicher gespeichert (nicht in Git)
- [ ] `DISCORD_GUILD_ID` gesetzt für schnelles Sync
- [ ] Backend API erreichbar (`BACKEND_URL`)
- [ ] Bot Permissions im Discord Server gesetzt
- [ ] Intents aktiviert (Message Content, Server Members)
- [ ] Logging überwacht (`docker-compose logs -f bot`)
- [ ] Healthcheck funktioniert (`docker-compose ps`)

## Support

Bei Problemen:
1. Logs prüfen: `docker-compose logs -f bot`
2. Backend-Health: `curl http://localhost:8000/health`
3. Discord Intents aktiviert?
4. Guild ID korrekt gesetzt?

## Lizenz

Teil des BIW Pokal Projekts.
