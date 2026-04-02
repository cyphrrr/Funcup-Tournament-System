"""
Aktuell Cog - Zeigt den aktuellen Anmeldestand für den nächsten Pokal
/aktuell - Postet Übersicht der angemeldeten Teams öffentlich im Channel
"""

import logging
import discord
from discord.ext import commands

from utils.api_client import BackendAPIClient

logger = logging.getLogger('biw-bot.aktuell')


class Aktuell(commands.Cog):
    """Cog für /aktuell Command — zeigt Anmeldestand."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.api = BackendAPIClient()
        logger.info('✅ Aktuell Cog geladen')

    @discord.slash_command(
        name="aktuell",
        description="Zeigt den aktuellen Anmeldestand für den nächsten BIW Pokal"
    )
    async def aktuell(self, ctx: discord.ApplicationContext):
        await ctx.defer()  # Öffentlich, kein ephemeral

        logger.info(f'👤 {ctx.author.name} ruft /aktuell auf')

        # 1. Participation Report laden
        report = await self.api.get_participation_report()

        if not report:
            await ctx.followup.send(
                "❌ Fehler beim Laden der Anmeldedaten. Bitte versuche es später erneut."
            )
            return

        # 2. Daten aufbereiten
        participating = report.get("participating", [])

        teams_with_name = sorted(
            [p["team_name"] for p in participating if p.get("team_name")],
            key=str.lower
        )
        without_team_count = sum(1 for p in participating if not p.get("team_name"))

        # 3. Embed bauen
        embed = discord.Embed(
            title="🏆 BIW Pokal — Anmeldestand",
            color=discord.Color.gold()
        )

        if teams_with_name:
            description = f"📊 **{len(teams_with_name)} Teams** sind dabei"
            if without_team_count > 0:
                description += f"\n👤 + {without_team_count} weitere Teilnehmer ohne Team"
            embed.description = description

            # Teamnamen als kommaseparierten String
            team_str = ", ".join(teams_with_name)

            # Discord Field Limit = 1024 Zeichen
            if len(team_str) <= 1024:
                embed.add_field(
                    name="✅ Teams",
                    value=team_str,
                    inline=False
                )
            else:
                # Auf mehrere Fields aufteilen
                chunks = []
                current_chunk = ""
                for name in teams_with_name:
                    addition = name if not current_chunk else f", {name}"
                    if len(current_chunk) + len(addition) > 1000:
                        chunks.append(current_chunk)
                        current_chunk = name
                    else:
                        current_chunk += addition
                if current_chunk:
                    chunks.append(current_chunk)

                for i, chunk in enumerate(chunks, 1):
                    label = f"✅ Teams ({i}/{len(chunks)})" if len(chunks) > 1 else "✅ Teams"
                    embed.add_field(name=label, value=chunk, inline=False)

        elif without_team_count > 0:
            embed.description = (
                f"👤 {without_team_count} Teilnehmer angemeldet, "
                "aber noch kein Team verknüpft.\n\n"
                "Team verknüpfen: `/claim <teamname>`"
            )
        else:
            embed.description = (
                "Noch keine Anmeldungen.\n\n"
                "Melde dich mit `/dabei ja` an!"
            )

        embed.set_footer(text="Teilnahme melden: /dabei ja")

        await ctx.followup.send(embed=embed)
        logger.info(
            f'✅ Anmeldestand gepostet: {len(teams_with_name)} Teams, '
            f'{without_team_count} ohne Team'
        )


def setup(bot):
    bot.add_cog(Aktuell(bot))
