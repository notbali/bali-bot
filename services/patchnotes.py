import re

import aiohttp


class PatchNotesError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        super().__init__(message)


PATCH_SOURCE = {
    "league": "https://www.leagueoflegends.com/en-us/news/tags/patch-notes/",
    "valorant": "https://playvalorant.com/en-us/news/tags/patch-notes/",
}


def _extract_title(html: str) -> str:
    m = re.search(r"<title>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    if not m:
        return ""
    t = re.sub(r"\s+", " ", m.group(1)).strip()
    return t


async def fetch_latest_patchnote(
    session: aiohttp.ClientSession,
    game: str,
) -> tuple[str, str]:
    source = PATCH_SOURCE.get(game)
    if not source:
        raise PatchNotesError(0, f"Unsupported game `{game}`.")
    async with session.get(source) as resp:
        text = await resp.text()
        if resp.status != 200:
            raise PatchNotesError(resp.status, text[:500] or resp.reason)
        # Current Riot pages usually canonicalize to the newest patch article.
        latest_url = str(resp.url)
        title = _extract_title(text)
        return latest_url, title
