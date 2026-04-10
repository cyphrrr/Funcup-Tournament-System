#!/usr/bin/env python3
"""
Einmalige Migration: participating_next von UserProfile auf Team übertragen,
dann Spalte von UserProfile entfernen, is_active auf beide Tabellen hinzufügen.

Ausführen auf Production:
  docker exec -it biw-backend python scripts/migrate_participating.py
"""
import os
import sys
import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    PG_USER = os.environ.get("POSTGRES_USER", "biw")
    PG_PASS = os.environ.get("POSTGRES_PASSWORD", "biw")
    PG_DB = os.environ.get("POSTGRES_DB", "biw")
    PG_HOST = os.environ.get("POSTGRES_HOST", "biw-postgres")
    DATABASE_URL = f"postgresql://{PG_USER}:{PG_PASS}@{PG_HOST}:5432/{PG_DB}"

def main():
    print("=" * 55)
    print("  Migration: participating_next → Team")
    print("=" * 55)

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cursor = conn.cursor()

    try:
        # 1. is_active auf teams hinzufügen (falls nicht vorhanden)
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'teams' AND column_name = 'is_active'
        """)
        if not cursor.fetchone():
            print("➕ teams.is_active hinzufügen...")
            cursor.execute("ALTER TABLE teams ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE")
        else:
            print("⏭️  teams.is_active existiert bereits")

        # 2. participating_next auf teams hinzufügen (falls nicht vorhanden)
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'teams' AND column_name = 'participating_next'
        """)
        if not cursor.fetchone():
            print("➕ teams.participating_next hinzufügen...")
            cursor.execute("ALTER TABLE teams ADD COLUMN participating_next BOOLEAN NOT NULL DEFAULT FALSE")
        else:
            print("⏭️  teams.participating_next existiert bereits")

        # 3. Daten migrieren: UserProfile.participating_next → Team.participating_next
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'user_profiles' AND column_name = 'participating_next'
        """)
        if cursor.fetchone():
            print("🔄 Daten migrieren: UserProfile → Team...")
            cursor.execute("""
                UPDATE teams
                SET participating_next = TRUE
                WHERE id IN (
                    SELECT team_id FROM user_profiles
                    WHERE participating_next = TRUE
                    AND team_id IS NOT NULL
                )
                AND participating_next = FALSE
            """)
            migrated = cursor.rowcount
            print(f"   {migrated} Teams auf participating_next=TRUE gesetzt")

            # 4. Spalte von UserProfile entfernen
            print("🗑️  user_profiles.participating_next entfernen...")
            cursor.execute("ALTER TABLE user_profiles DROP COLUMN participating_next")
        else:
            print("⏭️  user_profiles.participating_next existiert nicht mehr (bereits migriert)")

        # 5. is_active auf user_profiles hinzufügen (falls nicht vorhanden)
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'user_profiles' AND column_name = 'is_active'
        """)
        if not cursor.fetchone():
            print("➕ user_profiles.is_active hinzufügen...")
            cursor.execute("ALTER TABLE user_profiles ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE")
        else:
            print("⏭️  user_profiles.is_active existiert bereits")

        conn.commit()
        print("\n✅ Migration erfolgreich!")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ FEHLER: {e}")
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()
