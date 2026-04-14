import os

from dotenv import load_dotenv

load_dotenv()


def _normalize_discord_token(raw: str | None) -> str:
    s = (raw or "").strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        s = s[1:-1].strip()
    if s.startswith("\ufeff"):
        s = s.lstrip("\ufeff").strip()
    return s


DISCORD_TOKEN = _normalize_discord_token(os.getenv("DISCORD_TOKEN"))

# Requires "Server Members Intent" on the Bot tab + DISCORD_ENABLE_MEMBERS_INTENT=1
ENABLE_MEMBERS_INTENT = os.getenv("DISCORD_ENABLE_MEMBERS_INTENT", "").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)

# Requires "Message Content Intent" on the Bot tab + DISCORD_ENABLE_MESSAGE_CONTENT_INTENT=1
ENABLE_MESSAGE_CONTENT_INTENT = os.getenv(
    "DISCORD_ENABLE_MESSAGE_CONTENT_INTENT", ""
).strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)

RIOT_API_KEY = os.getenv("RIOT_API_KEY", "")
HENRIK_API_KEY = os.getenv("HENRIK_API_KEY", "")
TRACKER_GG_API_KEY = os.getenv("TRACKER_GG_API_KEY", "").strip()

# Valorant rank source: auto (Tracker if TRACKER_GG_API_KEY else Henrik), tracker, henrik
VALORANT_RANK_PROVIDER = os.getenv("VALORANT_RANK_PROVIDER", "auto").strip().lower()

HENRIK_BASE = "https://api.henrikdev.xyz"
TRACKER_GG_API_BASE = "https://public-api.tracker.gg/api/v2"

# Riot account routing (where account-v1 lives)
ACCOUNT_REGION = {
    "americas": "americas.api.riotgames.com",
    "europe": "europe.api.riotgames.com",
    "asia": "asia.api.riotgames.com",
    "sea": "sea.api.riotgames.com",
}

# LoL platform host (gameplay APIs)
LOL_PLATFORM_HOSTS = {
    "na1": "na1.api.riotgames.com",
    "euw1": "euw1.api.riotgames.com",
    "eun1": "eun1.api.riotgames.com",
    "kr": "kr.api.riotgames.com",
    "br1": "br1.api.riotgames.com",
    "la1": "la1.api.riotgames.com",
    "la2": "la2.api.riotgames.com",
    "oc1": "oc1.api.riotgames.com",
    "tr1": "tr1.api.riotgames.com",
    "ru": "ru.api.riotgames.com",
    "jp1": "jp1.api.riotgames.com",
    "ph2": "ph2.api.riotgames.com",
    "sg2": "sg2.api.riotgames.com",
    "th2": "th2.api.riotgames.com",
    "tw2": "tw2.api.riotgames.com",
    "vn2": "vn2.api.riotgames.com",
}

# Map LoL platform -> account-v1 routing cluster
PLATFORM_TO_ACCOUNT_REGION = {
    "na1": "americas",
    "br1": "americas",
    "la1": "americas",
    "la2": "americas",
    "oc1": "americas",
    "euw1": "europe",
    "eun1": "europe",
    "tr1": "europe",
    "ru": "europe",
    "kr": "asia",
    "jp1": "asia",
    "ph2": "sea",
    "sg2": "sea",
    "th2": "sea",
    "tw2": "sea",
    "vn2": "sea",
}
