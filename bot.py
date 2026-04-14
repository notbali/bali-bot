import asyncio
import logging
import sys

import aiohttp
import discord
from discord.ext import commands

import db
from config import DISCORD_TOKEN

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("bali-bot")


class BaliBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.members = True
        intents.voice_states = True
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.http_session: aiohttp.ClientSession | None = None

    async def setup_hook(self) -> None:
        self.http_session = aiohttp.ClientSession()
        await self.load_extension("cogs.tracking")
        await self.load_extension("cogs.leaderboard")
        await self.load_extension("cogs.fun")
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
    async with bot:
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
