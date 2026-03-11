"""
Spieltag Cog - Paarungen des aktuellen Spieltags posten
/spieltag - Zeigt Select-Menü, postet Übersicht öffentlich im Channel

Berechtigung: Nur User mit Rolle "Organisation" oder "Teilnehmer"
"""

import logging
import discord
from discord.ext import commands

from utils.api_client import BackendAPIClient

logger = logging.getLogger('biw-bot.spieltag')

# Rollen die /spieltag nutzen dürfen (case-insensitive Vergleich)
ALLOWED_ROLES = {"organisation", "teilnehmer"}


def has_spieltag_permission(member: discord.Member) -> bool:
    """Prüft ob Member eine der erlaubten Rollen hat."""
    return any(role.name.lower() in ALLOWED_ROLES for role in member.roles)


def detect_current_matchday(groups_data: list) -> int | None:
    """
    Ermittelt den aktuellen Spieltag aus den Gruppen-Daten.

    Logik: Höchster matchday der mindestens 1 Ergebnis hat
    aber noch nicht komplett abgeschlossen ist.

    Returns:
        Matchday-Nummer (int) oder None wenn keiner aktuell ist
    """
    matchday_stats = {}  # {1: {"total": 0, "played": 0}, ...}

    for group in groups_data:
        for match in group.get("matches", []):
            md = match.get("matchday")
            if md is None:
                continue
            if md not in matchday_stats:
                matchday_stats[md] = {"total": 0, "played": 0}
            matchday_stats[md]["total"] += 1
            if match.get("status") == "played":
                matchday_stats[md]["played"] += 1

    if not matchday_stats:
        return None

    # Höchster matchday mit ≥1 Ergebnis aber nicht komplett
    for md in sorted(matchday_stats.keys(), reverse=True):
        stats = matchday_stats[md]
        if stats["played"] >= 1 and stats["played"] < stats["total"]:
            return md

    return None


def build_matchday_options(groups_data: list, ko_status: dict) -> list[discord.SelectOption]:
    """
    Baut die Select-Optionen aus Gruppen- und KO-Daten.

    Returns:
        Liste von SelectOption für das Dropdown-Menü
    """
    options = []

    # --- Matchday-Statistik sammeln ---
    matchday_stats = {}
    for group in groups_data:
        for match in group.get("matches", []):
            md = match.get("matchday")
            if md is None:
                continue
            if md not in matchday_stats:
                matchday_stats[md] = {"total": 0, "played": 0}
            matchday_stats[md]["total"] += 1
            if match.get("status") == "played":
                matchday_stats[md]["played"] += 1

    current_md = detect_current_matchday(groups_data)

    # --- Gruppenphase-Optionen ---
    for md in sorted(matchday_stats.keys()):
        stats = matchday_stats[md]
        is_current = (md == current_md)

        emoji = "🔴" if is_current else "📋"
        label = f"Spieltag {md}"
        if is_current:
            label = f"Spieltag {md} (aktuell)"

        description = f"{stats['played']} von {stats['total']} Spielen gespielt"

        options.append(discord.SelectOption(
            label=label,
            value=f"group:{md}",
            description=description,
            emoji=emoji,
            default=is_current
        ))

    # --- KO-Phase-Optionen (nur wenn Brackets existieren) ---
    if ko_status.get("brackets_generated"):
        bracket_labels = {
            "meister": "Meisterrunde",
            "lucky_loser": "Lucky Loser",
            "loser": "Verliererrunde",
        }

        brackets = ko_status.get("brackets", {})
        for bracket_type, label in bracket_labels.items():
            bracket_info = brackets.get(bracket_type)
            if bracket_info is None:
                continue

            played = bracket_info.get("matches_played", 0)
            total = bracket_info.get("matches_total", 0)
            description = f"{played} von {total} Spielen gespielt"

            options.append(discord.SelectOption(
                label=label,
                value=f"ko:{bracket_type}",
                description=description,
                emoji="🥊"
            ))

    return options


def format_score(home_goals, away_goals, status: str) -> str:
    """Formatiert den Spielstand."""
    if home_goals is not None and away_goals is not None:
        return f"{home_goals} : {away_goals}"
    return "  :  "


def build_group_embed(season: dict, matchday: int, groups_data: list, user: discord.Member) -> discord.Embed:
    """
    Baut ein Discord Embed für einen Gruppenphase-Spieltag.

    Args:
        season: Season-Dict mit name, id
        matchday: Spieltag-Nummer (1, 2, 3)
        groups_data: Response von /groups-with-teams
        user: Discord Member der den Command ausgelöst hat
    """
    embed = discord.Embed(
        title=f"🏆 BIW Pokal — {season['name']} · Spieltag {matchday}",
        color=discord.Color.gold()
    )

    # Team-ID → Name Mapping aufbauen
    team_names = {}
    for group in groups_data:
        for team in group.get("teams", []):
            team_names[team["id"]] = team["name"]

    has_matches = False

    for group in sorted(groups_data, key=lambda g: g["group"]["name"]):
        group_name = group["group"]["name"]

        # Matches dieses Spieltags filtern
        matches = [
            m for m in group.get("matches", [])
            if m.get("matchday") == matchday
        ]

        if not matches:
            continue

        has_matches = True
        lines = []

        for m in matches:
            home = team_names.get(m["home_team_id"], "???")
            away = team_names.get(m["away_team_id"], "???")
            score = format_score(m.get("home_goals"), m.get("away_goals"), m.get("status", ""))

            # Status-Indikator
            status_icon = ""
            if m.get("status") != "played":
                status_icon = "  ⏳"

            # Gleichmäßige Formatierung mit Monospace
            lines.append(f"{home}  {score}  {away}{status_icon}")

        field_value = "```\n" + "\n".join(lines) + "\n```"

        embed.add_field(
            name=f"📋 Gruppe {group_name}",
            value=field_value,
            inline=False
        )

    if not has_matches:
        embed.description = "Keine Spiele für diesen Spieltag gefunden."

    embed.set_footer(text=f"Gepostet von {user.display_name} via /spieltag")
    return embed


def build_ko_embed(season: dict, bracket_type: str, brackets_data: dict, user: discord.Member) -> discord.Embed:
    """
    Baut ein Discord Embed für ein KO-Bracket.

    Args:
        season: Season-Dict mit name, id
        bracket_type: "meister", "lucky_loser" oder "loser"
        brackets_data: Response von /ko-brackets
        user: Discord Member der den Command ausgelöst hat
    """
    bracket_titles = {
        "meister": "Meisterrunde",
        "lucky_loser": "Lucky Loser",
        "loser": "Verliererrunde",
    }

    title = bracket_titles.get(bracket_type, bracket_type)

    embed = discord.Embed(
        title=f"🏆 BIW Pokal — {season['name']} · {title}",
        color=discord.Color.gold()
    )

    brackets = brackets_data.get("brackets", {})
    bracket = brackets.get(bracket_type)

    if not bracket:
        embed.description = "Bracket nicht gefunden."
        return embed

    rounds = bracket.get("rounds", {})

    if not rounds:
        embed.description = "Noch keine Spiele in diesem Bracket."
        return embed

    # Runden sortiert ausgeben (runde_1, runde_2, ...)
    for round_key in sorted(rounds.keys()):
        matches = rounds[round_key]

        if not matches:
            continue

        # Runden-Name aus dem ersten Match nehmen
        round_name = matches[0].get("round", round_key)

        lines = []
        for m in matches:
            # Freilos überspringen
            if m.get("is_bye"):
                continue

            home = m.get("home_team", {})
            away = m.get("away_team", {})

            home_name = home.get("name", "TBD") if home else "TBD"
            away_name = away.get("name", "TBD") if away else "TBD"

            score = format_score(m.get("home_goals"), m.get("away_goals"), m.get("status", ""))

            status_icon = ""
            if m.get("status") != "played":
                status_icon = "  ⏳"

            lines.append(f"{home_name}  {score}  {away_name}{status_icon}")

        if not lines:
            continue

        field_value = "```\n" + "\n".join(lines) + "\n```"

        embed.add_field(
            name=f"🥊 {round_name}",
            value=field_value,
            inline=False
        )

    embed.set_footer(text=f"Gepostet von {user.display_name} via /spieltag")
    return embed


class SpieltageSelect(discord.ui.Select):
    """Dropdown-Menü mit Spieltag- und KO-Optionen."""

    def __init__(
        self,
        season: dict,
        groups_data: list,
        ko_brackets_data: dict,
        api: BackendAPIClient,
        select_options: list[discord.SelectOption],
    ):
        self.season = season
        self.groups_data = groups_data
        self.ko_brackets_data = ko_brackets_data
        self.api = api

        super().__init__(
            placeholder="Was willst du sehen?",
            min_values=1,
            max_values=1,
            options=select_options
        )

    async def callback(self, interaction: discord.Interaction):
        choice = self.values[0]
        phase, key = choice.split(":", 1)

        try:
            if phase == "group":
                matchday = int(key)
                embed = build_group_embed(
                    self.season, matchday, self.groups_data, interaction.user
                )
            elif phase == "ko":
                # KO-Brackets ggf. frisch laden (könnten sich geändert haben)
                if not self.ko_brackets_data:
                    self.ko_brackets_data = await self.api.get_ko_brackets(self.season["id"])

                embed = build_ko_embed(
                    self.season, key, self.ko_brackets_data, interaction.user
                )
            else:
                await interaction.response.edit_message(
                    content="❌ Ungültige Auswahl.", view=None
                )
                return

            # ÖFFENTLICH im Channel posten
            await interaction.channel.send(embed=embed)

            # Ephemeral-Nachricht updaten
            await interaction.response.edit_message(
                content="✅ Spieltag gepostet!", view=None
            )

        except Exception as e:
            logger.error(f"❌ Fehler beim Posten: {e}", exc_info=e)
            await interaction.response.edit_message(
                content=f"❌ Fehler: {e}", view=None
            )


class SpieltageView(discord.ui.View):
    """View mit dem Spieltag-Select-Menü."""

    def __init__(
        self,
        season: dict,
        groups_data: list,
        ko_brackets_data: dict,
        api: BackendAPIClient,
        select_options: list[discord.SelectOption],
    ):
        super().__init__(timeout=60)
        self.add_item(SpieltageSelect(
            season, groups_data, ko_brackets_data, api, select_options
        ))

    async def on_timeout(self):
        """Deaktiviert das Menü nach Timeout."""
        for item in self.children:
            item.disabled = True


class Spieltag(commands.Cog):
    """Cog für /spieltag Command — postet Paarungen öffentlich."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.api = BackendAPIClient()
        logger.info('✅ Spieltag Cog geladen')

    @discord.slash_command(
        name="spieltag",
        description="Zeigt die Paarungen des aktuellen Spieltags"
    )
    async def spieltag(self, ctx: discord.ApplicationContext):
        """
        Slash Command: /spieltag
        Zeigt Select-Menü mit verfügbaren Spieltagen.
        Nach Auswahl wird die Übersicht öffentlich im Channel gepostet.

        Berechtigung: Nur Rollen "Organisation" oder "Teilnehmer".
        """
        # --- Rollenprüfung ---
        if not has_spieltag_permission(ctx.author):
            await ctx.respond(
                "❌ Du brauchst die Rolle **Organisation** oder **Teilnehmer** "
                "um diesen Befehl zu nutzen.",
                ephemeral=True
            )
            return

        await ctx.defer(ephemeral=True)

        logger.info(f'👤 {ctx.author.name} ruft /spieltag auf')

        # --- Aktive Saison finden ---
        seasons = await self.api.get_seasons()
        active_season = next(
            (s for s in seasons if s.get("status") == "active"),
            None
        )

        if not active_season:
            await ctx.followup.send(
                "❌ Aktuell läuft kein Pokal. Keine aktive Saison gefunden.",
                ephemeral=True
            )
            return

        season_id = active_season["id"]

        # --- Gruppen + Matches laden ---
        groups_data = await self.api.get_groups_with_teams(season_id)

        # --- KO-Status prüfen ---
        ko_status = await self.api.get_ko_brackets_status(season_id)

        # --- KO-Brackets laden (nur wenn vorhanden) ---
        ko_brackets_data = {}
        if ko_status.get("brackets_generated"):
            ko_brackets_data = await self.api.get_ko_brackets(season_id)

        # --- Select-Optionen bauen ---
        select_options = build_matchday_options(groups_data, ko_status)

        if not select_options:
            await ctx.followup.send(
                "❌ Keine Spieltage oder KO-Runden gefunden für die aktive Saison.",
                ephemeral=True
            )
            return

        # --- View mit Select-Menü anzeigen ---
        view = SpieltageView(
            season=active_season,
            groups_data=groups_data,
            ko_brackets_data=ko_brackets_data,
            api=self.api,
            select_options=select_options,
        )

        await ctx.followup.send(
            f"🏆 **{active_season['name']}** — Was willst du sehen?",
            view=view,
            ephemeral=True
        )

        logger.info(
            f'✅ Select-Menü gesendet für {ctx.author.name} '
            f'({len(select_options)} Optionen)'
        )


def setup(bot: commands.Bot):
    bot.add_cog(Spieltag(bot))
