#!/usr/bin/env python3
"""
Migration Script: KO-Bracket 3-System
======================================

Fügt hinzu:
1. Neue Tabelle: ko_brackets
2. Neue Spalte: ko_matches.bracket_type
3. Befüllt bestehende KOMatches mit bracket_type = "meister"

Idempotent: Kann mehrfach ausgeführt werden ohne Fehler.
"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from sqlalchemy import create_engine, text, inspect
from app.db import Base, DATABASE_URL
from app.models import KOBracket, KOMatch, Season

def check_column_exists(engine, table_name: str, column_name: str) -> bool:
    """Prüft ob eine Spalte existiert"""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def check_table_exists(engine, table_name: str) -> bool:
    """Prüft ob eine Tabelle existiert"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()

def migrate():
    """Führt die Migration durch"""
    print("🚀 Starte KO-Bracket Migration...")
    print(f"📁 Database: {DATABASE_URL}")

    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # 1. Prüfe ob ko_brackets Tabelle bereits existiert
        if check_table_exists(engine, "ko_brackets"):
            print("✅ Tabelle 'ko_brackets' existiert bereits")
        else:
            print("📝 Erstelle Tabelle 'ko_brackets'...")
            Base.metadata.tables['ko_brackets'].create(engine)
            print("✅ Tabelle 'ko_brackets' erstellt")

        # 2. Prüfe ob ko_matches Tabelle existiert
        if not check_table_exists(engine, "ko_matches"):
            print("ℹ️  Tabelle 'ko_matches' existiert noch nicht - wird beim nächsten Start erstellt")
        else:
            # Prüfe ob bracket_type Spalte existiert
            if check_column_exists(engine, "ko_matches", "bracket_type"):
                print("✅ Spalte 'ko_matches.bracket_type' existiert bereits")
            else:
                print("📝 Füge Spalte 'ko_matches.bracket_type' hinzu...")

                # SQLite: ALTER TABLE ADD COLUMN
                conn.execute(text("""
                    ALTER TABLE ko_matches
                    ADD COLUMN bracket_type VARCHAR NOT NULL DEFAULT 'meister'
                """))
                conn.commit()
                print("✅ Spalte 'ko_matches.bracket_type' hinzugefügt")

            # 3. Befülle bestehende KOMatches mit bracket_type = "meister" (falls vorhanden)
            if check_table_exists(engine, "ko_matches") and check_column_exists(engine, "ko_matches", "bracket_type"):
                result = conn.execute(text("""
                    SELECT COUNT(*) as count
                    FROM ko_matches
                    WHERE bracket_type IS NULL OR bracket_type = ''
                """))
                null_count = result.fetchone()[0]

                if null_count > 0:
                    print(f"📝 Setze bracket_type='meister' für {null_count} bestehende KO-Matches...")
                    conn.execute(text("""
                        UPDATE ko_matches
                        SET bracket_type = 'meister'
                        WHERE bracket_type IS NULL OR bracket_type = ''
                    """))
                    conn.commit()
                    print(f"✅ {null_count} KO-Matches aktualisiert")
                else:
                    print("✅ Alle KO-Matches haben bereits bracket_type gesetzt")

                # 4. Erstelle KOBracket-Einträge für bestehende Saisons mit KO-Matches
                print("📝 Prüfe bestehende Saisons mit KO-Matches...")
                result = conn.execute(text("""
                    SELECT DISTINCT season_id
                    FROM ko_matches
                """))
                season_ids = [row[0] for row in result.fetchall()]

                if season_ids:
                    print(f"   Gefunden: {len(season_ids)} Saison(en) mit KO-Matches")

                    for season_id in season_ids:
                        # Prüfe ob bereits ein Meister-Bracket existiert
                        result = conn.execute(text("""
                            SELECT COUNT(*)
                            FROM ko_brackets
                            WHERE season_id = :sid AND bracket_type = 'meister'
                        """), {"sid": season_id})

                        exists = result.fetchone()[0] > 0

                        if not exists:
                            print(f"   📝 Erstelle Meister-Bracket für Saison {season_id}...")
                            conn.execute(text("""
                                INSERT INTO ko_brackets (season_id, bracket_type, status, created_at)
                                VALUES (:sid, 'meister', 'active', datetime('now'))
                            """), {"sid": season_id})
                            conn.commit()
                            print(f"   ✅ Meister-Bracket erstellt für Saison {season_id}")
                        else:
                            print(f"   ✅ Meister-Bracket existiert bereits für Saison {season_id}")
                else:
                    print("   ℹ️  Keine Saisons mit KO-Matches gefunden")

    print("\n✅ Migration abgeschlossen!")
    print("\n📊 Überprüfung:")

    with engine.connect() as conn:
        # Tabellen-Check
        if check_table_exists(engine, "ko_brackets"):
            result = conn.execute(text("SELECT COUNT(*) FROM ko_brackets"))
            bracket_count = result.fetchone()[0]
            print(f"   - KO-Brackets: {bracket_count}")
        else:
            print(f"   - KO-Brackets: Tabelle existiert noch nicht")

        if check_table_exists(engine, "ko_matches"):
            result = conn.execute(text("SELECT COUNT(*) FROM ko_matches"))
            match_count = result.fetchone()[0]
            print(f"   - KO-Matches: {match_count}")

            if check_column_exists(engine, "ko_matches", "bracket_type"):
                result = conn.execute(text("""
                    SELECT bracket_type, COUNT(*) as count
                    FROM ko_matches
                    GROUP BY bracket_type
                """))
                for row in result.fetchall():
                    print(f"   - Bracket '{row[0]}': {row[1]} Matches")
        else:
            print(f"   - KO-Matches: Tabelle existiert noch nicht")

if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"\n❌ Fehler bei Migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
