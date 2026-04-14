import re
from typing import Any
from urllib.parse import quote

import aiohttp

from config import (
    HENRIK_API_KEY,
    HENRIK_BASE,
    TRACKER_GG_API_BASE,
    TRACKER_GG_API_KEY,
    VALORANT_RANK_PROVIDER,
)


class HenrikError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        super().__init__(message)


class TrackerGGError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        super().__init__(message)


VAL_TIERS = [
    "IRON",
    "BRONZE",
    "SILVER",
    "GOLD",
    "PLATINUM",
    "DIAMOND",
    "ASCENDANT",
    "IMMORTAL",
    "RADIANT",
]


def _henrik_headers() -> dict[str, str]:
    h: dict[str, str] = {}
    if HENRIK_API_KEY:
        h["Authorization"] = HENRIK_API_KEY
    return h


def _trn_error_message(body: Any) -> str | None:
    if not isinstance(body, dict):
        return None
    errs = body.get("errors")
    if isinstance(errs, list) and errs:
        e0 = errs[0]
        if isinstance(e0, dict):
            return str(e0.get("message") or e0.get("code") or "")
    return None


def _trn_display(stat: Any) -> str | None:
    if isinstance(stat, dict):
        dv = stat.get("displayValue")
        if dv is not None and str(dv).strip():
            return str(dv).strip()
    return None


def _trn_numeric(stat: Any) -> int | None:
    if isinstance(stat, dict):
        v = stat.get("value")
        if v is not None:
            try:
                return int(float(v))
            except (TypeError, ValueError):
                pass
    return None


def _looks_like_val_rank(text: str) -> bool:
    u = text.upper()
    return any(t in u for t in VAL_TIERS)


def _sort_key_from_rank_label(label: str) -> int:
    u = label.upper()
    ti = -1
    for i, t in enumerate(VAL_TIERS):
        if t in u.replace(" ", ""):
            ti = i
            break
    if ti < 0:
        return 0
    m = re.search(r"(\d)\b", label)
    div = int(m.group(1)) if m else 2
    return ti * 100 + min(max(div, 1), 3) * 10


def _resolve_provider() -> str:
    p = VALORANT_RANK_PROVIDER
    if p in ("tracker", "henrik"):
        return p
    return "tracker" if TRACKER_GG_API_KEY else "henrik"


def _normalize_henrik(body: dict[str, Any]) -> dict[str, Any]:
    d = body.get("data") or body
    current = d.get("current_data") if isinstance(d, dict) else None
    if not isinstance(current, dict):
        current = d

    label = (
        current.get("currenttierpatched")
        or current.get("currenttier_patched")
        or d.get("currenttierpatched")
        or d.get("currenttier_patched")
    )
    rr = current.get("ranking_in_tier")
    if rr is None:
        rr = d.get("ranking_in_tier")
    elo = current.get("elo")
    if elo is None:
        elo = d.get("elo")
    tier_raw = current.get("currenttier")
    if tier_raw is None:
        tier_raw = d.get("currenttier")
    try:
        tier = int(tier_raw or 0)
    except (TypeError, ValueError):
        tier = 0

    if not label and tier == 0:
        label = "Unranked"

    return {
        "currenttierpatched": label,
        "ranking_in_tier": rr,
        "elo": elo,
        "currenttier": tier,
        "_source": "henrik",
    }


def _normalize_tracker(body: dict[str, Any]) -> dict[str, Any]:
    data = body.get("data") or {}
    segments = data.get("segments") or []

    rank_candidates: list[str] = []
    rr_num: int | None = None
    elo: int | None = None

    for seg in segments:
        stats = seg.get("stats") or {}
        if not isinstance(stats, dict):
            continue
        for key, stat in stats.items():
            kl = key.lower()
            dv = _trn_display(stat)
            ev = _trn_numeric(stat)

            if dv and _looks_like_val_rank(dv):
                rank_candidates.append(dv)

            if "rankrating" in kl or kl in ("rr", "actrankrating"):
                if ev is not None:
                    rr_num = ev
                elif dv:
                    m = re.search(r"(\d+)", dv)
                    if m:
                        rr_num = int(m.group(1))

            if (kl == "elo" or kl.endswith("elo")) and "rank" not in kl and ev is not None:
                elo = ev

    rank_label = max(rank_candidates, key=_sort_key_from_rank_label) if rank_candidates else None

    return {
        "currenttierpatched": rank_label or "Unknown",
        "ranking_in_tier": rr_num,
        "elo": elo,
        "currenttier": 0,
        "_source": "tracker.gg",
    }


async def _fetch_henrik_raw(
    session: aiohttp.ClientSession,
    region: str,
    name: str,
    tag: str,
) -> dict[str, Any]:
    reg = region.lower().strip()
    path = f"{HENRIK_BASE}/valorant/v2/mmr/{reg}/{quote(name, safe='')}/{quote(tag, safe='')}"
    async with session.get(path, headers=_henrik_headers()) as resp:
        body = await resp.json()
        if resp.status != 200:
            msg = body.get("errors", [{}])[0].get("message") if isinstance(body, dict) else None
            raise HenrikError(resp.status, msg or await resp.text() or resp.reason)
        return body


async def _fetch_tracker_raw(
    session: aiohttp.ClientSession,
    name: str,
    tag: str,
) -> dict[str, Any]:
    if not TRACKER_GG_API_KEY:
        raise TrackerGGError(0, "TRACKER_GG_API_KEY is not set.")
    path = quote(f"{name}#{tag}", safe="")
    url = f"{TRACKER_GG_API_BASE}/valorant/standard/profile/riot/{path}"
    headers = {"TRN-Api-Key": TRACKER_GG_API_KEY}
    async with session.get(url, headers=headers) as resp:
        try:
            body = await resp.json()
        except Exception:
            text = await resp.text()
            raise TrackerGGError(resp.status, text or resp.reason)
        if resp.status != 200:
            msg = _trn_error_message(body) or (body if isinstance(body, str) else None)
            if not msg and isinstance(body, dict):
                msg = str(body)[:500]
            raise TrackerGGError(resp.status, str(msg or resp.reason))
        return body


async def fetch_valorant_mmr(
    session: aiohttp.ClientSession,
    region: str,
    name: str,
    tag: str,
) -> dict[str, Any]:
    prov = _resolve_provider()
    if prov == "henrik":
        raw = await _fetch_henrik_raw(session, region, name, tag)
        return _normalize_henrik(raw)
    if prov == "tracker":
        raw = await _fetch_tracker_raw(session, name, tag)
        return _normalize_tracker(raw)

    # auto
    if TRACKER_GG_API_KEY:
        try:
            raw = await _fetch_tracker_raw(session, name, tag)
            return _normalize_tracker(raw)
        except TrackerGGError as e:
            if e.status == 404:
                raw = await _fetch_henrik_raw(session, region, name, tag)
                return _normalize_henrik(raw)
            raise
    raw = await _fetch_henrik_raw(session, region, name, tag)
    return _normalize_henrik(raw)


def valorant_sort_key(norm: dict[str, Any]) -> int:
    elo = norm.get("elo")
    if elo is not None:
        try:
            return int(elo)
        except (TypeError, ValueError):
            pass
    tier = int(norm.get("currenttier") or 0)
    rr = int(norm.get("ranking_in_tier") or 0)
    if tier > 0 or rr:
        return tier * 100 + min(rr, 99)
    label = norm.get("currenttierpatched") or ""
    return _sort_key_from_rank_label(label)


def format_valorant_rank(norm: dict[str, Any]) -> str:
    label = norm.get("currenttierpatched") or "Unknown"
    rr = norm.get("ranking_in_tier")
    parts = [str(label)]
    if rr is not None and f"{rr}" not in label:
        parts.append(f"{rr} RR")
    return " · ".join(parts)
