#!/bin/bash
# Auto-Version-Bump — wird nach jedem git commit via Claude Code Hook ausgeführt.
# Liest stdin (Hook-JSON), prüft ob ein git commit stattfand, und bumpt die VERSION.
#
# Regeln:
#   feat: oder feat(...)  → MINOR bump (0.9.0 → 0.10.0)
#   alles andere          → PATCH bump (0.9.0 → 0.9.1)
#   release: ...          → übersprungen (verhindert Endlosschleife)

set -e

INPUT=$(cat)
CMD=$(python3 -c "import json,sys; d=json.load(sys.stdin); print(d['tool_input'].get('command',''))" <<< "$INPUT" 2>/dev/null || true)

# Nur bei git commit Befehlen
echo "$CMD" | grep -q 'git commit' || exit 0

# Letzten Commit-Message holen
MSG=$(git log -1 --format=%s 2>/dev/null || true)

# Release-Commits überspringen (kein zweiter Bump)
echo "$MSG" | grep -q '^release:' && exit 0

# VERSION-Datei lesen
VF="VERSION"
if [ ! -f "$VF" ]; then
  echo "[auto-version] VERSION-Datei nicht gefunden, überspringe." >&2
  exit 0
fi

CURRENT=$(cat "$VF" | tr -d '[:space:]')
BASE=$(echo "$CURRENT" | sed 's/-.*//')
MAJOR=$(echo "$BASE" | cut -d. -f1)
MINOR=$(echo "$BASE" | cut -d. -f2)
PATCH=$(echo "$BASE" | cut -d. -f3)
SUFFIX=$(echo "$CURRENT" | grep -oE '\-[a-z]+$' || true)

# Bump-Typ bestimmen
if echo "$MSG" | grep -qE '^feat[:(]'; then
  MINOR=$((MINOR + 1))
  PATCH=0
  BUMP_TYPE="minor"
else
  PATCH=$((PATCH + 1))
  BUMP_TYPE="patch"
fi

NEW="${MAJOR}.${MINOR}.${PATCH}${SUFFIX}"

printf '%s' "$NEW" > "$VF"
git add "$VF"
git commit -m "release: v${NEW}"

echo "[auto-version] ${CURRENT} → ${NEW} (${BUMP_TYPE})"
