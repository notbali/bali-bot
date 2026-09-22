import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks

import db
from config import GONEXT_BOT_SECRET, GONEXT_URL
from services.gonext import GonextError, allowed_mentions_for, fetch_due_pings

log = logging.getLogger("bali-bot.premier")


class PremierCog(commands.Cog):
    """Posts GO//NEXT's Premier availability pings. The site decides what's due
    and when; this cog just polls, posts each ping once per server, and
    remembers what it posted."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        if GONEXT_URL and GONEXT_BOT_SECRET:
            self.poll_pings.start()
        else:
            log.info("GONEXT_URL / GONEXT_BOT_SECRET not set; Premier pings disabled.")

    def cog_unload(self) -> None:
        self.poll_pings.cancel()

    premier = app_commands.Group(name="premier", description="GO//NEXT Premier pings")

    @premier.command(name="set-channel", description="Post GO//NEXT Premier pings in a channel")
    @app_commands.describe(channel="Where Premier pings should be posted")
    @app_commands.default_permissions(manage_guild=True)
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        assert interaction.guild
        db.set_premier_channel(interaction.guild.id, channel.id)
        await interaction.response.send_message(
            f"Premier pings will post in {channel.mention}. Checks run every 5 minutes.",
            ephemeral=True,
        )

    @premier.command(name="clear-channel", description="Stop posting GO//NEXT Premier pings")
    @app_commands.default_permissions(manage_guild=True)
    async def clear_channel(self, interaction: discord.Interaction):
        assert interaction.guild
        db.clear_premier_channel(interaction.guild.id)
        await interaction.response.send_message("Premier pings turned off.", ephemeral=True)

    @premier.command(name="check", description="Check GO//NEXT for due pings right now")
    @app_commands.default_permissions(manage_guild=True)
    async def check(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            posted = await self._post_due_pings()
        except GonextError as e:
            await interaction.followup.send(f"Couldn't reach GO//NEXT: {e}", ephemeral=True)
            return
        await interaction.followup.send(
            f"Posted {posted} ping(s)." if posted else "Nothing due right now.", ephemeral=True
        )

    async def _post_due_pings(self) -> int:
        session = self.bot.http_session
        if session is None or not (GONEXT_URL and GONEXT_BOT_SECRET):
            return 0
        channels = db.all_premier_channels()
        if not channels:
            return 0

        pings = await fetch_due_pings(session, GONEXT_URL, GONEXT_BOT_SECRET)
        posted = 0
        for row in channels:
            guild_id, channel_id = int(row["guild_id"]), int(row["channel_id"])
            guild = self.bot.get_guild(guild_id)
            channel = guild.get_channel(channel_id) if guild else None
            if not isinstance(channel, discord.TextChannel):
                continue
            for ping in pings:
                if db.premier_ping_posted(guild_id, ping.key):
                    continue
                try:
                    await channel.send(content=ping.content, allowed_mentions=allowed_mentions_for(ping))
                except discord.HTTPException:
                    log.warning("Failed posting Premier ping %s in guild %s", ping.key, guild_id)
                    continue
                db.mark_premier_ping_posted(guild_id, ping.key)
                posted += 1
        return posted

    @tasks.loop(minutes=5)
    async def poll_pings(self) -> None:
        try:
            await self._post_due_pings()
        except GonextError as e:
            log.warning("Premier ping poll failed: %s", e)
        except Exception:
            log.exception("Premier ping poll crashed")

    @poll_pings.before_loop
    async def _before_poll_pings(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(PremierCog(bot))
