"""
Gruppen Cog - Zeigt alle Gruppen der aktuellen/geplanten Saison mit ihren Teams.
/gruppen - Postet die Gruppen-Zusammensetzung öffentlich im Channel.

Nutzen: Überblick über die Gruppen, sobald die Auslosung gelaufen ist.
Berechtigung: Nur User mit Rolle "Organisation" oder "Teilnehmer".
"""

import logging
import discord
from discord.ext import commands

from utils.api_client import BackendAPIClient

logger = logging.getLogger('biw-bot.gruppen')

# Rollen die /gruppen nutzen dürfen (case-insensitive Vergleich)
ALLOWED_ROLES = {"organisation", "teilnehmer"}


def has_permission(member: discord.Member) -> bool:
    """Prüft ob Member eine der erlaubten Rollen hat."""
    return any(role.name.lower() in ALLOWED_ROLES for role in member.roles)


def resolve_season(seasons: list) -> dict | None:
    """
    Wählt die anzuzeigende Saison: erst die aktive, sonst die geplante.

    Returns:
        Season-Dict oder None wenn weder aktive noch geplante Saison existiert.
    """
    active = next((s for s in seasons if s.get("status") == "active"), None)
    if active:
        return active
    return next((s for s in seasons if s.get("status") == "planned"), None)


def build_gruppen_embed(season: dict, groups_data: list, user: discord.Member) -> discord.Embed:
    """
    Baut ein Discord Embed mit allen Gruppen und ihren Teams.

    Args:
        season: Season-Dict mit name, id
        groups_data: Response von /groups-with-teams
        user: Discord Member der den Command ausgelöst hat
    """
    embed = discord.Embed(
        title=f"🏆 BIW Pokal — {season['name']} · Gruppen",
        color=discord.Color.gold()
    )

    total_teams = sum(len(g.get("teams", [])) for g in groups_data)
    embed.description = f"{len(groups_data)} Gruppen · {total_teams} Teams"

    # Noch keine Teams zugelost -> Hinweis statt leerer Felder
    if total_teams == 0:
        embed.description = (
            "Die Gruppen stehen, aber es sind noch keine Teams zugelost.\n"
            "Auslosung noch nicht erfolgt."
        )
        return embed

    for group in sorted(groups_data, key=lambda g: g["group"]["name"]):
        group_name = group["group"]["name"]
        teams = group.get("teams", [])

        if teams:
            team_lines = "\n".join(t["name"] for t in teams)
            value = "```\n" + team_lines + "\n```"
        else:
            value = "_noch keine Teams_"

        embed.add_field(
            name=f"📋 Gruppe {group_name} ({len(teams)})",
            value=value,
            inline=True
        )

    embed.set_footer(text=f"Angefordert von {user.display_name} via /gruppen")
    return embed


class Gruppen(commands.Cog):
    """Cog für /gruppen Command — postet die Gruppen-Zusammensetzung."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.api = BackendAPIClient()
        logger.info('✅ Gruppen Cog geladen')

    @discord.slash_command(
        name="gruppen",
        description="Zeigt alle Gruppen der aktuellen Saison mit ihren Teams"
    )
    async def gruppen(self, ctx: discord.ApplicationContext):
        """
        Slash Command: /gruppen
        Postet die Gruppen-Zusammensetzung der aktiven (sonst geplanten) Saison
        öffentlich im Channel.

        Berechtigung: Nur Rollen "Organisation" oder "Teilnehmer".
        """
        if not has_permission(ctx.author):
            await ctx.respond(
                "❌ Du brauchst die Rolle **Organisation** oder **Teilnehmer** "
                "um diesen Befehl zu nutzen.",
                ephemeral=True
            )
            return

        await ctx.defer()  # Öffentlich

        logger.info(f'👤 {ctx.author.name} ruft /gruppen auf')

        seasons = await self.api.get_seasons()
        season = resolve_season(seasons)

        if not season:
            await ctx.followup.send(
                "❌ Aktuell ist kein Pokal geplant. Keine aktive oder geplante Saison gefunden."
            )
            return

        groups_data = await self.api.get_groups_with_teams(season["id"])

        if not groups_data:
            await ctx.followup.send(
                f"❌ Für **{season['name']}** wurden noch keine Gruppen erstellt."
            )
            return

        embed = build_gruppen_embed(season, groups_data, ctx.author)
        await ctx.followup.send(embed=embed)

        logger.info(f'✅ Gruppen gepostet für {season["name"]} ({len(groups_data)} Gruppen)')


def setup(bot: commands.Bot):
    bot.add_cog(Gruppen(bot))
