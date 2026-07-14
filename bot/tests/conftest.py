"""Pytest-Konfiguration für Bot-Tests.

Fügt das bot/-Verzeichnis zum Import-Pfad hinzu, damit `cogs.*` und `utils.*`
wie zur Laufzeit importierbar sind.
"""

import os
import sys

BOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BOT_DIR not in sys.path:
    sys.path.insert(0, BOT_DIR)
