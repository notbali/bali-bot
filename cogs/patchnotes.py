import discord
from discord import app_commands
from discord.ext import commands, tasks

import db
from services.patchnotes import PatchNotesError, fetch_latest_patchnote


PATCH_GAMES = (
    app_commands.Choice(name="League of Legends", value="league"),
    app_commands.Choice(name="Valorant", value="valorant"),
)


def _default_patchnotes_url(game: str) -> str:
    if game == "league":
        return "https://www.leagueoflegends.com/en-us/news/tags/patch-notes/"
    return "https://playvalorant.com/en-us/news/tags/patch-notes/"


def _embed_color(game: str) -> int:
    return 0xC89B3C if game == "league" else 0xFD4556


class PatchNotesCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.autopost_patchnotes.start()

    def cog_unload(self) -> None:
        self.autopost_patchnotes.cancel()

    patchnotes = app_commands.Group(
        name="patchnotes",
        description="Configure and post patch notes in this server",
    )

    @patchnotes.command(name="set-channel", description="Set patch notes channel for a game")
    @app_commands.describe(game="Which game", channel="Where patch notes should be posted")
    @app_commands.choices(game=PATCH_GAMES)
    @app_commands.default_permissions(manage_guild=True)
    async def set_channel(
        self,
        interaction: discord.Interaction,
        game: app_commands.Choice[str],
        channel: discord.TextChannel,
    ):
        assert interaction.guild
        db.set_patchnote_channel(interaction.guild.id, game.value, channel.id)
        await interaction.response.send_message(
            f"Set **{game.name}** patch notes channel to {channel.mention}.\n"
            "Auto-post checks run hourly.",
            ephemeral=True,
        )

    @patchnotes.command(name="clear-channel", description="Clear configured patch notes channel")
    @app_commands.describe(game="Which game")
    @app_commands.choices(game=PATCH_GAMES)
    @app_commands.default_permissions(manage_guild=True)
    async def clear_channel(self, interaction: discord.Interaction, game: app_commands.Choice[str]):
        assert interaction.guild
        db.clear_patchnote_channel(interaction.guild.id, game.value)
        await interaction.response.send_message(
            f"Cleared **{game.name}** patch notes channel.",
            ephemeral=True,
        )

    @patchnotes.command(name="post", description="Post patch notes to configured channel")
    @app_commands.describe(
        game="Which game",
        title="Patch title, e.g. 14.8 Notes",
        url="Patch notes URL (optional)",
    )
    @app_commands.choices(game=PATCH_GAMES)
    @app_commands.default_permissions(manage_guild=True)
    async def post_patchnotes(
        self,
        interaction: discord.Interaction,
        game: app_commands.Choice[str],
        title: str,
        url: str | None = None,
    ):
        assert interaction.guild
        channel_id = db.get_patchnote_channel(interaction.guild.id, game.value)
        if not channel_id:
            await interaction.response.send_message(
                f"No channel configured for **{game.name}**.\n"
                f"Run `/patchnotes set-channel` first.",
                ephemeral=True,
            )
            return

        channel = interaction.guild.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "Configured channel no longer exists or is not a text channel.",
                ephemeral=True,
            )
            return

        target_url = (url or "").strip() or _default_patchnotes_url(game.value)
        embed = discord.Embed(
            title=f"{game.name} Patch Notes",
            description=f"**{title.strip()}**\n{target_url}",
            color=_embed_color(game.value),
        )
        embed.set_footer(text=f"Posted by {interaction.user.display_name}")

        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            await interaction.response.send_message(
                f"I can't send messages in {channel.mention}. Check channel permissions.",
                ephemeral=True,
            )
            return
        db.set_patchnote_last_url(interaction.guild.id, game.value, target_url)

        await interaction.response.send_message(
            f"Posted **{game.name}** patch notes in {channel.mention}.",
            ephemeral=True,
        )

    @tasks.loop(minutes=60)
    async def autopost_patchnotes(self) -> None:
        session = self.bot.http_session
        if session is None:
            return

        latest_by_game: dict[str, tuple[str, str]] = {}
        for game in ("league", "valorant"):
            try:
                latest_by_game[game] = await fetch_latest_patchnote(session, game)
            except PatchNotesError:
                continue
            except Exception:
                continue

        for row in db.all_patchnote_channels():
            guild_id = int(row["guild_id"])
            game = str(row["game"])
            channel_id = int(row["channel_id"])
            latest = latest_by_game.get(game)
            if not latest:
                continue

            latest_url, title = latest
            if not latest_url:
                continue
            if db.get_patchnote_last_url(guild_id, game) == latest_url:
                continue

            guild = self.bot.get_guild(guild_id)
            if guild is None:
                continue
            channel = guild.get_channel(channel_id)
            if not isinstance(channel, discord.TextChannel):
                continue

            embed = discord.Embed(
                title=f"{'League of Legends' if game == 'league' else 'Valorant'} Patch Notes",
                description=f"**{title or 'New patch notes available'}**\n{latest_url}",
                color=_embed_color(game),
            )
            embed.set_footer(text="Auto-posted by bali-bot")

            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                continue
            except discord.HTTPException:
                continue

            db.set_patchnote_last_url(guild_id, game, latest_url)

    @autopost_patchnotes.before_loop
    async def _before_autopost_patchnotes(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(PatchNotesCog(bot))
