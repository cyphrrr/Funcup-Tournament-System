# Discord Backend Integration - Zusammenfassung

Vollständige Backend-Integration für Discord Bot, OAuth2 Login und Wappen-Upload implementiert.

---

## ✅ Implementierte Features

### 1. User Profile System
- **Neues Model:** `UserProfile` mit Discord-ID, Team-Verknüpfung, OAuth2-Tokens
- **Relationships:** User ↔ Team Verknüpfung
- **Timestamps:** Automatisches `created_at` und `updated_at`

### 2. Discord Bot API (6 Endpoints)
- `GET /api/discord/users/{discord_id}` - User-Profil abrufen
- `PATCH /api/discord/users/{discord_id}/participation` - Teilnahme setzen
- `PATCH /api/discord/users/{discord_id}/profile` - Profil-URL setzen
- `POST /api/discord/users/register` - User registrieren (Admin)
- `GET /api/discord/participation-report` - Teilnahme-Report (Admin)

### 3. Discord OAuth2 (2 Endpoints)
- `GET /api/auth/discord/login` - OAuth2 Flow starten
- `GET /api/auth/discord/callback` - OAuth2 Callback Handler
- **Features:**
  - CSRF Protection (State Tokens)
  - Auto-Erstellung/Update von User-Profilen
  - JWT Token Generation für API-Auth
  - Speicherung von Discord Access/Refresh Tokens

### 4. Wappen-Upload (3 Endpoints)
- `POST /api/upload/crest` - Wappen hochladen
- `DELETE /api/upload/crest` - Wappen löschen
- `GET /api/upload/crest/{discord_id}` - Wappen abrufen
- **Verarbeitung:**
  - Validierung (Format, MIME Type, Größe)
  - Auto-Resize (max 512x512px)
  - WebP-Konvertierung (Kompression)
  - EXIF Orientation Fix

---

## 📁 Neue/Geänderte Dateien

### Backend Core
```
backend/
├── requirements.txt                  ✅ ERWEITERT (authlib, pillow, httpx, aiofiles)
├── app/
│   ├── models.py                    ✅ ERWEITERT (UserProfile Model)
│   ├── schemas.py                   ✅ ERWEITERT (Discord/Auth/Upload Schemas)
│   ├── api.py                       ✅ ERWEITERT (15 neue Endpoints)
│   ├── main.py                      ✅ ERWEITERT (Static Files mounting)
│   ├── discord_oauth.py             ✅ NEU (OAuth2 Client)
│   └── image_utils.py               ✅ NEU (Bildverarbeitung)
├── DISCORD_INTEGRATION.md           ✅ NEU (Vollständige API-Doku)
└── test_discord_api.sh              ✅ NEU (Test-Script)
```

### Bot Integration
```
bot/
└── utils/
    └── api_client.py                ✅ ANGEPASST (neue Endpoint-Pfade)
```

### Konfiguration
```
docker-compose.yml                   ✅ ERWEITERT (uploads Volume, OAuth2 Env Vars)
.env.example                         ✅ ERWEITERT (Discord OAuth2, Upload Config)
.gitignore                           ✅ ERWEITERT (uploads/* ignorieren)
```

### Uploads
```
uploads/
├── .gitkeep                         ✅ NEU
└── crests/                          ✅ NEU (Wappen-Ordner)
```

---

## 🔧 Environment Variables

**Neu hinzugefügt in `.env.example`:**

```bash
# Discord OAuth2
DISCORD_CLIENT_ID=deine-application-id
DISCORD_CLIENT_SECRET=dein-client-secret
DISCORD_REDIRECT_URI=https://biw-pokal.de/api/auth/discord/callback

# File Upload
UPLOAD_DIR=/app/uploads
MAX_FILE_SIZE=5242880        # 5MB
CREST_MAX_WIDTH=512
CREST_MAX_HEIGHT=512

# Database (für docker-compose)
POSTGRES_USER=biw_user
POSTGRES_PASSWORD=biw_password_change_me
POSTGRES_DB=biw_pokal
```

---

## 🚀 Deployment-Schritte

### 1. Environment konfigurieren
```bash
# .env erstellen
cp .env.example .env

# Discord OAuth2 Credentials eintragen
nano .env
```

### 2. Dependencies installieren
```bash
cd backend
source .venv/bin/activate  # oder .venv\Scripts\activate (Windows)
pip install -r requirements.txt
```

### 3. Datenbank Migration
```bash
# SQLAlchemy erstellt Tabellen automatisch beim Start
# user_profiles Tabelle wird automatisch angelegt

# Oder manuell via Alembic:
# alembic revision --autogenerate -m "add user_profiles table"
# alembic upgrade head
```

### 4. Services starten
```bash
# Gesamtes System
docker-compose up -d

# Nur Backend neu bauen
docker-compose up -d --build backend

# Logs prüfen
docker-compose logs -f backend
docker-compose logs -f bot
```

---

## 🧪 Testing

### Automatisiert (Test-Script)
```bash
cd backend
./test_discord_api.sh
```

### Manuell via curl

**1. User registrieren:**
```bash
curl -X POST http://localhost:8000/api/discord/users/register \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "discord_id": "123456789012345678",
    "discord_username": "TestUser#1234",
    "participating_next": true
  }'
```

**2. User-Daten abrufen:**
```bash
curl http://localhost:8000/api/discord/users/123456789012345678
```

**3. Teilnahme setzen:**
```bash
curl -X PATCH http://localhost:8000/api/discord/users/123456789012345678/participation \
  -H "Content-Type: application/json" \
  -d '{"participating": true}'
```

**4. Wappen hochladen:**
```bash
# Erst einloggen und JWT Token holen
# Dann:
curl -X POST http://localhost:8000/api/upload/crest \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@wappen.png"
```

---

## 📊 Datenbank-Schema

### Neue Tabelle: `user_profiles`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PRIMARY KEY |
| `discord_id` | VARCHAR | UNIQUE, NOT NULL, INDEXED |
| `discord_username` | VARCHAR | - |
| `discord_avatar_url` | VARCHAR | - |
| `team_id` | INTEGER | FK → teams.id |
| `profile_url` | VARCHAR | - |
| `participating_next` | BOOLEAN | DEFAULT TRUE |
| `crest_url` | VARCHAR | - |
| `access_token` | TEXT | - |
| `refresh_token` | TEXT | - |
| `token_expires_at` | TIMESTAMP | - |
| `created_at` | TIMESTAMP | DEFAULT NOW() |
| `updated_at` | TIMESTAMP | DEFAULT NOW() |

**Relationships:**
- `user_profiles.team_id` → `teams.id` (Many-to-One)

---

## 🔐 Discord Developer Portal Setup

### Application erstellen
1. Gehe zu https://discord.com/developers/applications
2. "New Application" → Name: "BIW Pokal"
3. Kopiere **Application ID** → `DISCORD_CLIENT_ID`

### OAuth2 konfigurieren
1. Tab "OAuth2" → "General"
2. **Client Secret** generieren → `DISCORD_CLIENT_SECRET`
3. **Redirects** hinzufügen:
   - `https://biw-pokal.de/api/auth/discord/callback` (Production)
   - `http://localhost:8000/api/auth/discord/callback` (Dev)

### Bot hinzufügen
1. Tab "Bot" → "Add Bot"
2. **Token** kopieren → `DISCORD_BOT_TOKEN` (für bot/.env)
3. **Intents** aktivieren:
   - ✅ MESSAGE CONTENT INTENT
   - ✅ SERVER MEMBERS INTENT

### Bot einladen
1. Tab "OAuth2" → "URL Generator"
2. **Scopes:** `bot`, `applications.commands`
3. **Permissions:** Send Messages, Embed Links, Read Message History
4. URL kopieren und im Browser öffnen

---

## 🎯 Integration-Flow

### Discord Bot → Backend
```
Discord User tippt /dabei ja
    ↓
Bot ruft /api/discord/users/{id}/participation
    ↓
Backend updated user_profiles.participating_next
    ↓
Bot zeigt Erfolgs-Embed
```

### Web-Dashboard → OAuth2
```
User klickt "Mit Discord einloggen"
    ↓
Frontend holt /api/auth/discord/login
    ↓
Redirect zu Discord Authorization
    ↓
User authorized → Discord redirected zu /callback
    ↓
Backend tauscht Code → Token
    ↓
Backend erstellt/updated UserProfile
    ↓
Backend gibt JWT zurück
    ↓
Frontend speichert JWT, User ist eingeloggt
```

### Wappen-Upload
```
User wählt Bild im Dashboard
    ↓
Frontend sendet multipart/form-data zu /api/upload/crest
    ↓
Backend validiert Datei
    ↓
Backend verarbeitet Bild (resize, WebP)
    ↓
Backend speichert als {discord_id}.webp
    ↓
Backend updated user_profiles.crest_url
    ↓
Frontend zeigt neues Wappen
```

---

## ⚠️ Bekannte TODOs

### Sicherheit
- [ ] OAuth2 State Storage in Redis (statt Memory)
- [ ] Refresh Token Flow implementieren
- [ ] Rate Limiting auf Upload-Endpoint
- [ ] OAuth2 Tokens verschlüsselt speichern
- [ ] CORS auf Production-Domain beschränken

### Features
- [ ] Default-Wappen bei Nicht-Vorhandensein
- [ ] Wappen-Moderation (NSFW Detection)
- [ ] Bulk User Import (CSV)
- [ ] User-Suche im Admin-Panel
- [ ] Wappen-Historie

### Performance
- [ ] Nginx serviert `/uploads/` direkt (schneller)
- [ ] Image Caching Headers
- [ ] Compression für API Responses

---

## 📚 Dokumentation

- **Backend API:** `backend/DISCORD_INTEGRATION.md`
- **Bot README:** `bot/README.md`
- **Project Guide:** `CLAUDE.md`

---

## 🐛 Troubleshooting

### Backend startet nicht
```bash
# Dependencies fehlen?
pip install -r backend/requirements.txt

# Env Vars gesetzt?
cat .env

# Logs prüfen
docker-compose logs backend
```

### Bot findet User nicht
```bash
# User registriert?
curl http://localhost:8000/api/discord/users/DISCORD_ID

# Falls 404: User registrieren
curl -X POST http://localhost:8000/api/discord/users/register \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{"discord_id": "...", "discord_username": "..."}'
```

### OAuth2 fehlschlägt
```bash
# Client ID/Secret korrekt?
echo $DISCORD_CLIENT_ID
echo $DISCORD_CLIENT_SECRET

# Redirect URI in Discord Portal eingetragen?
# Muss EXAKT übereinstimmen!
```

### Upload funktioniert nicht
```bash
# Uploads-Ordner existiert?
ls -la uploads/crests/

# Permissions korrekt?
chmod 755 uploads/crests/

# JWT Token gültig?
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/me
```

---

## ✅ Nächste Schritte

1. **Discord OAuth2 Credentials holen** (Discord Developer Portal)
2. **`.env` konfigurieren** (alle Discord-Variablen setzen)
3. **Services starten** (`docker-compose up -d`)
4. **Test-Script ausführen** (`./backend/test_discord_api.sh`)
5. **User registrieren** (via Admin-Endpoint)
6. **Bot Commands testen** (in Discord: `/dabei`, `/status`)
7. **OAuth2 Flow testen** (Web-Dashboard Login)
8. **Wappen-Upload testen** (nach Login)

---

**Status:** ✅ Backend vollständig implementiert und bereit für Tests!
**Nächster Schritt:** Discord OAuth2 Credentials einrichten + Testing
