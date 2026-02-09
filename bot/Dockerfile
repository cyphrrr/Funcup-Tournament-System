# Discord Bot Dockerfile
FROM python:3.11-slim

# Arbeitsverzeichnis erstellen
WORKDIR /app

# Non-root User erstellen für Security
RUN useradd -m -u 1000 botuser && chown -R botuser:botuser /app

# Dependencies installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bot-Code kopieren
COPY . .

# Zu Non-root User wechseln
USER botuser

# Healthcheck (optional) - prüft ob Python-Prozess läuft
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD pgrep -f "python main.py" || exit 1

# Bot starten
CMD ["python", "-u", "main.py"]
