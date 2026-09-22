"""Client for GO//NEXT's bot API, which decides which Premier pings are due."""

from dataclasses import dataclass
from typing import Any

import aiohttp
import discord


class GonextError(Exception):
    pass


@dataclass(frozen=True)
class Ping:
    # Stable id for this ping (e.g. "match-day:<match id>"); post each key once.
    key: str
    content: str
    # The only users the message may notify.
    mention_user_ids: list[int]


def parse_pings(payload: Any) -> list[Ping]:
    if not isinstance(payload, dict) or not isinstance(payload.get("pings"), list):
        raise GonextError("Unexpected response from GO//NEXT.")
    pings = []
    for raw in payload["pings"]:
        try:
            key, content, ids = raw["key"], raw["content"], raw["mentionUserIds"]
        except (KeyError, TypeError) as e:
            raise GonextError("Malformed ping from GO//NEXT.") from e
        if not isinstance(key, str) or not isinstance(content, str) or not isinstance(ids, list):
            raise GonextError("Malformed ping from GO//NEXT.")
        pings.append(Ping(key=key, content=content, mention_user_ids=[int(i) for i in ids]))
    return pings


def allowed_mentions_for(ping: Ping) -> discord.AllowedMentions:
    # Only the teammates GO//NEXT listed — never @everyone or roles, even if a
    # display name in the message happens to contain one.
    return discord.AllowedMentions(
        everyone=False,
        roles=False,
        users=[discord.Object(id=i) for i in ping.mention_user_ids],
    )


async def fetch_due_pings(session: aiohttp.ClientSession, base_url: str, secret: str) -> list[Ping]:
    url = base_url.rstrip("/") + "/api/bot/pings"
    async with session.get(
        url,
        headers={"Authorization": f"Bearer {secret}"},
        timeout=aiohttp.ClientTimeout(total=15),
    ) as resp:
        if resp.status != 200:
            raise GonextError(f"GO//NEXT returned {resp.status}.")
        return parse_pings(await resp.json())
