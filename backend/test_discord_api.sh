#!/bin/bash
# Test-Script für Discord Bot API Integration
# Usage: ./test_discord_api.sh

set -e

BASE_URL="http://localhost:8000"
API_KEY="biw-n8n-secret-key-change-me"
DISCORD_ID="123456789012345678"

echo "🧪 BIW Pokal - Discord API Tests"
echo "=================================="
echo ""

# Farben für Output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Health Check
echo -e "${YELLOW}Test 1: Health Check${NC}"
curl -s -w "\nStatus: %{http_code}\n" $BASE_URL/health | jq .
echo ""

# Test 2: User registrieren (Admin)
echo -e "${YELLOW}Test 2: User registrieren (Admin)${NC}"
curl -s -X POST $BASE_URL/api/discord/users/register \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -w "\nStatus: %{http_code}\n" \
  -d "{
    \"discord_id\": \"$DISCORD_ID\",
    \"discord_username\": \"TestUser#1234\",
    \"participating_next\": true
  }" | jq .
echo ""

# Test 3: User-Daten abrufen
echo -e "${YELLOW}Test 3: User-Daten abrufen${NC}"
curl -s -w "\nStatus: %{http_code}\n" \
  $BASE_URL/api/discord/users/$DISCORD_ID | jq .
echo ""

# Test 4: Teilnahme auf "ja" setzen
echo -e "${YELLOW}Test 4: Teilnahme setzen (ja)${NC}"
curl -s -X PATCH $BASE_URL/api/discord/users/$DISCORD_ID/participation \
  -H "Content-Type: application/json" \
  -w "\nStatus: %{http_code}\n" \
  -d '{"participating": true}' | jq .
echo ""

# Test 5: Teilnahme auf "nein" setzen
echo -e "${YELLOW}Test 5: Teilnahme setzen (nein)${NC}"
curl -s -X PATCH $BASE_URL/api/discord/users/$DISCORD_ID/participation \
  -H "Content-Type: application/json" \
  -w "\nStatus: %{http_code}\n" \
  -d '{"participating": false}' | jq .
echo ""

# Test 6: Profil-URL setzen
echo -e "${YELLOW}Test 6: Profil-URL setzen${NC}"
curl -s -X PATCH $BASE_URL/api/discord/users/$DISCORD_ID/profile \
  -H "Content-Type: application/json" \
  -w "\nStatus: %{http_code}\n" \
  -d '{"profile_url": "https://onlineliga.de/user/123456"}' | jq .
echo ""

# Test 7: Participation Report (Admin)
echo -e "${YELLOW}Test 7: Participation Report${NC}"
curl -s -H "X-API-Key: $API_KEY" \
  -w "\nStatus: %{http_code}\n" \
  $BASE_URL/api/discord/participation-report | jq .
echo ""

# Test 8: OAuth2 Login URL
echo -e "${YELLOW}Test 8: OAuth2 Login URL${NC}"
curl -s -w "\nStatus: %{http_code}\n" \
  $BASE_URL/api/auth/discord/login | jq .
echo ""

echo -e "${GREEN}✅ Alle Tests abgeschlossen!${NC}"
echo ""
echo "Hinweise:"
echo "- Test 2 schlägt fehl wenn User bereits existiert (erwartet)"
echo "- Test 8 gibt nur URL zurück (kein OAuth2 Flow in Script)"
echo "- Für Wappen-Upload manuell testen (multipart/form-data)"
