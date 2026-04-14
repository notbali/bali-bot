from typing import Any

import aiohttp

from config import (
    ACCOUNT_REGION,
    LOL_PLATFORM_HOSTS,
    PLATFORM_TO_ACCOUNT_REGION,
    RIOT_API_KEY,
)


class RiotError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        super().__init__(message)


def _headers() -> dict[str, str]:
    if not RIOT_API_KEY:
        raise RiotError(0, "RIOT_API_KEY is not set.")
    return {"X-Riot-Token": RIOT_API_KEY}


async def fetch_account_by_riot_id(
    session: aiohttp.ClientSession,
    game_name: str,
    tag_line: str,
    platform: str,
) -> dict[str, Any]:
    cluster = PLATFORM_TO_ACCOUNT_REGION.get(platform.lower())
    if not cluster:
        raise RiotError(0, f"Unknown League platform `{platform}`. Try na1, euw1, kr, …")
    host = ACCOUNT_REGION[cluster]
    from urllib.parse import quote

    url = (
        f"https://{host}/riot/account/v1/accounts/by-riot-id/"
        f"{quote(game_name, safe='')}/{quote(tag_line, safe='')}"
    )
    async with session.get(url, headers=_headers()) as resp:
        if resp.status != 200:
            text = await resp.text()
            raise RiotError(resp.status, text or resp.reason)
        return await resp.json()


async def fetch_summoner_by_puuid(
    session: aiohttp.ClientSession,
    platform: str,
    puuid: str,
) -> dict[str, Any]:
    ph = platform.lower()
    host = LOL_PLATFORM_HOSTS.get(ph)
    if not host:
        raise RiotError(0, f"Unknown League platform `{platform}`.")
    url = f"https://{host}/lol/summoner/v4/summoners/by-puuid/{puuid}"
    async with session.get(url, headers=_headers()) as resp:
        if resp.status != 200:
            text = await resp.text()
            raise RiotError(resp.status, text or resp.reason)
        return await resp.json()


async def fetch_league_entries_by_puuid(
    session: aiohttp.ClientSession,
    platform: str,
    puuid: str,
) -> list[dict[str, Any]]:
    ph = platform.lower()
    host = LOL_PLATFORM_HOSTS.get(ph)
    if not host:
        raise RiotError(0, f"Unknown League platform `{platform}`.")
    url = f"https://{host}/lol/league/v4/entries/by-puuid/{puuid}"
    async with session.get(url, headers=_headers()) as resp:
        if resp.status == 404:
            return []
        if resp.status != 200:
            text = await resp.text()
            raise RiotError(resp.status, text or resp.reason)
        data = await resp.json()
        return data if isinstance(data, list) else []


async def league_rank_summary(
    session: aiohttp.ClientSession,
    game_name: str,
    tag_line: str,
    platform: str,
) -> dict[str, Any]:
    acc = await fetch_account_by_riot_id(session, game_name, tag_line, platform)
    puuid = acc["puuid"]
    entries = await fetch_league_entries_by_puuid(session, platform, puuid)
    solo = next((e for e in entries if e.get("queueType") == "RANKED_SOLO_5x5"), None)
    flex = next((e for e in entries if e.get("queueType") == "RANKED_FLEX_SR"), None)
    summoner_level: int | None = None
    try:
        summ = await fetch_summoner_by_puuid(session, platform, puuid)
        summoner_level = summ.get("summonerLevel")
    except RiotError:
        pass
    return {
        "puuid": puuid,
        "summoner_level": summoner_level,
        "solo": solo,
        "flex": flex,
    }


# Numeric sort key: higher = better (approximate)
TIER_ORDER = [
    "IRON",
    "BRONZE",
    "SILVER",
    "GOLD",
    "PLATINUM",
    "EMERALD",
    "DIAMOND",
    "MASTER",
    "GRANDMASTER",
    "CHALLENGER",
]
RANK_ORDER = ["IV", "III", "II", "I"]


def league_sort_key(entry: dict[str, Any] | None) -> int:
    if not entry:
        return -1
    tier = (entry.get("tier") or "").upper()
    rank = (entry.get("rank") or "").upper()
    lp = int(entry.get("leaguePoints") or 0)
    try:
        ti = TIER_ORDER.index(tier)
    except ValueError:
        ti = 0
    if tier in ("MASTER", "GRANDMASTER", "CHALLENGER"):
        inner = 0
    else:
        try:
            inner = RANK_ORDER.index(rank)
        except ValueError:
            inner = 0
    return ti * 10_000 + inner * 100 + min(lp, 99)


def format_league_entry(entry: dict[str, Any] | None) -> str:
    if not entry:
        return "Unranked"
    tier = (entry.get("tier") or "?").title()
    rank = entry.get("rank") or ""
    lp = entry.get("leaguePoints")
    wr = wins_losses(entry)
    base = f"{tier} {rank}".strip() + (f" · {lp} LP" if lp is not None else "")
    if wr:
        return f"{base} · {wr}"
    return base


def wins_losses(entry: dict[str, Any]) -> str | None:
    w, l = entry.get("wins"), entry.get("losses")
    if w is None or l is None:
        return None
    total = w + l
    if total <= 0:
        return None
    pct = round(100 * w / total)
    return f"{w}W/{l}L ({pct}%)"
