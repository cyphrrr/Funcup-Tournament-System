#!/usr/bin/env python3
"""
BIW Pokal Discord Bot
Haupteinstiegspunkt für den Bot mit Slash Commands
"""

import os
import sys
import logging
from pathlib import Path
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Environment Variables laden
load_dotenv()

# Logging konfigurieren (Docker-kompatibel auf stdout)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('biw-bot')

# Discord Intents (benötigte Berechtigungen)
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Bot initialisieren
bot = commands.Bot(
    command_prefix='!',  # Prefix für Text-Commands (optional)
    intents=intents,
    help_command=None  # Default Help Command deaktivieren
)


@bot.event
async def on_ready():
    """Wird ausgeführt wenn Bot bereit ist"""
    logger.info(f'✅ Bot eingeloggt als {bot.user.name} (ID: {bot.user.id})')
    logger.info(f'📊 Verbunden mit {len(bot.guilds)} Server(n)')

    # Slash Commands synchronisieren (Pycord Syntax)
    guild_id = os.getenv('DISCORD_GUILD_ID')
    if guild_id:
        await bot.sync_commands(guild_ids=[int(guild_id)])
        logger.info(f'🔄 Slash Commands synchronisiert für Guild {guild_id}')
    else:
        await bot.sync_commands()
        logger.info('🔄 Slash Commands global synchronisiert (kann bis zu 1h dauern)')

    # Status setzen
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="BIW Pokal Turnier"
        )
    )
    logger.info('✅ Bot ist bereit!')


@bot.event
async def on_application_command_error(ctx: discord.ApplicationContext, error: discord.DiscordException):
    """Globale Error Handler für Slash Commands"""
    logger.error(f'❌ Command Error in /{ctx.command.name}: {error}', exc_info=error)

    # User-freundliche Fehlermeldung
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.respond(
            f'⏱️ Dieser Befehl ist noch auf Cooldown. Versuch es in {error.retry_after:.1f}s erneut.',
            ephemeral=True
        )
    elif isinstance(error, commands.MissingPermissions):
        await ctx.respond(
            '❌ Du hast nicht die benötigten Berechtigungen für diesen Befehl.',
            ephemeral=True
        )
    else:
        await ctx.respond(
            f'❌ Ein Fehler ist aufgetreten: {str(error)}\n'
            'Bitte versuche es später erneut oder kontaktiere einen Admin.',
            ephemeral=True
        )


def load_cogs():
    """Lädt alle Cogs aus dem cogs/ Verzeichnis"""
    cogs_dir = Path(__file__).parent / 'cogs'

    if not cogs_dir.exists():
        logger.warning(f'⚠️ Cogs-Verzeichnis nicht gefunden: {cogs_dir}')
        return

    # Alle .py Dateien im cogs/ Verzeichnis laden
    for cog_file in cogs_dir.glob('*.py'):
        if cog_file.name.startswith('_'):
            continue  # __init__.py überspringen

        cog_name = f'cogs.{cog_file.stem}'
        try:
            bot.load_extension(cog_name)
            logger.info(f'✅ Cog geladen: {cog_name}')
        except Exception as e:
            logger.error(f'❌ Fehler beim Laden von {cog_name}: {e}', exc_info=e)


def main():
    """Hauptfunktion - startet den Bot"""
    # Token aus Environment laden
    token = os.getenv('DISCORD_BOT_TOKEN')

    if not token:
        logger.error('❌ DISCORD_BOT_TOKEN nicht gesetzt in Environment Variables!')
        logger.error('Bitte .env Datei erstellen oder Environment Variable setzen.')
        sys.exit(1)

    # Backend URL validieren
    backend_url = os.getenv('BACKEND_URL', 'http://backend:8000')
    logger.info(f'🔗 Backend URL: {backend_url}')

    # Guild ID optional
    guild_id = os.getenv('DISCORD_GUILD_ID')
    if guild_id:
        logger.info(f'🏰 Guild-spezifische Commands für Guild ID: {guild_id}')
    else:
        logger.warning('⚠️ DISCORD_GUILD_ID nicht gesetzt - Commands werden global synchronisiert (langsam!)')

    # Cogs laden
    logger.info('📦 Lade Cogs...')
    load_cogs()

    # Bot starten
    logger.info('🚀 Starte Bot...')
    try:
        bot.run(token)
    except discord.LoginFailure:
        logger.error('❌ Login fehlgeschlagen! Token ungültig.')
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info('⚠️ Bot wurde durch Tastatur unterbrochen')
        sys.exit(0)
    except Exception as e:
        logger.error(f'❌ Unerwarteter Fehler: {e}', exc_info=e)
        sys.exit(1)


if __name__ == '__main__':
    main()
