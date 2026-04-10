#!/usr/bin/env python3
"""
BIW Pokal - Produktions-Datenbank Migration Script

Fügt fehlende Spalten hinzu, die im SQLAlchemy-Model definiert sind
aber in einer bestehenden Prod-DB noch nicht vorhanden sind.

Nutzung:
    cd backend
    python scripts/migrate_prod.py

Sicher: Idempotent – mehrfaches Ausführen ist ohne Effekt.
Nur für PostgreSQL. Bei SQLite wird das Script übersprungen.
"""

import sys
import os
from pathlib import Path

# ── .env laden ────────────────────────────────────────────────────────────────

candidates = [
    Path(__file__).parent.parent / ".env",          # backend/.env
    Path(__file__).parent.parent.parent / ".env",   # root/.env
]
env_path = next((p for p in candidates if p.exists()), None)
if not env_path:
    print("WARNUNG: Keine .env gefunden. Gesuchte Pfade:")
    for p in candidates:
        print(f"  {p}")
    print("  Fahre fort mit bestehenden Umgebungsvariablen.\n")
else:
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    # Aus POSTGRES_* Variablen zusammenbauen
    pg_user = os.environ.get("POSTGRES_USER")
    pg_pass = os.environ.get("POSTGRES_PASSWORD")
    pg_host = os.environ.get("POSTGRES_HOST", "localhost")
    pg_port = os.environ.get("POSTGRES_PORT", "5432")
    pg_db   = os.environ.get("POSTGRES_DB")

    missing = [k for k, v in {"POSTGRES_USER": pg_user, "POSTGRES_PASSWORD": pg_pass, "POSTGRES_DB": pg_db}.items() if not v]
    if missing:
        print("ERROR: Keine Datenbankverbindung konfiguriert.")
        print("  Setze entweder DATABASE_URL oder alle POSTGRES_* Variablen in .env:")
        print("    DATABASE_URL=postgresql://user:pass@host:5432/dbname")
        print("  oder:")
        print("    POSTGRES_USER=...")
        print("    POSTGRES_PASSWORD=...")
        print("    POSTGRES_HOST=...  (optional, default: localhost)")
        print("    POSTGRES_PORT=...  (optional, default: 5432)")
        print("    POSTGRES_DB=...")
        print(f"\n  Fehlende Variablen: {', '.join(missing)}")
        sys.exit(1)

    DATABASE_URL = f"postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}"

if not DATABASE_URL.startswith("postgresql"):
    print(f"INFO: DATABASE_URL ist kein PostgreSQL ({DATABASE_URL[:20]}...).")
    print("      Script ist nur für PostgreSQL-Prod-DBs gedacht. Übersprungen.")
    sys.exit(0)

try:
    import psycopg2
except ImportError:
    print("ERROR: psycopg2 nicht installiert.")
    print("       Installiere mit: pip install psycopg2-binary")
    sys.exit(1)

# ── Bekannte Pflicht-Migrationen ──────────────────────────────────────────────
# Diese Spalten existieren im Model aber fehlen auf älteren Prod-DBs.
# Reihenfolge spielt keine Rolle – jede Migration ist unabhängig.

REQUIRED_MIGRATIONS = [
    {
        "table": "groups",
        "column": "completed",
        "sql": "ALTER TABLE groups ADD COLUMN IF NOT EXISTS completed BOOLEAN DEFAULT false NOT NULL",
        "description": "groups.completed  (Gruppe als abgeschlossen markiert)",
    },
    {
        "table": "ko_matches",
        "column": "bracket_type",
        "sql": "ALTER TABLE ko_matches ADD COLUMN IF NOT EXISTS bracket_type VARCHAR DEFAULT 'meister' NOT NULL",
        "description": "ko_matches.bracket_type  (Bracket-Zugehörigkeit: meister/lucky_loser/loser)",
    },
    {
        "table": "ko_matches",
        "column": "is_third_place",
        "sql": "ALTER TABLE ko_matches ADD COLUMN IF NOT EXISTS is_third_place INTEGER DEFAULT 0 NOT NULL",
        "description": "ko_matches.is_third_place  (1 = Spiel um Platz 3)",
    },
    {
        "table": "ko_matches",
        "column": "loser_next_match_id",
        "sql": "ALTER TABLE ko_matches ADD COLUMN IF NOT EXISTS loser_next_match_id INTEGER REFERENCES ko_matches(id)",
        "description": "ko_matches.loser_next_match_id  (Verlierer-Weiterleitung für Halbfinale)",
    },
    {
        "table": "ko_matches",
        "column": "loser_next_match_slot",
        "sql": "ALTER TABLE ko_matches ADD COLUMN IF NOT EXISTS loser_next_match_slot VARCHAR",
        "description": "ko_matches.loser_next_match_slot  (home | away - wohin der Verlierer geht)",
    },
]

# ── Erwartete Spalten pro Tabelle (aus SQLAlchemy-Models) ─────────────────────
# Wird für die Vollständigkeitsprüfung am Ende genutzt.
# Muss bei neuen Model-Spalten gepflegt werden.

EXPECTED_COLUMNS: dict[str, list[str]] = {
    "seasons": [
        "id", "name", "participant_count", "status", "created_at", "sheet_tab_gid",
    ],
    "groups": [
        "id", "season_id", "name", "sort_order", "completed",
    ],
    "teams": [
        "id", "name", "logo_url", "onlineliga_url", "participating_next", "is_active",
    ],
    "season_teams": [
        "id", "season_id", "team_id", "group_id",
    ],
    "matches": [
        "id", "season_id", "group_id", "home_team_id", "away_team_id",
        "home_goals", "away_goals", "status", "matchday", "ingame_week",
    ],
    "news": [
        "id", "title", "content", "author", "published", "created_at",
    ],
    "ko_brackets": [
        "id", "season_id", "bracket_type", "status", "generated_at", "created_at",
    ],
    "ko_matches": [
        "id", "season_id", "bracket_type", "round", "position",
        "home_team_id", "away_team_id", "home_goals", "away_goals",
        "is_bye", "status", "ingame_week", "next_match_id", "next_match_slot",
        "is_third_place", "loser_next_match_id", "loser_next_match_slot",
    ],
    "user_profiles": [
        "id", "discord_id", "discord_username", "discord_avatar_url",
        "team_id", "profile_url", "is_active", "crest_url",
        "access_token", "refresh_token", "token_expires_at",
        "created_at", "updated_at",
    ],
}

# ── Hilfsfunktionen ────────────────────────────────────────────────────────────

def get_existing_columns(cursor, table_name: str) -> set[str]:
    cursor.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        """,
        (table_name,),
    )
    return {row[0] for row in cursor.fetchall()}


def get_existing_tables(cursor) -> set[str]:
    cursor.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        """
    )
    return {row[0] for row in cursor.fetchall()}


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 55)
    print("  BIW Pokal – Produktions-DB Migration")
    print("=" * 55)
    print(f"\nVerbinde mit: {DATABASE_URL[:40]}...\n")

    try:
        conn = psycopg2.connect(DATABASE_URL)
    except Exception as e:
        print(f"FEHLER: Datenbankverbindung fehlgeschlagen: {e}")
        sys.exit(1)

    conn.autocommit = False
    cursor = conn.cursor()
    added = 0
    skipped = 0

    try:
        # ── 1. Bekannte Pflicht-Migrationen ────────────────────────────────
        print("── Pflicht-Migrationen ──────────────────────────────────────")
        for m in REQUIRED_MIGRATIONS:
            existing_cols = get_existing_columns(cursor, m["table"])
            if m["column"] in existing_cols:
                print(f"  ✓  {m['description']}")
                skipped += 1
            else:
                print(f"  +  {m['description']}")
                cursor.execute(m["sql"])
                conn.commit()
                print(f"     → hinzugefügt ✓")
                added += 1

        print(f"\n  {added} Spalte(n) hinzugefügt, {skipped} bereits vorhanden.\n")

        # ── 2. Vollständigkeitsprüfung ─────────────────────────────────────
        print("── Vollständigkeitsprüfung (Model vs. DB) ───────────────────")
        existing_tables = get_existing_tables(cursor)
        warnings: list[str] = []

        for table, expected_cols in EXPECTED_COLUMNS.items():
            if table not in existing_tables:
                warnings.append(f"  ⚠  Tabelle '{table}' existiert nicht in der DB!")
                continue

            existing_cols = get_existing_columns(cursor, table)
            missing = sorted(set(expected_cols) - existing_cols)

            if missing:
                for col in missing:
                    warnings.append(
                        f"  ⚠  {table}.{col}  – im Model definiert, fehlt in der DB"
                    )
            else:
                print(f"  ✓  {table}  ({len(expected_cols)} Spalten)")

        if warnings:
            print("\n── Warnungen ────────────────────────────────────────────────")
            for w in warnings:
                print(w)
            print(
                "\n  HINWEIS: Fehlende Spalten manuell zu REQUIRED_MIGRATIONS hinzufügen"
                "\n           und das Script erneut ausführen."
            )
        else:
            print("\n  Alle Tabellen und Spalten sind vollständig. 🎉")

        print("\n" + "=" * 55)
        print("  Migration abgeschlossen.")
        print("=" * 55)

    except Exception as e:
        conn.rollback()
        print(f"\nFEHLER während Migration: {e}")
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
