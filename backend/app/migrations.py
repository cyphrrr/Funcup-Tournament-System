"""Additive Auto-Migration für bestehende Datenbanken.

Deckt die Lücke, die ``Base.metadata.create_all`` lässt: create_all legt fehlende
*Tabellen* an, aber niemals fehlende *Spalten* in bereits existierenden Tabellen.
Wird beim Start nach create_all aufgerufen, damit Modell-Erweiterungen (neue
Spalten) ohne manuelles ALTER TABLE / ohne Alembic auf der Live-DB landen.

Bewusst nur **additiv** — entfernt oder ändert nie etwas. Fehlende Spalten werden
NULLABLE und ohne server_default ergänzt (SQLite kann via ALTER ADD COLUMN keine
non-constant Defaults wie CURRENT_TIMESTAMP setzen). Python-seitige ``default=``
greifen bei neuen Inserts ohnehin weiter; Bestandszeilen erhalten NULL.
"""

import logging

from sqlalchemy import inspect, text

from .db import Base

logger = logging.getLogger("biw.migrations")


def run_auto_migrations(engine):
    """Ergänzt fehlende Spalten in existierenden Tabellen. Gibt Liste der
    ergänzten ``"tabelle.spalte"``-Namen zurück (leer = nichts zu tun)."""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    dialect = engine.dialect
    added: list[str] = []

    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue  # komplett fehlende Tabellen übernimmt create_all
            db_cols = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in db_cols:
                    continue
                col_type = column.type.compile(dialect=dialect)
                conn.execute(text(
                    f'ALTER TABLE {table.name} ADD COLUMN {column.name} {col_type}'
                ))
                added.append(f"{table.name}.{column.name}")
                logger.warning("Auto-Migration: Spalte ergänzt → %s (%s)",
                               added[-1], col_type)

    if added:
        logger.warning("Auto-Migration abgeschlossen: %d Spalte(n) ergänzt: %s",
                       len(added), ", ".join(added))
    else:
        logger.info("Auto-Migration: keine fehlenden Spalten.")
    return added
