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

    async def _ensure_user(self, ctx: discord.ApplicationContext) -> dict | None:
        """
        Zentrale Hilfsmethode für Auto-Registration.
        Extrahiert Discord-Daten und ruft ensure_user auf.

        Returns:
            User-Dict bei Erfolg, None bei Fehler (mit ephemeral Fehlermeldung)
        """
        discord_id = str(ctx.author.id)
        discord_username = ctx.author.name  # Ohne discriminator (bei neuen Accounts leer)
        avatar_url = ctx.author.display_avatar.url if ctx.author.display_avatar else None

        user = await self.api.ensure_user(discord_id, discord_username, avatar_url)

        if not user:
            await ctx.respond(
                "⚠️ Registrierung fehlgeschlagen. Bitte versuche es erneut.",
                ephemeral=True
            )

        return user

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

        logger.info(f'👤 {ctx.author.name} setzt Teilnahme: {status}')

        # Auto-Register/Update User
        user = await self._ensure_user(ctx)
        if not user:
            return

        discord_id = str(ctx.author.id)
        participating = (status == "ja")

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
                description='Teilnahme konnte nicht gespeichert werden. Bitte versuche es später erneut.',
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

        logger.info(f'👤 {ctx.author.name} fragt Status ab')

        # Auto-Register/Update User
        user_data = await self._ensure_user(ctx)
        if not user_data:
            return

        discord_id = str(ctx.author.id)

        # Status-Embed erstellen
        embed = discord.Embed(
            title=f"📊 Status: {ctx.author.name}",
            color=discord.Color.blue()
        )

        # Team Name
        team_name = user_data.get('team_name')
        if team_name:
            embed.add_field(
                name="🏆 Team",
                value=team_name,
                inline=False
            )
        else:
            embed.add_field(
                name="🏆 Team",
                value="Nicht zugewiesen\n💡 Nutze `/claim <teamname>` um dein Team zu verknüpfen",
                inline=False
            )

        # Teilnahme-Status
        participating = user_data.get('participating_next', False)
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

    @discord.slash_command(
        name="claim",
        description="Verknüpfe dein Discord-Konto mit deinem BIW Pokal Team"
    )
    async def claim(
        self,
        ctx: discord.ApplicationContext,
        teamname: Option(
            str,
            description="Name deines Teams (oder Teil davon)",
            required=True,
            min_length=2
        )
    ):
        """
        Slash Command: /claim
        Verknüpft Discord-User mit einem Team (Self-Service)

        Flow:
            1. Auto-register user
            2. Check if user already has team
            3. Search teams
            4. If 0 results -> error
            5. If 1 result -> show confirm dialog
            6. If 2-10 results -> show select menu
        """
        await ctx.defer(ephemeral=True)

        logger.info(f'👤 {ctx.author.name} versucht Team zu claimen: {teamname}')

        # 1. Auto-Register User
        user = await self._ensure_user(ctx)
        if not user:
            return

        discord_id = str(ctx.author.id)

        # 2. Check if user already has team
        if user.get('team_id') is not None:
            team_name = user.get('team_name', 'Unbekannt')
            embed = discord.Embed(
                title="⚠️ Du hast bereits ein Team",
                description=f'Du bist bereits als **{team_name}** registriert.\n\nFalls das nicht korrekt ist, kontaktiere einen Admin.',
                color=discord.Color.orange()
            )
            await ctx.followup.send(embed=embed, ephemeral=True)
            logger.info(f'⚠️ {ctx.author.name} hat bereits Team: {team_name}')
            return

        # 3. Team suchen
        teams = await self.api.search_teams(teamname)

        if not teams:
            # Keine Treffer
            embed = discord.Embed(
                title="❌ Kein Team gefunden",
                description=f'Kein Team mit "{teamname}" gefunden.\n\nPrüfe die Schreibweise und versuche es erneut.',
                color=discord.Color.red()
            )
            await ctx.followup.send(embed=embed, ephemeral=True)
            logger.info(f'❌ Keine Teams gefunden für Suche: {teamname}')
            return

        if len(teams) == 1:
            # Genau ein Treffer -> Bestätigungsdialog
            team = teams[0]
            view = ClaimConfirmView(self.api, discord_id, team, timeout=60)

            embed = discord.Embed(
                title="🏆 Team gefunden",
                description=f'Möchtest du dich als **{team["name"]}** registrieren?',
                color=discord.Color.blue()
            )
            embed.set_footer(text="Klicke auf ✅ zum Bestätigen oder ❌ zum Abbrechen")

            await ctx.followup.send(embed=embed, view=view, ephemeral=True)
            logger.info(f'✅ Ein Team gefunden für {ctx.author.name}: {team["name"]}')

        else:
            # Mehrere Treffer -> Select Menu
            view = ClaimSelectView(self.api, discord_id, teams, timeout=60)

            team_list = "\n".join([f"• {t['name']}" for t in teams[:10]])
            embed = discord.Embed(
                title="🔍 Mehrere Teams gefunden",
                description=f'Wähle dein Team aus:\n\n{team_list}',
                color=discord.Color.blue()
            )
            embed.set_footer(text="Nutze das Dropdown-Menü um dein Team auszuwählen")

            await ctx.followup.send(embed=embed, view=view, ephemeral=True)
            logger.info(f'✅ {len(teams)} Teams gefunden für {ctx.author.name}')


# ============================================================
# Interactive Views for /claim Command
# ============================================================

class ClaimConfirmView(discord.ui.View):
    """
    Confirmation dialog for single team match.
    Shows ✅ Bestätigen and ❌ Abbrechen buttons.
    """

    def __init__(self, api_client, discord_id: str, team: dict, timeout: float = 60):
        super().__init__(timeout=timeout)
        self.api = api_client
        self.discord_id = discord_id
        self.team = team

    @discord.ui.button(label="✅ Bestätigen", style=discord.ButtonStyle.success)
    async def confirm_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        """User confirmed team selection"""
        await interaction.response.defer()

        # Claim team via API
        result = await self.api.claim_team(self.discord_id, self.team['id'])

        if result.get('success'):
            embed = discord.Embed(
                title="✅ Team erfolgreich verknüpft!",
                description=f'Du bist jetzt als **{self.team["name"]}** registriert.',
                color=discord.Color.green()
            )
            embed.add_field(name="🏆 Team", value=self.team['name'], inline=True)
            embed.add_field(name="📅 Nächster Pokal", value="✅ Dabei", inline=True)
            embed.set_footer(text="Nutze /status um deine Daten zu sehen")

            logger.info(f'✅ Team "{self.team["name"]}" geclaimed von User {self.discord_id}')

        elif result.get('error') == 'profile_url_required':
            embed = discord.Embed(
                title="⚠️ Schritt fehlt",
                description='Bitte hinterlege zuerst dein Onlineliga-Profil, bevor du ein Team verknüpfst.\n\n`/profil url:https://www.onlineliga.de/...`',
                color=discord.Color.orange()
            )
            logger.warning(f'⚠️ User {self.discord_id} hat keine Profile URL gesetzt')

        elif result.get('error') == 'team_claimed':
            embed = discord.Embed(
                title="❌ Team bereits vergeben",
                description=f'**{self.team["name"]}** ist bereits von einem anderen User verknüpft.\n\nFalls das dein Team ist, kontaktiere einen Admin.',
                color=discord.Color.red()
            )
            logger.warning(f'⚠️ Team "{self.team["name"]}" bereits vergeben')

        elif result.get('error') == 'already_has_team':
            embed = discord.Embed(
                title="❌ Du hast bereits ein Team",
                description='Du hast bereits ein Team verknüpft. Kontaktiere einen Admin falls du es ändern möchtest.',
                color=discord.Color.red()
            )
            logger.warning(f'⚠️ User {self.discord_id} hat bereits ein Team')

        else:
            embed = discord.Embed(
                title="❌ Fehler",
                description='Team konnte nicht verknüpft werden. Bitte versuche es später erneut.',
                color=discord.Color.red()
            )
            logger.error(f'❌ Claim fehlgeschlagen für User {self.discord_id}: {result}')

        # Disable buttons after interaction
        for item in self.children:
            item.disabled = True

        await interaction.message.edit(embed=embed, view=self)

    @discord.ui.button(label="❌ Abbrechen", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        """User cancelled"""
        embed = discord.Embed(
            title="❌ Abgebrochen",
            description='Team-Verknüpfung abgebrochen.',
            color=discord.Color.grey()
        )

        # Disable buttons
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(embed=embed, view=self)
        logger.info(f'⚠️ Team-Claim abgebrochen von User {self.discord_id}')


class ClaimSelectView(discord.ui.View):
    """
    Select menu for multiple team matches.
    Shows dropdown with team names.
    """

    def __init__(self, api_client, discord_id: str, teams: list, timeout: float = 60):
        super().__init__(timeout=timeout)
        self.api = api_client
        self.discord_id = discord_id
        self.teams = teams

        # Add select menu
        self.add_item(TeamSelect(teams))

    async def claim_team(self, interaction: discord.Interaction, team_id: int):
        """Called when user selects a team"""
        await interaction.response.defer()

        # Find selected team
        team = next((t for t in self.teams if t['id'] == team_id), None)
        if not team:
            logger.error(f'❌ Team ID {team_id} nicht in Liste gefunden')
            return

        # Claim team via API
        result = await self.api.claim_team(self.discord_id, team_id)

        if result.get('success'):
            embed = discord.Embed(
                title="✅ Team erfolgreich verknüpft!",
                description=f'Du bist jetzt als **{team["name"]}** registriert.',
                color=discord.Color.green()
            )
            embed.add_field(name="🏆 Team", value=team['name'], inline=True)
            embed.add_field(name="📅 Nächster Pokal", value="✅ Dabei", inline=True)
            embed.set_footer(text="Nutze /status um deine Daten zu sehen")

            logger.info(f'✅ Team "{team["name"]}" geclaimed von User {self.discord_id}')

        elif result.get('error') == 'profile_url_required':
            embed = discord.Embed(
                title="⚠️ Schritt fehlt",
                description='Bitte hinterlege zuerst dein Onlineliga-Profil, bevor du ein Team verknüpfst.\n\n`/profil url:https://www.onlineliga.de/...`',
                color=discord.Color.orange()
            )
            logger.warning(f'⚠️ User {self.discord_id} hat keine Profile URL gesetzt')

        elif result.get('error') == 'team_claimed':
            embed = discord.Embed(
                title="❌ Team bereits vergeben",
                description=f'**{team["name"]}** ist bereits von einem anderen User verknüpft.\n\nFalls das dein Team ist, kontaktiere einen Admin.',
                color=discord.Color.red()
            )
            logger.warning(f'⚠️ Team "{team["name"]}" bereits vergeben')

        elif result.get('error') == 'already_has_team':
            embed = discord.Embed(
                title="❌ Du hast bereits ein Team",
                description='Du hast bereits ein Team verknüpft. Kontaktiere einen Admin falls du es ändern möchtest.',
                color=discord.Color.red()
            )
            logger.warning(f'⚠️ User {self.discord_id} hat bereits ein Team')

        else:
            embed = discord.Embed(
                title="❌ Fehler",
                description='Team konnte nicht verknüpft werden. Bitte versuche es später erneut.',
                color=discord.Color.red()
            )
            logger.error(f'❌ Claim fehlgeschlagen für User {self.discord_id}: {result}')

        # Disable select menu after interaction
        for item in self.children:
            item.disabled = True

        await interaction.message.edit(embed=embed, view=self)


class TeamSelect(discord.ui.Select):
    """
    Dropdown select for team selection.
    """

    def __init__(self, teams: list):
        options = [
            discord.SelectOption(
                label=team['name'][:100],  # Max 100 chars
                value=str(team['id']),
                description=f"Team ID: {team['id']}"
            )
            for team in teams[:25]  # Max 25 options
        ]

        super().__init__(
            placeholder="Wähle dein Team...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        """Called when user selects an option"""
        team_id = int(self.values[0])
        await self.view.claim_team(interaction, team_id)


def setup(bot: commands.Bot):
    """Setup-Funktion zum Laden des Cogs"""
    bot.add_cog(Teilnahme(bot))
