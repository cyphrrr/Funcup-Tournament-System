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

# Discord-Limits
FIELD_LIMIT = 1024          # max. Zeichen pro Field-Value
MAX_FIELDS = 25             # max. Fields pro Embed
EMBED_CHAR_LIMIT = 5500     # Puffer unter Discords 6000-Gesamtlimit


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


def _split_field(name: str, lines: list) -> list[tuple[str, str]]:
    """
    Wandelt Zeilen in ein oder mehrere (name, value)-Fields um und splittet
    bei Überlänge (> FIELD_LIMIT Zeichen).
    """
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

    fields = []
    for i, chunk in enumerate(chunks, 1):
        field_name = name if len(chunks) == 1 else f"{name} ({i}/{len(chunks)})"
        fields.append((field_name, "```\n" + chunk + "\n```"))
    return fields


def build_spielplan_embeds(season: dict, groups_data: list, selection: str,
                           user: discord.Member) -> list[discord.Embed]:
    """
    Baut ein oder mehrere Discord Embeds mit dem Spielplan.

    Ein Embed hat harte Grenzen (max. 25 Fields, max. 6000 Zeichen). Bei
    „Alle Gruppen" werden die Fields daher auf mehrere Embeds verteilt.

    Args:
        season: Season-Dict mit name, id
        groups_data: Response von /groups-with-teams
        selection: Gruppenname oder ALL_GROUPS ("__all__")
        user: Discord Member der den Command ausgelöst hat

    Returns:
        Liste von Embeds (mind. eines).
    """
    all_groups = selection == ALL_GROUPS
    title_suffix = "" if all_groups else f" · Gruppe {selection}"
    base_title = f"🏆 BIW Pokal — {season['name']} · Spielplan{title_suffix}"
    footer = f"Angefordert von {user.display_name} via /spielplan"

    if all_groups:
        selected = sorted(groups_data, key=lambda g: g["group"]["name"])
    else:
        selected = [g for g in groups_data if g["group"]["name"] == selection]

    # 1) Flache Field-Liste (name, value) bauen
    fields: list[tuple[str, str]] = []
    for group in selected:
        group_name = group["group"]["name"]
        by_matchday = _matchday_lines(group.get("matches", []))
        for md in sorted(by_matchday.keys()):
            if all_groups:
                field_name = f"📋 Gruppe {group_name} · Spieltag {md}"
            else:
                field_name = f"Spieltag {md}"
            fields.extend(_split_field(field_name, by_matchday[md]))

    if not fields:
        embed = discord.Embed(title=base_title, color=discord.Color.gold())
        embed.description = "Für diese Auswahl ist noch kein Spielplan vorhanden."
        embed.set_footer(text=footer)
        return [embed]

    # 2) Fields in Embeds packen (Field-Anzahl UND Zeichen-Gesamtlimit beachten)
    embeds: list[discord.Embed] = []
    current: discord.Embed | None = None
    current_chars = 0
    for name, value in fields:
        cost = len(name) + len(value)
        if (current is None
                or len(current.fields) >= MAX_FIELDS
                or current_chars + cost > EMBED_CHAR_LIMIT):
            current = discord.Embed(title=base_title, color=discord.Color.gold())
            embeds.append(current)
            current_chars = len(base_title)
        current.add_field(name=name, value=value, inline=False)
        current_chars += cost

    # 3) Seitenzahl (nur bei mehreren) + Footer setzen
    total = len(embeds)
    for i, embed in enumerate(embeds, 1):
        if total > 1:
            embed.title = f"{base_title} ({i}/{total})"
        embed.set_footer(text=footer)

    return embeds


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
        embeds = build_spielplan_embeds(
            self.season, self.groups_data, selection, interaction.user
        )

        # Menü schließen / bestätigen. Interaction-Response braucht keine
        # channel.send-Rechte.
        await interaction.response.edit_message(
            content="✅ Spielplan gepostet!", view=None
        )

        # Öffentlich posten via Interaction-Followup statt channel.send:
        # Followups laufen über den Interaction-Webhook und funktionieren auch
        # in Channels, in denen der Bot keine normalen "Send Messages"-Rechte
        # hat (verhindert 403 Missing Access).
        try:
            for embed in embeds:
                await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"❌ Fehler beim Posten des Spielplans: {e}", exc_info=e)
            await interaction.followup.send(
                content=f"❌ Konnte den Spielplan nicht posten: {e}",
                ephemeral=True
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
