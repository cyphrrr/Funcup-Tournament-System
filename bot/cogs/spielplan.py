"""
Spielplan Cog - Zeigt den Spielplan einer Gruppe (oder aller Gruppen).
/spielplan - Zeigt ein Auswahlmenü, postet den gewählten Spielplan öffentlich.

Berechtigung: Nur User mit Rolle "Organisation" oder "Teilnehmer".
"""

import logging
import discord
from discord.ext import commands

from utils.api_client import BackendAPIClient

logger = logging.getLogger('biw-bot.spielplan')

# Rollen die /spielplan nutzen dürfen (case-insensitive Vergleich)
ALLOWED_ROLES = {"organisation", "teilnehmer"}

# Sentinel-Value für die "Alle Gruppen"-Option im Select-Menü
ALL_GROUPS = "__all__"

# Discord-Limit für Field-Werte
FIELD_LIMIT = 1024


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


def format_score(home_goals, away_goals, status: str) -> str:
    """Formatiert den Spielstand; leer bei ungespielten Spielen."""
    if home_goals is not None and away_goals is not None:
        return f"{home_goals} : {away_goals}"
    return "  :  "


def build_group_options(groups_data: list) -> list[discord.SelectOption]:
    """
    Baut die Select-Optionen: "Alle Gruppen" zuoberst, danach je Gruppe eine.

    Returns:
        Liste von SelectOption für das Dropdown-Menü.
    """
    options = [
        discord.SelectOption(
            label="Alle Gruppen",
            value=ALL_GROUPS,
            description="Kompletter Spielplan aller Gruppen",
            emoji="📖",
        )
    ]

    for group in sorted(groups_data, key=lambda g: g["group"]["name"]):
        group_name = group["group"]["name"]
        match_count = len(group.get("matches", []))
        options.append(discord.SelectOption(
            label=f"Gruppe {group_name}",
            value=group_name,
            description=f"{match_count} Spiele",
            emoji="📋",
        ))

    return options


def _matchday_lines(matches: list) -> dict:
    """Gruppiert Match-Zeilen nach Spieltag. Returns {matchday: [zeilen]}."""
    by_matchday: dict = {}
    for m in sorted(matches, key=lambda x: (x.get("matchday") or 0)):
        md = m.get("matchday")
        if md is None:
            continue
        home = m.get("home_team_name", "???")
        away = m.get("away_team_name", "???")
        score = format_score(m.get("home_goals"), m.get("away_goals"), m.get("status", ""))
        status_icon = "" if m.get("status") == "played" else "  ⏳"
        by_matchday.setdefault(md, []).append(f"{home}  {score}  {away}{status_icon}")
    return by_matchday


def _add_lines_field(embed: discord.Embed, name: str, lines: list) -> None:
    """Fügt ein Monospace-Field hinzu und splittet bei Überlänge."""
    chunks = []
    current = ""
    for line in lines:
        addition = line if not current else f"\n{line}"
        # +8 Puffer für die ```-Fences
        if len(current) + len(addition) + 8 > FIELD_LIMIT:
            chunks.append(current)
            current = line
        else:
            current += addition
    if current:
        chunks.append(current)

    for i, chunk in enumerate(chunks, 1):
        field_name = name if len(chunks) == 1 else f"{name} ({i}/{len(chunks)})"
        embed.add_field(name=field_name, value="```\n" + chunk + "\n```", inline=False)


def build_spielplan_embed(season: dict, groups_data: list, selection: str,
                          user: discord.Member) -> discord.Embed:
    """
    Baut ein Discord Embed mit dem Spielplan.

    Args:
        season: Season-Dict mit name, id
        groups_data: Response von /groups-with-teams
        selection: Gruppenname oder ALL_GROUPS ("__all__")
        user: Discord Member der den Command ausgelöst hat
    """
    all_groups = selection == ALL_GROUPS
    title_suffix = "" if all_groups else f" · Gruppe {selection}"
    embed = discord.Embed(
        title=f"🏆 BIW Pokal — {season['name']} · Spielplan{title_suffix}",
        color=discord.Color.gold()
    )

    if all_groups:
        selected = sorted(groups_data, key=lambda g: g["group"]["name"])
    else:
        selected = [g for g in groups_data if g["group"]["name"] == selection]

    has_matches = False
    for group in selected:
        group_name = group["group"]["name"]
        by_matchday = _matchday_lines(group.get("matches", []))
        for md in sorted(by_matchday.keys()):
            has_matches = True
            if all_groups:
                field_name = f"📋 Gruppe {group_name} · Spieltag {md}"
            else:
                field_name = f"Spieltag {md}"
            _add_lines_field(embed, field_name, by_matchday[md])

    if not has_matches:
        embed.description = "Für diese Auswahl ist noch kein Spielplan vorhanden."

    embed.set_footer(text=f"Angefordert von {user.display_name} via /spielplan")
    return embed


class SpielplanSelect(discord.ui.Select):
    """Dropdown-Menü mit den Gruppen-Optionen."""

    def __init__(self, season: dict, groups_data: list,
                 options: list[discord.SelectOption]):
        self.season = season
        self.groups_data = groups_data
        super().__init__(
            placeholder="Welche Gruppe soll ich anzeigen?",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        selection = self.values[0]
        try:
            embed = build_spielplan_embed(
                self.season, self.groups_data, selection, interaction.user
            )
            await interaction.channel.send(embed=embed)
            await interaction.response.edit_message(
                content="✅ Spielplan gepostet!", view=None
            )
        except Exception as e:
            logger.error(f"❌ Fehler beim Posten: {e}", exc_info=e)
            await interaction.response.edit_message(
                content=f"❌ Fehler: {e}", view=None
            )


class SpielplanView(discord.ui.View):
    """View mit dem Spielplan-Select-Menü."""

    def __init__(self, season: dict, groups_data: list,
                 options: list[discord.SelectOption]):
        super().__init__(timeout=60)
        self.add_item(SpielplanSelect(season, groups_data, options))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class Spielplan(commands.Cog):
    """Cog für /spielplan Command — postet den Spielplan öffentlich."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.api = BackendAPIClient()
        logger.info('✅ Spielplan Cog geladen')

    @discord.slash_command(
        name="spielplan",
        description="Zeigt den Spielplan einer Gruppe (oder aller Gruppen)"
    )
    async def spielplan(self, ctx: discord.ApplicationContext):
        """
        Slash Command: /spielplan
        Zeigt ein Auswahlmenü (je Gruppe + "Alle Gruppen"). Nach Auswahl wird
        der Spielplan öffentlich im Channel gepostet.

        Berechtigung: Nur Rollen "Organisation" oder "Teilnehmer".
        """
        if not has_permission(ctx.author):
            await ctx.respond(
                "❌ Du brauchst die Rolle **Organisation** oder **Teilnehmer** "
                "um diesen Befehl zu nutzen.",
                ephemeral=True
            )
            return

        await ctx.defer(ephemeral=True)

        logger.info(f'👤 {ctx.author.name} ruft /spielplan auf')

        seasons = await self.api.get_seasons()
        season = resolve_season(seasons)

        if not season:
            await ctx.followup.send(
                "❌ Aktuell ist kein Pokal geplant. Keine aktive oder geplante Saison gefunden.",
                ephemeral=True
            )
            return

        groups_data = await self.api.get_groups_with_teams(season["id"])

        if not groups_data:
            await ctx.followup.send(
                f"❌ Für **{season['name']}** wurden noch keine Gruppen erstellt.",
                ephemeral=True
            )
            return

        options = build_group_options(groups_data)
        view = SpielplanView(season, groups_data, options)

        await ctx.followup.send(
            f"🏆 **{season['name']}** — Welchen Spielplan willst du sehen?",
            view=view,
            ephemeral=True
        )

        logger.info(f'✅ Spielplan-Menü gesendet für {season["name"]} ({len(options)} Optionen)')


def setup(bot: commands.Bot):
    bot.add_cog(Spielplan(bot))
