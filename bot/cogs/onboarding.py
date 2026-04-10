"""
Onboarding Cog - Geführter Anmeldeprozess für neue Teilnehmer
/anmelden - Mehrstufiger Onboarding-Flow (Teilnahme → Team → Profil → Fertig)
"""

import logging
import os
import re
import discord
from discord.ext import commands
from discord import Option

from utils.api_client import BackendAPIClient

logger = logging.getLogger('biw-bot.onboarding')

DASHBOARD_URL = os.getenv('DASHBOARD_URL', 'https://biw-pokal.de')


def _validate_url(url: str) -> bool:
    """Validiert ob URL gültig ist (gleiche Logik wie profil.py)."""
    url_pattern = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$',
        re.IGNORECASE
    )
    return url_pattern.match(url) is not None


class OnboardingSession:
    """Tracks state across the multi-step onboarding flow."""

    def __init__(self, discord_id: str, user_data: dict, api: BackendAPIClient, teamname_param: str = None):
        self.discord_id = discord_id
        self.user_data = user_data
        self.api = api
        self.participating = user_data.get('participating_next', False)
        self.team_claimed = user_data.get('team_id') is not None
        self.team_name = user_data.get('team_name')
        self.profile_url_set = bool(user_data.get('profile_url'))
        self.profile_url = user_data.get('profile_url')
        self.teamname_param = teamname_param  # Pre-filled from slash command parameter

    def build_summary_embed(self) -> discord.Embed:
        """Builds the final summary embed."""
        embed = discord.Embed(
            title="✅ Anmeldung abgeschlossen!",
            color=discord.Color.green()
        )

        embed.add_field(
            name="📅 Teilnahme",
            value="✅ Dabei" if self.participating else "❌ Nicht dabei",
            inline=True
        )

        if self.team_claimed and self.team_name:
            embed.add_field(name="🏆 Team", value=self.team_name, inline=True)
        else:
            embed.add_field(
                name="🏆 Team",
                value="Noch nicht verknüpft — `/claim <teamname>`",
                inline=True
            )

        if self.profile_url_set and self.profile_url:
            embed.add_field(
                name="🔗 Profil",
                value=f"[Zum Profil]({self.profile_url})",
                inline=False
            )
        else:
            embed.add_field(
                name="🔗 Profil",
                value="Noch nicht hinterlegt — `/profil <url>`",
                inline=False
            )

        upload_url = f'{DASHBOARD_URL}/dashboard.html'
        embed.add_field(
            name="🛡️ Wappen",
            value=f"Lade dein Wappen im Dashboard hoch: [Dashboard]({upload_url})",
            inline=False
        )

        embed.set_footer(text="Nutze /status um deine Daten jederzeit einzusehen.")
        return embed


# ============================================================
# Flow progression helpers
# ============================================================

async def proceed_to_team_step(interaction: discord.Interaction, session: OnboardingSession):
    """Step 3: Team claim (or skip if already has one)."""
    if session.team_claimed:
        await proceed_to_profile_step(interaction, session)
        return

    # If teamname parameter was provided, search directly
    if session.teamname_param:
        search_term = session.teamname_param
        session.teamname_param = None  # Consume it

        embed = discord.Embed(
            title="🏆 Team verknüpfen",
            description=f'Suche nach „{search_term}"...',
            color=discord.Color.gold()
        )
        msg = await interaction.followup.send(embed=embed, ephemeral=True)
        await do_team_search_on_message(msg, interaction, session, search_term)
        return

    # No parameter — show search button + skip
    embed = discord.Embed(
        title="🏆 Team verknüpfen",
        description="Suche jetzt dein Team, um es mit deinem Discord-Konto zu verknüpfen.",
        color=discord.Color.gold()
    )
    view = TeamSearchView(session)
    msg = await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    view.message = msg


async def do_team_search_on_message(msg, interaction: discord.Interaction, session: OnboardingSession, search_term: str):
    """Execute team search and update a specific message with results."""
    teams = await session.api.search_teams(search_term)

    if not teams:
        embed = discord.Embed(
            title="❌ Kein Team gefunden",
            description=f'Kein Team gefunden für „{search_term}". Kontaktiere einen Admin oder versuche es später mit `/claim`.',
            color=discord.Color.red()
        )
        await msg.edit(embed=embed, view=None)
        await proceed_to_profile_step(interaction, session)

    elif len(teams) == 1:
        team = teams[0]
        view = OnboardingTeamConfirmView(session, team)
        view.message = msg
        embed = discord.Embed(
            title="🏆 Team gefunden",
            description=f'Ist das dein Team: **{team["name"]}**?',
            color=discord.Color.blue()
        )
        await msg.edit(embed=embed, view=view)

    else:
        view = OnboardingTeamSelectView(session, teams[:10])
        view.message = msg
        team_list = "\n".join([f"• {t['name']}" for t in teams[:10]])
        embed = discord.Embed(
            title="🔍 Mehrere Teams gefunden",
            description=f'Wähle dein Team aus:\n\n{team_list}',
            color=discord.Color.blue()
        )
        await msg.edit(embed=embed, view=view)


async def do_team_search(interaction: discord.Interaction, session: OnboardingSession, search_term: str):
    """Execute team search and show results by editing the original response."""
    teams = await session.api.search_teams(search_term)

    if not teams:
        embed = discord.Embed(
            title="❌ Kein Team gefunden",
            description=f'Kein Team gefunden für „{search_term}". Kontaktiere einen Admin oder versuche es später mit `/claim`.',
            color=discord.Color.red()
        )
        await interaction.edit_original_response(embed=embed, view=None)
        await proceed_to_profile_step(interaction, session)

    elif len(teams) == 1:
        team = teams[0]
        view = OnboardingTeamConfirmView(session, team)
        embed = discord.Embed(
            title="🏆 Team gefunden",
            description=f'Ist das dein Team: **{team["name"]}**?',
            color=discord.Color.blue()
        )
        await interaction.edit_original_response(embed=embed, view=view)

    else:
        view = OnboardingTeamSelectView(session, teams[:10])
        team_list = "\n".join([f"• {t['name']}" for t in teams[:10]])
        embed = discord.Embed(
            title="🔍 Mehrere Teams gefunden",
            description=f'Wähle dein Team aus:\n\n{team_list}',
            color=discord.Color.blue()
        )
        await interaction.edit_original_response(embed=embed, view=view)


async def proceed_to_profile_step(interaction: discord.Interaction, session: OnboardingSession):
    """Step 4: Profile URL (or skip if already set)."""
    if session.profile_url_set:
        await show_summary(interaction, session)
        return

    embed = discord.Embed(
        title="🔗 Profil-URL hinterlegen",
        description="Möchtest du deine Onlineliga Profil-URL hinterlegen? (Optional)",
        color=discord.Color.gold()
    )
    view = ProfileStepView(session)
    msg = await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    view.message = msg


async def show_summary(interaction: discord.Interaction, session: OnboardingSession):
    """Step 6: Final summary."""
    embed = session.build_summary_embed()
    await interaction.followup.send(embed=embed, ephemeral=True)


# ============================================================
# Step 2: Participation View
# ============================================================

class ParticipationView(discord.ui.View):
    """Buttons for participation selection (Step 2)."""

    def __init__(self, session: OnboardingSession, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.session = session
        self.message = None

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            embed = discord.Embed(
                title="⏰ Zeitüberschreitung",
                description="Starte den Prozess mit `/anmelden` erneut.",
                color=discord.Color.grey()
            )
            try:
                await self.message.edit(embed=embed, view=self)
            except Exception:
                pass

    @discord.ui.button(label="✅ Ich bin dabei!", style=discord.ButtonStyle.success)
    async def participate_yes(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.defer()
        success = await self.session.api.set_participation(self.session.discord_id, True)
        if success:
            self.session.participating = True
            logger.info(f'✅ Teilnahme gesetzt für {self.session.discord_id}')

        for item in self.children:
            item.disabled = True
        await interaction.edit_original_response(view=self)

        await proceed_to_team_step(interaction, self.session)

    @discord.ui.button(label="❌ Nicht dabei", style=discord.ButtonStyle.secondary)
    async def participate_no(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.session.api.set_participation(self.session.discord_id, False)
        self.session.participating = False

        for item in self.children:
            item.disabled = True

        embed = discord.Embed(
            title="👋 Okay!",
            description="Du bist aktuell nicht dabei. Du kannst dich jederzeit mit `/dabei ja` oder `/anmelden` anmelden.",
            color=discord.Color.grey()
        )
        await interaction.edit_original_response(embed=embed, view=self)
        logger.info(f'ℹ️ {self.session.discord_id} nimmt nicht teil')


# ============================================================
# Step 3: Team Claim Views
# ============================================================

class TeamNameModal(discord.ui.Modal):
    """Modal for entering team name search."""

    def __init__(self, session: OnboardingSession):
        super().__init__(title="Team suchen")
        self.session = session
        self.add_item(
            discord.ui.InputText(
                label="Dein Teamname (oder Teil davon)",
                placeholder="z.B. FC Bayern oder Bayern",
                min_length=2,
                max_length=100,
                style=discord.InputTextStyle.short
            )
        )

    async def callback(self, interaction: discord.Interaction):
        search_term = self.children[0].value.strip()
        await interaction.response.defer()
        await do_team_search(interaction, self.session, search_term)


class TeamSearchView(discord.ui.View):
    """View with a button to open team search modal, or skip."""

    def __init__(self, session: OnboardingSession, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.session = session
        self.message = None

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            embed = discord.Embed(
                title="⏰ Zeitüberschreitung",
                description="Starte den Prozess mit `/anmelden` erneut.",
                color=discord.Color.grey()
            )
            try:
                await self.message.edit(embed=embed, view=self)
            except Exception:
                pass

    @discord.ui.button(label="🔍 Team suchen", style=discord.ButtonStyle.primary)
    async def search_team(self, button: discord.ui.Button, interaction: discord.Interaction):
        modal = TeamNameModal(self.session)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="⏭️ Überspringen", style=discord.ButtonStyle.secondary)
    async def skip_team(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True

        embed = discord.Embed(
            title="⏭️ Team übersprungen",
            description="Du kannst dein Team jederzeit mit `/claim <teamname>` verknüpfen.",
            color=discord.Color.grey()
        )
        await interaction.edit_original_response(embed=embed, view=self)

        await proceed_to_profile_step(interaction, self.session)


class OnboardingTeamConfirmView(discord.ui.View):
    """Confirm a single team match during onboarding."""

    def __init__(self, session: OnboardingSession, team: dict, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.session = session
        self.team = team
        self.message = None

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            embed = discord.Embed(
                title="⏰ Zeitüberschreitung",
                description="Starte den Prozess mit `/anmelden` erneut.",
                color=discord.Color.grey()
            )
            try:
                await self.message.edit(embed=embed, view=self)
            except Exception:
                pass

    @discord.ui.button(label="✅ Ja, das ist mein Team", style=discord.ButtonStyle.success)
    async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.defer()

        result = await self.session.api.claim_team(self.session.discord_id, self.team['id'])

        for item in self.children:
            item.disabled = True

        if result.get('success'):
            self.session.team_claimed = True
            self.session.team_name = self.team['name']
            embed = discord.Embed(
                title="✅ Team verknüpft!",
                description=f'Du bist jetzt als **{self.team["name"]}** registriert.',
                color=discord.Color.green()
            )
            logger.info(f'✅ Team "{self.team["name"]}" geclaimed von {self.session.discord_id}')
        elif result.get('error') == 'already_has_team':
            self.session.team_claimed = True
            embed = discord.Embed(
                title="⚠️ Du hast bereits ein Team",
                description="Du hast bereits ein Team verknüpft.",
                color=discord.Color.orange()
            )
        elif result.get('error') == 'team_claimed':
            embed = discord.Embed(
                title="❌ Team bereits vergeben",
                description=f'**{self.team["name"]}** ist bereits von jemand anderem verknüpft. Kontaktiere einen Admin.',
                color=discord.Color.red()
            )
        else:
            embed = discord.Embed(
                title="❌ Fehler",
                description="Team konnte nicht verknüpft werden. Versuche es später mit `/claim`.",
                color=discord.Color.red()
            )
            logger.error(f'❌ Claim fehlgeschlagen: {result}')

        await interaction.edit_original_response(embed=embed, view=self)
        await proceed_to_profile_step(interaction, self.session)

    @discord.ui.button(label="❌ Das bin ich nicht", style=discord.ButtonStyle.secondary)
    async def deny(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True

        embed = discord.Embed(
            title="ℹ️ Team übersprungen",
            description="Kein Problem! Nutze später `/claim <teamname>` um dein Team zu verknüpfen.",
            color=discord.Color.grey()
        )
        await interaction.edit_original_response(embed=embed, view=self)
        await proceed_to_profile_step(interaction, self.session)


class OnboardingTeamSelect(discord.ui.Select):
    """Dropdown for selecting from multiple team matches."""

    def __init__(self, teams: list):
        options = [
            discord.SelectOption(
                label=team['name'][:100],
                value=str(team['id']),
                description=f"Team ID: {team['id']}"
            )
            for team in teams[:25]
        ]
        super().__init__(
            placeholder="Wähle dein Team...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        team_id = int(self.values[0])
        await self.view.on_team_selected(interaction, team_id)


class OnboardingTeamSelectView(discord.ui.View):
    """Select menu for multiple team matches during onboarding."""

    def __init__(self, session: OnboardingSession, teams: list, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.session = session
        self.teams = teams
        self.message = None
        self.add_item(OnboardingTeamSelect(teams))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            embed = discord.Embed(
                title="⏰ Zeitüberschreitung",
                description="Starte den Prozess mit `/anmelden` erneut.",
                color=discord.Color.grey()
            )
            try:
                await self.message.edit(embed=embed, view=self)
            except Exception:
                pass

    async def on_team_selected(self, interaction: discord.Interaction, team_id: int):
        await interaction.response.defer()

        team = next((t for t in self.teams if t['id'] == team_id), None)
        if not team:
            logger.error(f'❌ Team ID {team_id} nicht in Liste')
            return

        result = await self.session.api.claim_team(self.session.discord_id, team_id)

        for item in self.children:
            item.disabled = True

        if result.get('success'):
            self.session.team_claimed = True
            self.session.team_name = team['name']
            embed = discord.Embed(
                title="✅ Team verknüpft!",
                description=f'Du bist jetzt als **{team["name"]}** registriert.',
                color=discord.Color.green()
            )
            logger.info(f'✅ Team "{team["name"]}" geclaimed von {self.session.discord_id}')
        elif result.get('error') == 'already_has_team':
            self.session.team_claimed = True
            embed = discord.Embed(
                title="⚠️ Du hast bereits ein Team",
                description="Du hast bereits ein Team verknüpft.",
                color=discord.Color.orange()
            )
        elif result.get('error') == 'team_claimed':
            embed = discord.Embed(
                title="❌ Team bereits vergeben",
                description=f'**{team["name"]}** ist bereits von jemand anderem verknüpft. Kontaktiere einen Admin.',
                color=discord.Color.red()
            )
        else:
            embed = discord.Embed(
                title="❌ Fehler",
                description="Team konnte nicht verknüpft werden. Versuche es später mit `/claim`.",
                color=discord.Color.red()
            )
            logger.error(f'❌ Claim fehlgeschlagen: {result}')

        await interaction.edit_original_response(embed=embed, view=self)
        await proceed_to_profile_step(interaction, self.session)


# ============================================================
# Step 4: Profile URL Views
# ============================================================

class ProfileUrlModal(discord.ui.Modal):
    """Modal for entering profile URL."""

    def __init__(self, session: OnboardingSession):
        super().__init__(title="Profil-URL hinterlegen")
        self.session = session
        self.add_item(
            discord.ui.InputText(
                label="Deine Onlineliga Profil-URL",
                placeholder="https://www.onlineliga.de/...",
                min_length=10,
                max_length=500,
                style=discord.InputTextStyle.short
            )
        )

    async def callback(self, interaction: discord.Interaction):
        url = self.children[0].value.strip()

        if not _validate_url(url):
            embed = discord.Embed(
                title="❌ Ungültige URL",
                description=(
                    "Die URL ist nicht gültig. Sie muss mit `http://` oder `https://` beginnen.\n\n"
                    "**Beispiel:** `https://onlineliga.de/user/123456`"
                ),
                color=discord.Color.red()
            )
            view = ProfileRetryView(self.session)
            await interaction.response.edit_message(embed=embed, view=view)
            return

        await interaction.response.defer()
        success = await self.session.api.set_profile_url(self.session.discord_id, url)

        if success:
            self.session.profile_url_set = True
            self.session.profile_url = url
            embed = discord.Embed(
                title="✅ Profil-URL gespeichert!",
                description=f"**URL:** {url}",
                color=discord.Color.green()
            )
            logger.info(f'✅ Profil-URL gespeichert für {self.session.discord_id}')
        else:
            embed = discord.Embed(
                title="❌ Fehler",
                description="Profil-URL konnte nicht gespeichert werden. Nutze später `/profil <url>`.",
                color=discord.Color.red()
            )

        await interaction.edit_original_response(embed=embed, view=None)
        await show_summary(interaction, self.session)


class ProfileStepView(discord.ui.View):
    """Buttons for profile URL step (enter or skip)."""

    def __init__(self, session: OnboardingSession, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.session = session
        self.message = None

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            embed = discord.Embed(
                title="⏰ Zeitüberschreitung",
                description="Starte den Prozess mit `/anmelden` erneut.",
                color=discord.Color.grey()
            )
            try:
                await self.message.edit(embed=embed, view=self)
            except Exception:
                pass

    @discord.ui.button(label="🔗 URL eingeben", style=discord.ButtonStyle.primary)
    async def enter_url(self, button: discord.ui.Button, interaction: discord.Interaction):
        modal = ProfileUrlModal(self.session)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="⏭️ Überspringen", style=discord.ButtonStyle.secondary)
    async def skip_url(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True

        embed = discord.Embed(
            title="⏭️ Profil übersprungen",
            description="Du kannst dein Profil jederzeit mit `/profil <url>` hinterlegen.",
            color=discord.Color.grey()
        )
        await interaction.edit_original_response(embed=embed, view=self)

        await show_summary(interaction, self.session)


class ProfileRetryView(discord.ui.View):
    """Retry or skip after invalid URL."""

    def __init__(self, session: OnboardingSession, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.session = session

    @discord.ui.button(label="🔗 Erneut eingeben", style=discord.ButtonStyle.primary)
    async def retry_url(self, button: discord.ui.Button, interaction: discord.Interaction):
        modal = ProfileUrlModal(self.session)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="⏭️ Überspringen", style=discord.ButtonStyle.secondary)
    async def skip_url(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True

        embed = discord.Embed(
            title="⏭️ Profil übersprungen",
            description="Du kannst dein Profil jederzeit mit `/profil <url>` hinterlegen.",
            color=discord.Color.grey()
        )
        await interaction.edit_original_response(embed=embed, view=self)

        await show_summary(interaction, self.session)


# ============================================================
# Main Cog
# ============================================================

class Onboarding(commands.Cog):
    """Cog für geführten Onboarding-Prozess"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.api = BackendAPIClient()
        logger.info('✅ Onboarding Cog geladen')

    async def _ensure_user(self, ctx: discord.ApplicationContext) -> dict | None:
        """Zentrale Hilfsmethode für Auto-Registration."""
        discord_id = str(ctx.author.id)
        discord_username = ctx.author.name
        avatar_url = ctx.author.display_avatar.url if ctx.author.display_avatar else None

        user = await self.api.ensure_user(discord_id, discord_username, avatar_url)

        if not user:
            await ctx.respond(
                "⚠️ Registrierung fehlgeschlagen. Bitte versuche es erneut.",
                ephemeral=True
            )

        return user

    @discord.slash_command(
        name="anmelden",
        description="Melde dich für den BIW Pokal an — geführter Prozess"
    )
    async def anmelden(
        self,
        ctx: discord.ApplicationContext,
        teamname: Option(
            str,
            description="Name deines Teams (optional, kann auch im Dialog eingegeben werden)",
            required=False,
            default=None,
            min_length=2
        ) = None
    ):
        """Geführter Onboarding-Flow: Teilnahme → Team → Profil → Zusammenfassung"""
        await ctx.defer(ephemeral=True)

        logger.info(f'👤 {ctx.author.name} startet Onboarding (teamname={teamname})')

        # Step 0: Init
        user = await self._ensure_user(ctx)
        if not user:
            return

        discord_id = str(ctx.author.id)

        # Fetch full user data
        user_data = await self.api.get_team_by_discord_id(discord_id)
        if not user_data:
            user_data = user

        session = OnboardingSession(discord_id, user_data, self.api, teamname_param=teamname)

        # Step 1: Already fully registered? Early return
        if session.team_claimed and session.participating:
            embed = discord.Embed(
                title=f"📊 Status: {ctx.author.name}",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="🏆 Team",
                value=session.team_name or "Verknüpft",
                inline=True
            )
            embed.add_field(
                name="📅 Teilnahme",
                value="✅ Dabei",
                inline=True
            )
            if session.profile_url:
                embed.add_field(
                    name="🔗 Profil",
                    value=f"[Zum Profil]({session.profile_url})",
                    inline=False
                )
            upload_url = f'{DASHBOARD_URL}/dashboard.html'
            embed.add_field(
                name="🛡️ Wappen",
                value=f"[Im Dashboard hochladen]({upload_url})",
                inline=False
            )
            embed.set_footer(
                text="Du bist bereits angemeldet! Nutze /dabei, /profil, /claim oder /wappen um einzelne Daten zu ändern."
            )
            if ctx.author.display_avatar:
                embed.set_thumbnail(url=ctx.author.display_avatar.url)
            await ctx.followup.send(embed=embed, ephemeral=True)
            logger.info(f'ℹ️ {ctx.author.name} bereits vollständig angemeldet')
            return

        # Step 2: Participation
        embed = discord.Embed(
            title="🏆 BIW Pokal — Anmeldung",
            description="Willkommen bei Die Besten im Westen! In wenigen Schritten bist du angemeldet.",
            color=discord.Color.gold()
        )

        view = ParticipationView(session)
        message = await ctx.followup.send(embed=embed, view=view, ephemeral=True)
        view.message = message


def setup(bot: commands.Bot):
    """Setup-Funktion zum Laden des Cogs"""
    bot.add_cog(Onboarding(bot))
