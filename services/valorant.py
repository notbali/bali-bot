from typing import Any
from urllib.parse import quote

import aiohttp

from config import HENRIK_API_KEY, HENRIK_BASE


class HenrikError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        super().__init__(message)


def _headers() -> dict[str, str]:
    h: dict[str, str] = {}
    if HENRIK_API_KEY:
        h["Authorization"] = HENRIK_API_KEY
    return h


async def fetch_valorant_mmr(
    session: aiohttp.ClientSession,
    region: str,
    name: str,
    tag: str,
) -> dict[str, Any]:
    reg = region.lower().strip()
    path = f"{HENRIK_BASE}/valorant/v2/mmr/{reg}/{quote(name, safe='')}/{quote(tag, safe='')}"
    async with session.get(path, headers=_headers()) as resp:
        body = await resp.json()
        if resp.status != 200:
            msg = body.get("errors", [{}])[0].get("message") if isinstance(body, dict) else None
            raise HenrikError(resp.status, msg or await resp.text() or resp.reason)
        return body


def valorant_sort_key(data: dict[str, Any]) -> int:
    d = data.get("data") or data
    elo = d.get("elo")
    if elo is not None:
        try:
            return int(elo)
        except (TypeError, ValueError):
            pass
    tier = int(d.get("currenttier") or 0)
    rr = int(d.get("ranking_in_tier") or 0)
    return tier * 100 + min(rr, 99)


def format_valorant_rank(payload: dict[str, Any]) -> str:
    d = payload.get("data") or payload
    label = d.get("currenttierpatched") or d.get("currenttier_patched") or "Unknown"
    rr = d.get("ranking_in_tier")
    elo = d.get("elo")
    parts = [str(label)]
    if rr is not None:
        parts.append(f"{rr} RR")
    if elo is not None:
        parts.append(f"elo {elo}")
    return " · ".join(parts)
