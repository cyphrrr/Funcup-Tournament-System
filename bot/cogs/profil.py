"""
Profil Cog - Commands für User-Profil-Verwaltung
/profil - Onlineliga Profil-URL setzen
/wappen - Link zum Web-Dashboard für Wappen-Upload
"""

import logging
import os
import re
import discord
from discord.ext import commands
from discord import Option

from utils.api_client import BackendAPIClient

logger = logging.getLogger('biw-bot.profil')


class Profil(commands.Cog):
    """Cog für Profil-Verwaltung"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.api = BackendAPIClient()
        logger.info('✅ Profil Cog geladen')

    def _validate_url(self, url: str) -> bool:
        """
        Validiert ob URL gültig ist

        Args:
            url: URL zum Validieren

        Returns:
            True wenn gültige URL, False sonst
        """
        # Einfache URL-Validierung mit Regex
        url_pattern = re.compile(
            r'^https?://'  # http:// oder https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # Domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
            r'(?::\d+)?'  # Port (optional)
            r'(?:/?|[/?]\S+)$',  # Pfad
            re.IGNORECASE
        )
        return url_pattern.match(url) is not None

    @discord.slash_command(
        name="profil",
        description="Onlineliga Profil-URL hinterlegen"
    )
    async def profil(
        self,
        ctx: discord.ApplicationContext,
        url: Option(
            str,
            description="Deine Onlineliga Profil-URL (z.B. https://onlineliga.de/user/123)",
            required=True
        )
    ):
        """
        Slash Command: /profil
        Speichert Onlineliga Profil-URL für User
        """
        await ctx.defer(ephemeral=True)

        discord_id = str(ctx.author.id)

        logger.info(f'👤 {ctx.author.name} setzt Profil-URL: {url}')

        # URL validieren
        if not self._validate_url(url):
            embed = discord.Embed(
                title="❌ Ungültige URL",
                description=(
                    'Die angegebene URL ist nicht gültig.\n\n'
                    '**Beispiel für gültige URL:**\n'
                    '`https://onlineliga.de/user/123456`\n\n'
                    'Stelle sicher, dass die URL mit `http://` oder `https://` beginnt.'
                ),
                color=discord.Color.red()
            )
            await ctx.followup.send(embed=embed, ephemeral=True)
            logger.warning(f'⚠️ Ungültige URL von {ctx.author.name}: {url}')
            return

        # API Call
        success = await self.api.set_profile_url(discord_id, url)

        if success:
            # Erfolgs-Embed
            embed = discord.Embed(
                title="✅ Profil-URL gespeichert",
                description=(
                    f'Deine Onlineliga Profil-URL wurde erfolgreich hinterlegt.\n\n'
                    f'**URL:** {url}\n\n'
                    'Du kannst diese jederzeit mit `/profil <neue-url>` ändern.'
                ),
                color=discord.Color.green()
            )
            embed.set_footer(text=f"User: {ctx.author.name}")

            await ctx.followup.send(embed=embed, ephemeral=True)
            logger.info(f'✅ Profil-URL gespeichert für {ctx.author.name}')
        else:
            # Fehler-Embed
            embed = discord.Embed(
                title="❌ Fehler",
                description=(
                    'Profil-URL konnte nicht gespeichert werden.\n\n'
                    '**Mögliche Gründe:**\n'
                    '• Backend ist nicht erreichbar\n'
                    '• Dein Discord Account ist nicht registriert\n\n'
                    'Bitte kontaktiere einen Admin.'
                ),
                color=discord.Color.red()
            )

            await ctx.followup.send(embed=embed, ephemeral=True)
            logger.error(f'❌ Profil-URL-Speicherung fehlgeschlagen für {ctx.author.name}')

    @discord.slash_command(
        name="wappen",
        description="Link zum Dashboard für Wappen-Upload"
    )
    async def wappen(self, ctx: discord.ApplicationContext):
        """
        Slash Command: /wappen
        Sendet Link zum Web-Dashboard für Wappen-Upload
        """
        await ctx.defer(ephemeral=True)

        logger.info(f'👤 {ctx.author.name} fragt Wappen-Upload-Link ab')

        # Dashboard URL aus Environment oder Default
        dashboard_url = os.getenv('DASHBOARD_URL', 'https://biw-pokal.de')
        upload_url = f'{dashboard_url}/dashboard/wappen'

        # Info-Embed erstellen
        embed = discord.Embed(
            title="🛡️ Team-Wappen hochladen",
            description=(
                'Du kannst dein Team-Wappen über das Web-Dashboard hochladen.\n\n'
                f'**Dashboard-Link:**\n'
                f'🔗 [{dashboard_url}]({upload_url})\n\n'
                '**Anforderungen:**\n'
                '• Format: PNG, JPG oder SVG\n'
                '• Max. Größe: 2 MB\n'
                '• Empfohlene Auflösung: 512x512 px\n'
                '• Quadratisches Format bevorzugt\n\n'
                '**Hinweis:** Du musst im Dashboard eingeloggt sein.'
            ),
            color=discord.Color.blue()
        )

        # Button zum Dashboard
        view = discord.ui.View()
        button = discord.ui.Button(
            label="Zum Dashboard",
            style=discord.ButtonStyle.link,
            url=upload_url,
            emoji="🔗"
        )
        view.add_item(button)

        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.set_footer(text=f"Angefordert von {ctx.author.name}")

        await ctx.followup.send(embed=embed, view=view, ephemeral=True)
        logger.info(f'✅ Wappen-Link gesendet an {ctx.author.name}')


def setup(bot: commands.Bot):
    """Setup-Funktion zum Laden des Cogs"""
    bot.add_cog(Profil(bot))
