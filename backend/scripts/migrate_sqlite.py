import sqlite3
import sys

def migrate():
    """Make discord_id nullable in SQLite user_profiles table."""
    db_path = 'biw.db'
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if migration already applied
        cursor.execute("PRAGMA table_info(user_profiles)")
        columns = cursor.fetchall()
        discord_id_col = next((c for c in columns if c[1] == 'discord_id'), None)

        if not discord_id_col or discord_id_col[3] == 0:  # 3 = notnull, 0 = nullable
            print("discord_id already nullable, skipping migration")
            conn.close()
            return True

        print("Migrating user_profiles table...")

        # Rename old table
        cursor.execute("ALTER TABLE user_profiles RENAME TO user_profiles_old")

        # Create new table with nullable discord_id
        cursor.execute("""
            CREATE TABLE user_profiles (
                id INTEGER PRIMARY KEY,
                discord_id VARCHAR UNIQUE,
                discord_username VARCHAR,
                discord_avatar_url VARCHAR,
                team_id INTEGER,
                profile_url VARCHAR,
                participating_next BOOLEAN DEFAULT 1,
                crest_url VARCHAR,
                access_token TEXT,
                refresh_token TEXT,
                token_expires_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(team_id) REFERENCES teams(id)
            )
        """)

        # Copy data
        cursor.execute("""
            INSERT INTO user_profiles
            SELECT * FROM user_profiles_old
        """)

        # Drop old table
        cursor.execute("DROP TABLE user_profiles_old")

        conn.commit()
        conn.close()
        print("Migration successful!")
        return True
    except Exception as e:
        print(f"Migration failed: {e}")
        return False

if __name__ == '__main__':
    success = migrate()
    sys.exit(0 if success else 1)
