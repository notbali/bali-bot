import asyncio
import os
import random
import tempfile
import discord
import edge_tts
from discord import app_commands
from discord.ext import commands


def _mock_text(s: str) -> str:
    return "".join(c.upper() if random.random() > 0.5 else c.lower() for c in s)


class FunCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

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

    @app_commands.command(
        name="tts",
        description="Join your voice channel and read text aloud (needs FFmpeg installed)",
    )
    @app_commands.describe(text="What to speak", voice="Edge TTS voice name")
    async def tts_cmd(
        self,
        interaction: discord.Interaction,
        text: str,
        voice: str = "en-US-GuyNeural",
    ):
        if not interaction.user or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Use this from a server.", ephemeral=True)
            return
        vc_state = interaction.user.voice
        if not vc_state or not vc_state.channel:
            await interaction.response.send_message("Join a voice channel first.", ephemeral=True)
            return
        if len(text) > 500:
            await interaction.response.send_message("Keep it under 500 characters for TTS.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        path = tmp.name
        tmp.close()

        try:
            com = edge_tts.Communicate(text=text, voice=voice)
            await com.save(path)
        except Exception as e:
            if os.path.isfile(path):
                try:
                    os.unlink(path)
                except OSError:
                    pass
            await interaction.followup.send(f"TTS generation failed: {e}", ephemeral=True)
            return

        assert interaction.guild is not None
        channel = vc_state.channel
        voice_client: discord.VoiceClient | None = interaction.guild.voice_client

        try:
            if voice_client and voice_client.is_connected():
                if voice_client.channel.id != channel.id:
                    await voice_client.move_to(channel)
            else:
                voice_client = await channel.connect()
        except discord.ClientException as e:
            try:
                os.unlink(path)
            except OSError:
                pass
            await interaction.followup.send(f"Could not join voice: {e}", ephemeral=True)
            return

        assert voice_client is not None
        loop = interaction.client.loop
        done = asyncio.Event()

        def after_play(_err: BaseException | None) -> None:
            asyncio.run_coroutine_threadsafe(_cleanup_voice(loop, voice_client, path, done), loop)

        voice_client.stop()
        source = discord.FFmpegPCMAudio(path)
        voice_client.play(source, after=after_play)
        await interaction.followup.send("Speaking…", ephemeral=True)
        try:
            await asyncio.wait_for(done.wait(), timeout=120)
        except asyncio.TimeoutError:
            voice_client.stop()
            await _disconnect_safe(voice_client)
            try:
                os.unlink(path)
            except OSError:
                pass


async def _disconnect_safe(vc: discord.VoiceClient | None) -> None:
    if vc and vc.is_connected():
        await vc.disconnect()


async def _cleanup_voice(
    loop: asyncio.AbstractEventLoop,
    voice_client: discord.VoiceClient,
    path: str,
    done: asyncio.Event,
) -> None:
    try:
        await asyncio.sleep(0.3)
        await _disconnect_safe(voice_client)
    finally:
        try:
            if os.path.isfile(path):
                os.unlink(path)
        except OSError:
            pass
        done.set()


async def setup(bot: commands.Bot):
    await bot.add_cog(FunCog(bot))
