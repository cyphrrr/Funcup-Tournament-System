# Discord Integration - Backend API

Dokumentation für Discord Bot Integration, OAuth2 Login und Wappen-Upload.

## Übersicht

Die Discord-Integration besteht aus drei Teilen:

1. **Discord Bot API** - Endpoints für Bot-Commands (`/dabei`, `/status`, `/profil`)
2. **Discord OAuth2** - Web-Dashboard Login via Discord
3. **File Upload** - Wappen-Upload mit Bildverarbeitung

---

## 1. Discord Bot API

### Endpoints

#### GET `/api/discord/users/{discord_id}`

Holt User-Profil anhand Discord ID.

**Auth:** Keine (Public, für Bot)

**Response:**
```json
{
  "id": 1,
  "discord_id": "123456789012345678",
  "discord_username": "Max#1234",
  "discord_avatar_url": "https://cdn.discordapp.com/avatars/...",
  "team_id": 5,
  "team_name": "FC Example",
  "profile_url": "https://onlineliga.de/user/123",
  "participating_next": true,
  "crest_url": "/uploads/crests/123456789012345678.webp",
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z"
}
```

**Status Codes:**
- `200` - OK
- `404` - User nicht gefunden

---

#### PATCH `/api/discord/users/{discord_id}/participation`

Setzt Teilnahme-Status für nächsten Pokal.

**Auth:** Keine (Public, für Bot)

**Body:**
```json
{
  "participating": true
}
```

**Response:** UserProfile (siehe oben)

**Status Codes:**
- `200` - OK
- `404` - User nicht gefunden

**Verwendung:** Discord Bot `/dabei` Command

---

#### PATCH `/api/discord/users/{discord_id}/profile`

Speichert Onlineliga Profil-URL.

**Auth:** Keine (Public, für Bot)

**Body:**
```json
{
  "profile_url": "https://onlineliga.de/user/123456"
}
```

**Response:** UserProfile (siehe oben)

**Status Codes:**
- `200` - OK
- `400` - Ungültige URL
- `404` - User nicht gefunden

**Verwendung:** Discord Bot `/profil` Command

---

#### POST `/api/discord/users/register`

Registriert neuen Discord User.

**Auth:** Admin (Bearer Token oder API-Key)

**Body:**
```json
{
  "discord_id": "123456789012345678",
  "discord_username": "Max#1234",
  "team_id": 5,
  "profile_url": "https://onlineliga.de/user/123",
  "participating_next": true
}
```

**Response:** UserProfile (siehe oben)

**Status Codes:**
- `201` - Created
- `400` - User existiert bereits
- `401` - Nicht autorisiert

---

#### GET `/api/discord/participation-report`

Admin-Report über Teilnahme-Status aller User.

**Auth:** Admin (Bearer Token oder API-Key)

**Response:**
```json
{
  "total_users": 16,
  "participating": 14,
  "not_participating": 2,
  "participation_rate": 87.5,
  "users": [
    { /* UserProfile */ },
    { /* UserProfile */ }
  ]
}
```

**Status Codes:**
- `200` - OK
- `401` - Nicht autorisiert

---

## 2. Discord OAuth2

### Flow

1. User klickt "Mit Discord einloggen"
2. Backend redirect zu Discord Authorization
3. User authorisiert im Discord
4. Discord redirected zurück zu Backend Callback
5. Backend tauscht Code gegen Token, erstellt/updated User
6. Backend gibt JWT Token zurück
7. Frontend speichert JWT Token

### Endpoints

#### GET `/api/auth/discord/login`

Startet OAuth2 Flow.

**Auth:** Keine

**Response:**
```json
{
  "authorization_url": "https://discord.com/api/oauth2/authorize?client_id=..."
}
```

**Usage:**
```javascript
// Frontend
const response = await fetch('/api/auth/discord/login');
const { authorization_url } = await response.json();
window.location.href = authorization_url;  // Redirect zu Discord
```

---

#### GET `/api/auth/discord/callback`

OAuth2 Callback (Discord redirected hierher).

**Auth:** Keine

**Query Parameters:**
- `code` - Authorization Code von Discord
- `state` - CSRF State Token

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "discord_id": "123456789012345678",
    "discord_username": "Max#1234",
    "team_name": "FC Example",
    "participating_next": true
  }
}
```

**Status Codes:**
- `200` - OK
- `400` - Ungültiger State/Code

**Usage:**
```javascript
// Frontend (auf Callback-Seite)
const params = new URLSearchParams(window.location.search);
const code = params.get('code');
const state = params.get('state');

const response = await fetch(`/api/auth/discord/callback?code=${code}&state=${state}`);
const { access_token, user } = await response.json();

// Token speichern
localStorage.setItem('jwt_token', access_token);
```

---

## 3. File Upload (Wappen)

### Endpoints

#### POST `/api/upload/crest`

Wappen hochladen (eigenes Profil).

**Auth:** JWT Bearer Token (eingeloggter User)

**Content-Type:** `multipart/form-data`

**Body:**
- `file` - Bilddatei (PNG, JPG, WebP, max 5MB)

**Response:**
```json
{
  "crest_url": "/uploads/crests/123456789012345678.webp",
  "message": "Wappen erfolgreich hochgeladen"
}
```

**Status Codes:**
- `200` - OK
- `400` - Ungültige Datei
- `401` - Nicht autorisiert
- `404` - User-Profil nicht gefunden

**Verarbeitung:**
- Validiert Dateityp (PNG, JPG, WebP)
- Validiert Dateigröße (max 5MB)
- Resized auf max 512x512px (Aspect Ratio erhalten)
- Konvertiert zu WebP (kleinere Dateigröße)
- Speichert als `{discord_id}.webp`

**Usage:**
```javascript
// Frontend
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const response = await fetch('/api/upload/crest', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${jwt_token}`
  },
  body: formData
});

const { crest_url } = await response.json();
console.log('Wappen URL:', crest_url);
```

---

#### DELETE `/api/upload/crest`

Eigenes Wappen löschen.

**Auth:** JWT Bearer Token

**Response:**
```json
{
  "message": "Wappen erfolgreich gelöscht"
}
```

**Status Codes:**
- `200` - OK
- `401` - Nicht autorisiert
- `404` - Kein Wappen vorhanden

---

#### GET `/api/upload/crest/{discord_id}`

Wappen eines Users abrufen (public).

**Auth:** Keine

**Response:** Redirect zu Bilddatei

**Status Codes:**
- `302` - Redirect zu `/uploads/crests/{discord_id}.webp`
- `404` - Wappen nicht gefunden

---

## Datenbank-Schema

### Tabelle: `user_profiles`

```sql
CREATE TABLE user_profiles (
    id INTEGER PRIMARY KEY,
    discord_id VARCHAR UNIQUE NOT NULL,
    discord_username VARCHAR,
    discord_avatar_url VARCHAR,
    team_id INTEGER REFERENCES teams(id),
    profile_url VARCHAR,
    participating_next BOOLEAN DEFAULT TRUE,
    crest_url VARCHAR,
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_user_profiles_discord_id ON user_profiles(discord_id);
```

---

## Environment Variables

Neue Variablen in `.env`:

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
```

---

## Discord Developer Portal Setup

### 1. Application erstellen

1. Gehe zu https://discord.com/developers/applications
2. "New Application" → Name vergeben
3. Application ID = `DISCORD_CLIENT_ID`

### 2. OAuth2 konfigurieren

1. Tab "OAuth2" → "General"
2. **Client Secret** generieren → `DISCORD_CLIENT_SECRET`
3. **Redirects** hinzufügen:
   - `https://biw-pokal.de/api/auth/discord/callback`
   - `http://localhost:8000/api/auth/discord/callback` (Development)

### 3. Bot hinzufügen (für Bot-Features)

1. Tab "Bot"
2. "Add Bot"
3. Token kopieren → `DISCORD_BOT_TOKEN` (in .env für Bot-Service)

---

## Testing

### 1. User registrieren (Admin)

```bash
curl -X POST http://localhost:8000/api/discord/users/register \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "discord_id": "123456789012345678",
    "discord_username": "TestUser#1234",
    "team_id": 1,
    "participating_next": true
  }'
```

### 2. User-Daten abrufen (Bot)

```bash
curl http://localhost:8000/api/discord/users/123456789012345678
```

### 3. Teilnahme setzen (Bot)

```bash
curl -X PATCH http://localhost:8000/api/discord/users/123456789012345678/participation \
  -H "Content-Type: application/json" \
  -d '{"participating": true}'
```

### 4. Profil-URL setzen (Bot)

```bash
curl -X PATCH http://localhost:8000/api/discord/users/123456789012345678/profile \
  -H "Content-Type: application/json" \
  -d '{"profile_url": "https://onlineliga.de/user/123"}'
```

### 5. OAuth2 Login testen

```bash
# 1. Authorization URL holen
curl http://localhost:8000/api/auth/discord/login

# 2. Im Browser öffnen und einloggen
# 3. Nach Redirect: Code aus URL nehmen

# 4. Callback simulieren
curl "http://localhost:8000/api/auth/discord/callback?code=DEIN_CODE&state=DEIN_STATE"
```

### 6. Wappen hochladen

```bash
# Mit JWT Token
curl -X POST http://localhost:8000/api/upload/crest \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@/path/to/wappen.png"
```

---

## Production Checklist

- [ ] `DISCORD_CLIENT_SECRET` sicher gespeichert
- [ ] `JWT_SECRET` mindestens 32 Zeichen
- [ ] `DISCORD_REDIRECT_URI` auf Production-Domain gesetzt
- [ ] Redirect URI in Discord Developer Portal eingetragen
- [ ] OAuth2 Tokens verschlüsselt in DB (oder kurzlebig)
- [ ] Rate Limiting auf Upload-Endpoint
- [ ] CORS auf Production-Domain beschränkt
- [ ] Upload-Ordner hat korrektes Permissions (www-data)
- [ ] Nginx serviert `/uploads/` direkt (Performance)
- [ ] Backup-Strategy für Uploads

---

## Sicherheit

### OAuth2 State Tokens

- State wird pro Authorization Request generiert
- Nach Callback wird State gelöscht (einmalig verwendbar)
- **TODO Production:** State in Redis statt Memory speichern

### JWT Tokens

- 24h Gültigkeit (konfigurierbar)
- Signiert mit `JWT_SECRET`
- **TODO:** Refresh Token Mechanism implementieren

### Upload Security

- File Type Validation (Extension + MIME Type)
- File Size Limit (5MB)
- Image Verification (PIL öffnet Bild)
- Filenames sind Discord IDs (keine User-Input)
- WebP Konvertierung (verhindert eingebettete Scripts)

### API Rate Limiting

**TODO:** Rate Limiting implementieren für:
- Upload-Endpoint: 5 Requests/Minute
- OAuth Callback: 10 Requests/Minute
- Bot-Endpoints: 100 Requests/Minute

---

## Troubleshooting

### "Token Exchange fehlgeschlagen"

- `DISCORD_CLIENT_ID` und `DISCORD_CLIENT_SECRET` korrekt?
- Redirect URI in Discord Developer Portal eingetragen?
- Code nur einmal verwendbar - bei Retry neuen Code holen

### "User-Profil nicht gefunden"

- User muss zuerst registriert werden via `/api/discord/users/register`
- Discord ID muss exakt übereinstimmen (String, nicht Int)

### "Ungültiges Bild"

- Nur PNG, JPG, WebP erlaubt
- Datei muss gültiges Bild sein (korrupte Dateien werden abgelehnt)
- Max 5MB Dateigröße

### Uploads werden nicht serviert

- `/uploads/` Volume in docker-compose.yml gemountet?
- Upload-Ordner existiert? `mkdir -p uploads/crests`
- Static Files in `main.py` konfiguriert?

---

## Weitere Features (TODO)

- [ ] Refresh Token Flow für OAuth2
- [ ] Revoke Token Endpoint
- [ ] Bulk User Import (CSV)
- [ ] User-Suche (Discord Username)
- [ ] Wappen-Galerie (alle Wappen anzeigen)
- [ ] Default-Wappen bei Nicht-Vorhandensein
- [ ] Image Moderation (NSFW Detection)
- [ ] Wappen-Historie (alte Versionen speichern)
