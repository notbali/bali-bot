import asyncio
import logging
import sys

import aiohttp
import discord
from discord.ext import commands

import db
from config import DISCORD_TOKEN, ENABLE_MEMBERS_INTENT, ENABLE_MESSAGE_CONTENT_INTENT

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("bali-bot")


class BaliBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        if ENABLE_MEMBERS_INTENT:
            intents.members = True
        if ENABLE_MESSAGE_CONTENT_INTENT:
            intents.message_content = True
        intents.voice_states = True
        # Slash-only bot; when_mentioned avoids needing Message Content intent for a dummy prefix.
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            help_command=None,
        )
        self.http_session: aiohttp.ClientSession | None = None

    async def setup_hook(self) -> None:
        self.http_session = aiohttp.ClientSession()
        await self.load_extension("cogs.tracking")
        await self.load_extension("cogs.leaderboard")
        await self.load_extension("cogs.fun")
        await self.load_extension("cogs.patchnotes")
        await self.tree.sync()
        log.info("Slash commands synced.")

    async def close(self) -> None:
        if self.http_session and not self.http_session.closed:
            await self.http_session.close()
        await super().close()


async def main() -> None:
    if not DISCORD_TOKEN:
        log.error("Set DISCORD_TOKEN in .env (see .env.example).")
        sys.exit(1)
    db.init_db()
    bot = BaliBot()
    try:
        async with bot:
            await bot.start(DISCORD_TOKEN)
    except discord.LoginFailure:
        log.error(
            "Discord rejected DISCORD_TOKEN. Fix: Developer Portal → your application → Bot → "
            "copy Token (or Reset Token, then copy). Do not use OAuth2 → Client Secret. "
            "In .env use DISCORD_TOKEN=paste with no spaces or quotes."
        )
        sys.exit(1)
    except discord.PrivilegedIntentsRequired:
        log.error(
            "Privileged intent mismatch. Enable required toggles in Developer Portal → Bot, "
            "or disable env flags. Current flags: DISCORD_ENABLE_MEMBERS_INTENT=%s, "
            "DISCORD_ENABLE_MESSAGE_CONTENT_INTENT=%s",
            ENABLE_MEMBERS_INTENT,
            ENABLE_MESSAGE_CONTENT_INTENT,
        )
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
