#!/usr/bin/env python3
"""
Migration: Spalten für Spiel um Platz 3 zu ko_matches hinzufügen.

Fügt hinzu:
  - is_third_place       INTEGER DEFAULT 0
  - loser_next_match_id  INTEGER (nullable, FK auf ko_matches.id)
  - loser_next_match_slot VARCHAR (nullable)

Idempotent: Prüft vor jeder ALTER TABLE ob die Spalte bereits existiert.

Nutzung:
    cd backend
    python scripts/migrate_third_place.py [path/to/biw.db]

    Ohne Argument wird ./biw.db verwendet.
"""

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent / "biw.db"

NEW_COLUMNS = [
    {
        "name": "is_third_place",
        "sql": "ALTER TABLE ko_matches ADD COLUMN is_third_place INTEGER DEFAULT 0",
        "description": "is_third_place INTEGER DEFAULT 0  (1 = Spiel um Platz 3)",
    },
    {
        "name": "loser_next_match_id",
        "sql": "ALTER TABLE ko_matches ADD COLUMN loser_next_match_id INTEGER REFERENCES ko_matches(id)",
        "description": "loser_next_match_id INTEGER  (Verlierer-Weiterleitung für Halbfinale)",
    },
    {
        "name": "loser_next_match_slot",
        "sql": "ALTER TABLE ko_matches ADD COLUMN loser_next_match_slot VARCHAR",
        "description": "loser_next_match_slot VARCHAR  (home | away)",
    },
]


def get_existing_columns(cursor, table: str) -> set[str]:
    cursor.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cursor.fetchall()}


def main() -> None:
    print("=" * 55)
    print("  Migration: ko_matches – Platz-3-Spalten")
    print("=" * 55)

    if not DB_PATH.exists():
        print(f"\nFEHLER: Datenbank nicht gefunden: {DB_PATH}")
        sys.exit(1)

    print(f"\nDatenbank: {DB_PATH}\n")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        existing = get_existing_columns(cursor, "ko_matches")
        added = 0
        skipped = 0

        for col in NEW_COLUMNS:
            if col["name"] in existing:
                print(f"  ✓  {col['description']}  (bereits vorhanden)")
                skipped += 1
            else:
                cursor.execute(col["sql"])
                print(f"  +  {col['description']}  → hinzugefügt ✓")
                added += 1

        if added > 0:
            # is_third_place = 0 für alle bestehenden Matches sicherstellen
            cursor.execute("UPDATE ko_matches SET is_third_place = 0 WHERE is_third_place IS NULL")
            updated = cursor.rowcount
            if updated > 0:
                print(f"\n  {updated} bestehende Match(es): is_third_place auf 0 gesetzt.")

        conn.commit()
        print(f"\n  {added} Spalte(n) hinzugefügt, {skipped} bereits vorhanden.")
        print("\n" + "=" * 55)
        print("  Migration abgeschlossen.")
        print("=" * 55)

    except Exception as e:
        conn.rollback()
        print(f"\nFEHLER: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
