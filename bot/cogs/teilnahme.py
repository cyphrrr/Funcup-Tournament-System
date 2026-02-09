"""
Teilnahme Cog - Commands für Pokal-Teilnahme
/dabei - Teilnahme am nächsten Pokal setzen
/status - Eigene Daten anzeigen
"""

import logging
import discord
from discord.ext import commands
from discord import Option

from utils.api_client import BackendAPIClient

logger = logging.getLogger('biw-bot.teilnahme')


class Teilnahme(commands.Cog):
    """Cog für Teilnahme-Management"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.api = BackendAPIClient()
        logger.info('✅ Teilnahme Cog geladen')

    @discord.slash_command(
        name="dabei",
        description="Teilnahme am nächsten BIW Pokal festlegen"
    )
    async def dabei(
        self,
        ctx: discord.ApplicationContext,
        status: Option(
            str,
            description="Nimmst du am nächsten Pokal teil?",
            choices=["ja", "nein"],
            required=True
        )
    ):
        """
        Slash Command: /dabei
        Setzt Teilnahme-Status für den nächsten Pokal
        """
        await ctx.defer(ephemeral=True)  # Antwort nur für User sichtbar

        discord_id = str(ctx.author.id)
        participating = (status == "ja")

        logger.info(f'👤 {ctx.author.name} setzt Teilnahme: {status}')

        # API Call
        success = await self.api.set_participation(discord_id, participating)

        if success:
            # Erfolgs-Embed
            embed = discord.Embed(
                title="✅ Teilnahme gespeichert",
                description=(
                    f'**Status:** {"✅ Dabei" if participating else "❌ Nicht dabei"}\n\n'
                    'Deine Teilnahme für den nächsten BIW Pokal wurde aktualisiert.'
                ),
                color=discord.Color.green() if participating else discord.Color.red()
            )
            embed.set_footer(text=f"User: {ctx.author.name}")

            await ctx.followup.send(embed=embed, ephemeral=True)
            logger.info(f'✅ Teilnahme gespeichert für {ctx.author.name}: {status}')
        else:
            # Fehler-Embed
            embed = discord.Embed(
                title="❌ Fehler",
                description=(
                    'Teilnahme konnte nicht gespeichert werden.\n\n'
                    '**Mögliche Gründe:**\n'
                    '• Backend ist nicht erreichbar\n'
                    '• Dein Discord Account ist nicht registriert\n\n'
                    'Bitte kontaktiere einen Admin.'
                ),
                color=discord.Color.red()
            )

            await ctx.followup.send(embed=embed, ephemeral=True)
            logger.error(f'❌ Teilnahme-Speicherung fehlgeschlagen für {ctx.author.name}')

    @discord.slash_command(
        name="status",
        description="Zeigt deine aktuellen BIW Pokal Daten an"
    )
    async def status(self, ctx: discord.ApplicationContext):
        """
        Slash Command: /status
        Zeigt User-Status (Teilnahme, Team, Profil-URL, etc.)
        """
        await ctx.defer(ephemeral=True)

        discord_id = str(ctx.author.id)

        logger.info(f'👤 {ctx.author.name} fragt Status ab')

        # API Call
        user_data = await self.api.get_user_status(discord_id)

        if user_data:
            # Status-Embed erstellen
            embed = discord.Embed(
                title=f"📊 Status: {ctx.author.name}",
                color=discord.Color.blue()
            )

            # Team Name
            team_name = user_data.get('name', 'Nicht zugewiesen')
            embed.add_field(
                name="🏆 Team",
                value=team_name,
                inline=False
            )

            # Teilnahme-Status
            participating = user_data.get('participating', False)
            status_text = "✅ Dabei" if participating else "❌ Nicht dabei"
            embed.add_field(
                name="📅 Nächster Pokal",
                value=status_text,
                inline=True
            )

            # Profil-URL
            profile_url = user_data.get('profile_url')
            if profile_url:
                embed.add_field(
                    name="🔗 Onlineliga Profil",
                    value=f"[Zum Profil]({profile_url})",
                    inline=True
                )
            else:
                embed.add_field(
                    name="🔗 Onlineliga Profil",
                    value="Nicht hinterlegt\n`/profil <url>` zum Setzen",
                    inline=True
                )

            # Discord ID (für Debugging)
            embed.add_field(
                name="🆔 Discord ID",
                value=f"`{discord_id}`",
                inline=False
            )

            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            embed.set_footer(text=f"Abgefragt von {ctx.author.name}")

            await ctx.followup.send(embed=embed, ephemeral=True)
            logger.info(f'✅ Status abgerufen für {ctx.author.name}')
        else:
            # User nicht registriert oder Backend-Fehler
            embed = discord.Embed(
                title="❌ Keine Daten gefunden",
                description=(
                    'Dein Discord Account ist noch nicht registriert.\n\n'
                    '**Nächste Schritte:**\n'
                    '1. Stelle sicher, dass du zum BIW Pokal angemeldet bist\n'
                    '2. Kontaktiere einen Admin zur Registrierung\n'
                    '3. Versuche es später erneut\n\n'
                    'Bei anhaltenden Problemen: Backend könnte nicht erreichbar sein.'
                ),
                color=discord.Color.red()
            )

            await ctx.followup.send(embed=embed, ephemeral=True)
            logger.warning(f'⚠️ Keine Daten gefunden für {ctx.author.name} (ID: {discord_id})')


def setup(bot: commands.Bot):
    """Setup-Funktion zum Laden des Cogs"""
    bot.add_cog(Teilnahme(bot))
