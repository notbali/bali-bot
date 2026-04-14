import discord
from discord import app_commands
from discord.ext import commands

import db
from services.riot import RiotError, format_league_entry, league_rank_summary
from services.valorant import HenrikError, fetch_valorant_mmr, format_valorant_rank


VAL_REGIONS = ["na", "eu", "ap", "kr", "latam"]


def _tracker_2xko_url(name: str, tag: str) -> str:
    from urllib.parse import quote

    return f"https://tracker.gg/2xko/profile/riot/{quote(name, safe='')}%23{quote(tag, safe='')}/overview"


class TrackingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    valorant = app_commands.Group(name="valorant", description="Valorant rank (via Henrik API)")

    @valorant.command(name="link", description="Save your Riot ID and region for this server")
    @app_commands.describe(riot_id="In-game name, e.g. Player#TAG", region="Henrik region")
    @app_commands.choices(
        region=[
            app_commands.Choice(name=n.upper(), value=n)
            for n in VAL_REGIONS
        ]
    )
    async def val_link(
        self,
        interaction: discord.Interaction,
        riot_id: str,
        region: app_commands.Choice[str],
    ):
        parsed = db.parse_riot_id(riot_id)
        if not parsed:
            await interaction.response.send_message(
                "Use Riot ID format: `Player#TAG` (include the `#`).",
                ephemeral=True,
            )
            return
        name, tag = parsed
        assert interaction.guild
        db.save_link(
            interaction.guild.id,
            interaction.user.id,
            valorant_name=name,
            valorant_tag=tag,
            valorant_region=region.value,
        )
        await interaction.response.send_message(
            f"Linked **{name}#{tag}** on **{region.value.upper()}** for Valorant.",
            ephemeral=True,
        )

    @valorant.command(name="rank", description="Show current competitive rank")
    @app_commands.describe(member="Whose rank to look up (defaults to you)")
    async def val_rank(self, interaction: discord.Interaction, member: discord.Member | None = None):
        assert interaction.guild
        target = member or interaction.user
        row = db.get_link(interaction.guild.id, target.id)
        if not row.get("valorant_name"):
            await interaction.response.send_message(
                f"{target.mention} has no Valorant link. Use `/valorant link`.",
                ephemeral=True,
            )
            return
        await interaction.response.defer(thinking=True, ephemeral=True)
        session = self.bot.http_session
        try:
            payload = await fetch_valorant_mmr(
                session,
                row["valorant_region"],
                row["valorant_name"],
                row["valorant_tag"],
            )
            text = format_valorant_rank(payload)
        except HenrikError as e:
            await interaction.followup.send(f"Henrik API error ({e.status}): {e}", ephemeral=True)
            return
        await interaction.followup.send(
            f"**{row['valorant_name']}#{row['valorant_tag']}** — {text}",
            ephemeral=True,
        )

    @valorant.command(name="unlink", description="Remove your Valorant link")
    async def val_unlink(self, interaction: discord.Interaction):
        assert interaction.guild
        db.clear_game(interaction.guild.id, interaction.user.id, "valorant")
        await interaction.response.send_message("Valorant link cleared.", ephemeral=True)

    league = app_commands.Group(name="league", description="League of Legends rank (Riot API)")

    @league.command(name="link", description="Save Riot ID and platform shard for this server")
    @app_commands.describe(
        riot_id="Name#TAG",
        platform="Shard, e.g. na1, euw1, kr — see Riot routing docs",
    )
    async def lol_link(self, interaction: discord.Interaction, riot_id: str, platform: str):
        parsed = db.parse_riot_id(riot_id)
        if not parsed:
            await interaction.response.send_message("Use format `Player#TAG`.", ephemeral=True)
            return
        name, tag = parsed
        plat = platform.lower().strip()
        assert interaction.guild
        db.save_link(
            interaction.guild.id,
            interaction.user.id,
            league_name=name,
            league_tag=tag,
            league_platform=plat,
        )
        await interaction.response.send_message(
            f"Linked **{name}#{tag}** on **`{plat}`** for League.",
            ephemeral=True,
        )

    @league.command(name="rank", description="Show ranked solo/flex")
    @app_commands.describe(member="Defaults to you")
    async def lol_rank(self, interaction: discord.Interaction, member: discord.Member | None = None):
        assert interaction.guild
        target = member or interaction.user
        row = db.get_link(interaction.guild.id, target.id)
        if not row.get("league_name") or not row.get("league_platform"):
            await interaction.response.send_message(
                f"{target.mention} has no League link. Use `/league link`.",
                ephemeral=True,
            )
            return
        await interaction.response.defer(thinking=True, ephemeral=True)
        session = self.bot.http_session
        try:
            data = await league_rank_summary(
                session,
                row["league_name"],
                row["league_tag"],
                row["league_platform"],
            )
        except RiotError as e:
            await interaction.followup.send(f"Riot API error ({e.status}): {e}", ephemeral=True)
            return
        solo = format_league_entry(data.get("solo"))
        flex = format_league_entry(data.get("flex"))
        lvl = data.get("summoner_level")
        await interaction.followup.send(
            f"**{row['league_name']}#{row['league_tag']}** (Lv {lvl})\n"
            f"Solo/Duo: **{solo}**\nFlex: **{flex}**",
            ephemeral=True,
        )

    @league.command(name="unlink", description="Remove League link")
    async def lol_unlink(self, interaction: discord.Interaction):
        assert interaction.guild
        db.clear_game(interaction.guild.id, interaction.user.id, "league")
        await interaction.response.send_message("League link cleared.", ephemeral=True)

    twoxko = app_commands.Group(name="2xko", description="2XKO profile link (Tracker.gg)")

    @twoxko.command(name="link", description="Save Riot ID for quick Tracker.gg links")
    async def tk_link(self, interaction: discord.Interaction, riot_id: str):
        parsed = db.parse_riot_id(riot_id)
        if not parsed:
            await interaction.response.send_message("Use format `Player#TAG`.", ephemeral=True)
            return
        name, tag = parsed
        assert interaction.guild
        db.save_link(interaction.guild.id, interaction.user.id, twoxko_name=name, twoxko_tag=tag)
        url = _tracker_2xko_url(name, tag)
        await interaction.response.send_message(
            f"Linked **{name}#{tag}**.\nTracker: {url}",
            ephemeral=True,
        )

    @twoxko.command(name="profile", description="Open your 2XKO Tracker.gg page")
    @app_commands.describe(member="Defaults to you")
    async def tk_profile(self, interaction: discord.Interaction, member: discord.Member | None = None):
        assert interaction.guild
        target = member or interaction.user
        row = db.get_link(interaction.guild.id, target.id)
        if not row.get("twoxko_name"):
            await interaction.response.send_message(
                f"{target.mention} has no 2XKO link. Use `/2xko link`.",
                ephemeral=True,
            )
            return
        url = _tracker_2xko_url(row["twoxko_name"], row["twoxko_tag"])
        await interaction.response.send_message(url, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(TrackingCog(bot))
