#!/bin/bash
# BIW Pokal Release Script
# Verwendung: ./scripts/release.sh [patch|minor|major] [beta|stable]
#
# Beispiele:
#   ./scripts/release.sh patch          → 0.9.0-beta → 0.9.1-beta
#   ./scripts/release.sh minor          → 0.9.1-beta → 0.10.0-beta
#   ./scripts/release.sh patch stable   → 0.10.0-beta → 0.10.1
#   ./scripts/release.sh major stable   → 0.x.y → 1.0.0

set -e

BUMP_TYPE="${1:-patch}"
RELEASE_TYPE="${2:-beta}"
VERSION_FILE="VERSION"

if [ ! -f "$VERSION_FILE" ]; then
  echo "ERROR: VERSION-Datei nicht gefunden!"
  exit 1
fi

CURRENT=$(cat "$VERSION_FILE" | tr -d '[:space:]')
echo "Aktuelle Version: $CURRENT"

# Version parsen (z.B. "0.9.1-beta" → MAJOR=0, MINOR=9, PATCH=1)
BASE_VERSION=$(echo "$CURRENT" | sed 's/-.*//')
MAJOR=$(echo "$BASE_VERSION" | cut -d. -f1)
MINOR=$(echo "$BASE_VERSION" | cut -d. -f2)
PATCH=$(echo "$BASE_VERSION" | cut -d. -f3)

# Bump
case "$BUMP_TYPE" in
  patch) PATCH=$((PATCH + 1)) ;;
  minor) MINOR=$((MINOR + 1)); PATCH=0 ;;
  major) MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0 ;;
  *)
    echo "ERROR: Ungültiger Bump-Typ '$BUMP_TYPE'. Erlaubt: patch, minor, major"
    exit 1
    ;;
esac

# Suffix
if [ "$RELEASE_TYPE" = "stable" ]; then
  NEW_VERSION="${MAJOR}.${MINOR}.${PATCH}"
else
  NEW_VERSION="${MAJOR}.${MINOR}.${PATCH}-beta"
fi

echo "Neue Version:     $NEW_VERSION"
echo ""

# Bestätigung
read -p "Version auf $NEW_VERSION setzen und taggen? (j/n) " CONFIRM
if [ "$CONFIRM" != "j" ]; then
  echo "Abgebrochen."
  exit 0
fi

# VERSION-Datei aktualisieren
echo -n "$NEW_VERSION" > "$VERSION_FILE"

# Commit + Tag
git add "$VERSION_FILE"
git commit -m "release: v${NEW_VERSION}"
git tag -a "v${NEW_VERSION}" -m "Release v${NEW_VERSION}"

echo ""
echo "Version $NEW_VERSION committed und getaggt."
echo ""
echo "Zum Pushen:"
echo "  git push origin main && git push origin v${NEW_VERSION}"
