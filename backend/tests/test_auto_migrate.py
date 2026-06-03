"""
Tests für die additive Auto-Migration (app.migrations.run_auto_migrations).

Funktioniert gegen eine Datei-SQLite-DB (kein laufender Server nötig).
Simuliert eine "alte" DB, der eine im Modell definierte Spalte fehlt, und
prüft, dass die Migration sie additiv ergänzt — ohne Daten zu verlieren.

Tests:
1. test_fehlende_spalte_wird_ergaenzt: seasons ohne sheet_tab_gid → Spalte da, Zeile erhalten
2. test_idempotent: zweiter Lauf ergänzt nichts und wirft nicht
3. test_keine_aenderung_bei_aktuellem_schema: frische DB → leeres Ergebnis
4. test_daten_bleiben_erhalten: Bestandszeile unverändert, neue Spalte NULL
"""

import sys
import os
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, inspect, text

from app.db import Base
from app import models  # noqa: F401  (registriert die Modelle auf Base)
from app.migrations import run_auto_migrations


def _engine_with_legacy_seasons(path):
    """Erzeugt eine DB mit allen Tabellen, entfernt dann sheet_tab_gid aus seasons
    (so wie die alte Live-DB aussah) und legt eine Bestandszeile an."""
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        # seasons so umbauen, dass sheet_tab_gid fehlt (Legacy-Zustand)
        conn.execute(text("ALTER TABLE seasons RENAME TO seasons_new"))
        conn.execute(text(
            "CREATE TABLE seasons ("
            "id INTEGER PRIMARY KEY, name VARCHAR NOT NULL, "
            "participant_count INTEGER NOT NULL, status VARCHAR, created_at DATETIME)"
        ))
        conn.execute(text(
            "INSERT INTO seasons (id, name, participant_count, status) "
            "VALUES (1, 'Legacy-Saison', 8, 'active')"
        ))
        conn.execute(text("DROP TABLE seasons_new"))
    return engine


def test_fehlende_spalte_wird_ergaenzt():
    with tempfile.TemporaryDirectory() as d:
        engine = _engine_with_legacy_seasons(os.path.join(d, "t.db"))
        cols_before = {c["name"] for c in inspect(engine).get_columns("seasons")}
        assert "sheet_tab_gid" not in cols_before, "Setup-Fehler: Spalte sollte fehlen"

        added = run_auto_migrations(engine)

        cols_after = {c["name"] for c in inspect(engine).get_columns("seasons")}
        assert "sheet_tab_gid" in cols_after, "Spalte wurde nicht ergänzt"
        assert "seasons.sheet_tab_gid" in added
    print("OK test_fehlende_spalte_wird_ergaenzt")


def test_idempotent():
    with tempfile.TemporaryDirectory() as d:
        engine = _engine_with_legacy_seasons(os.path.join(d, "t.db"))
        run_auto_migrations(engine)            # erster Lauf ergänzt
        added_2nd = run_auto_migrations(engine)  # zweiter Lauf darf nichts tun
        assert added_2nd == [], f"Zweiter Lauf sollte leer sein, war {added_2nd}"
    print("OK test_idempotent")


def test_keine_aenderung_bei_aktuellem_schema():
    with tempfile.TemporaryDirectory() as d:
        engine = create_engine(f"sqlite:///{os.path.join(d, 't.db')}",
                               connect_args={"check_same_thread": False})
        Base.metadata.create_all(engine)
        added = run_auto_migrations(engine)
        assert added == [], f"Frisches Schema sollte keine Migration brauchen, war {added}"
    print("OK test_keine_aenderung_bei_aktuellem_schema")


def test_daten_bleiben_erhalten():
    with tempfile.TemporaryDirectory() as d:
        engine = _engine_with_legacy_seasons(os.path.join(d, "t.db"))
        run_auto_migrations(engine)
        with engine.connect() as conn:
            row = conn.execute(text(
                "SELECT name, participant_count, sheet_tab_gid FROM seasons WHERE id=1"
            )).fetchone()
        assert row[0] == "Legacy-Saison"
        assert row[1] == 8
        assert row[2] is None, "Neue Spalte sollte für Bestandszeile NULL sein"
    print("OK test_daten_bleiben_erhalten")


if __name__ == "__main__":
    test_fehlende_spalte_wird_ergaenzt()
    test_idempotent()
    test_keine_aenderung_bei_aktuellem_schema()
    test_daten_bleiben_erhalten()
    print("\nAlle Auto-Migrations-Tests bestanden.")
