import random
import re
import time
import discord
from discord import app_commands
from discord.ext import commands


def _mock_text(s: str) -> str:
    return "".join(c.upper() if random.random() > 0.5 else c.lower() for c in s)


class FunCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._last_auto_reply_channel_id: int | None = None
        self._last_auto_reply_message_id: int | None = None
        self._last_auto_reply_at: float = 0.0

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        if not message.guild:
            return
        if not message.content:
            return
        content = message.content.lower()

        # Phrase-based auto replies.
        phrase_replies = (
            ("shut up momo", "YEAH BRUH SHUT UR MOUTH"),
            ("rara", "A BAD TAKE FROM RARA AGAIN? TYPICAL"),
            ("chud", "THE BIGGEST CHUD OF ALL"),
            ("twice", "TWICE? IS THAT TWICE?? THE KPOP GROUP? I LOVE TWICE!!!")
        )
        for phrase, reply in phrase_replies:
            if phrase in content:
                sent = await message.reply(reply, mention_author=False)
                self._last_auto_reply_channel_id = sent.channel.id
                self._last_auto_reply_message_id = sent.id
                self._last_auto_reply_at = time.monotonic()
                return

        # If someone tells the bot to shut up right after an auto-reply,
        # react with a sad face on that auto-reply message.
        if re.search(r"\bshut up\b", content):
            if (
                self._last_auto_reply_channel_id == message.channel.id
                and self._last_auto_reply_message_id is not None
                and (time.monotonic() - self._last_auto_reply_at) <= 20
            ):
                try:
                    auto_reply = await message.channel.fetch_message(self._last_auto_reply_message_id)
                    await auto_reply.add_reaction("😔")
                except discord.HTTPException:
                    await message.add_reaction("😔")
                return

    @app_commands.command(name="say", description="The bot repeats your text in this channel")
    @app_commands.describe(text="What to say")
    async def say_cmd(self, interaction: discord.Interaction, text: str):
        if len(text) > 1900:
            await interaction.response.send_message("Too long (max ~1900 chars).", ephemeral=True)
            return
        await interaction.response.send_message("Sent.", ephemeral=True)
        await interaction.channel.send(text)

    @app_commands.command(name="clap", description="Add clap between every word")
    async def clap_cmd(self, interaction: discord.Interaction, text: str):
        parts = text.split()
        if not parts:
            await interaction.response.send_message("Give me words.", ephemeral=True)
            return
        out = " 👏 ".join(parts)
        await interaction.response.send_message(out[:2000])

    @app_commands.command(name="mock", description="sPoNgEbOb case")
    async def mock_cmd(self, interaction: discord.Interaction, text: str):
        await interaction.response.send_message(_mock_text(text)[:2000])


async def setup(bot: commands.Bot):
    await bot.add_cog(FunCog(bot))
