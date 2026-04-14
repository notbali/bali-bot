import asyncio

import discord
from discord import app_commands
from discord.ext import commands

import db
from services.riot import RiotError, format_league_entry, league_rank_summary, league_sort_key
from services.valorant import (
    HenrikError,
    TrackerGGError,
    fetch_valorant_mmr,
    format_valorant_rank,
    valorant_sort_key,
)


async def _display_name(client: discord.Client, guild: discord.Guild, user_id: int) -> str:
    m = guild.get_member(user_id)
    if m:
        return m.display_name
    try:
        u = await client.fetch_user(user_id)
        return u.global_name or u.name
    except discord.HTTPException:
        return f"user {user_id}"


class LeaderboardCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="leaderboard", description="Highest linked ranks in this server")
    @app_commands.describe(game="Which game to rank")
    @app_commands.choices(
        game=[
            app_commands.Choice(name="Valorant", value="valorant"),
            app_commands.Choice(name="League of Legends", value="league"),
        ]
    )
    async def leaderboard(
        self,
        interaction: discord.Interaction,
        game: app_commands.Choice[str],
    ):
        assert interaction.guild
        await interaction.response.defer(thinking=True)
        guild = interaction.guild
        rows = db.all_links_for_guild(guild.id)
        sem = asyncio.Semaphore(4)
        session = self.bot.http_session

        if game.value == "valorant":
            targets = [r for r in rows if r.get("valorant_name") and r.get("valorant_region")]
            if not targets:
                await interaction.followup.send("No one has linked Valorant in this server yet.")
                return

            async def one(row: dict) -> tuple[int, str, str]:
                async with sem:
                    try:
                        payload = await fetch_valorant_mmr(
                            session,
                            row["valorant_region"],
                            row["valorant_name"],
                            row["valorant_tag"],
                        )
                        key = valorant_sort_key(payload)
                        label = format_valorant_rank(payload)
                    except (HenrikError, TrackerGGError):
                        key = -1
                        label = "API error / private"
                    name = await _display_name(self.bot, guild, row["user_id"])
                    return key, name, label

            results = await asyncio.gather(*[one(r) for r in targets])
            results.sort(key=lambda t: t[0], reverse=True)
            lines = []
            for i, (k, disp, label) in enumerate(results[:20], 1):
                medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"`{i}.`")
                lines.append(f"{medal} **{disp}** — {label}")
            embed = discord.Embed(
                title="Valorant leaderboard (linked accounts)",
                description="\n".join(lines) or "Empty.",
                color=0xFD4556,
            )
            await interaction.followup.send(embed=embed)
            return

        # league
        targets = [
            r
            for r in rows
            if r.get("league_name") and r.get("league_platform")
        ]
        if not targets:
            await interaction.followup.send("No one has linked League in this server yet.")
            return

        async def one_lol(row: dict) -> tuple[int, str, str]:
            async with sem:
                try:
                    data = await league_rank_summary(
                        session,
                        row["league_name"],
                        row["league_tag"],
                        row["league_platform"],
                    )
                    solo = data.get("solo")
                    key = league_sort_key(solo)
                    label = format_league_entry(solo)
                except RiotError:
                    key = -1
                    label = "API error"
                name = await _display_name(self.bot, guild, row["user_id"])
                return key, name, label

        results = await asyncio.gather(*[one_lol(r) for r in targets])
        results.sort(key=lambda t: t[0], reverse=True)
        lines = []
        for i, (k, disp, label) in enumerate(results[:20], 1):
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"`{i}.`")
            lines.append(f"{medal} **{disp}** — {label}")
        embed = discord.Embed(
            title="League Solo/Duo leaderboard (linked accounts)",
            description="\n".join(lines) or "Empty.",
            color=0xC89B3C,
        )
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(LeaderboardCog(bot))
