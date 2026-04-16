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


def _extract_latest_article_url(html: str, game: str) -> str | None:
    domain = "leagueoflegends.com" if game == "league" else "playvalorant.com"
    # Riot tag pages frequently use relative links in HTML; support both absolute and relative.
    abs_pattern = rf"https://(?:www\.)?{re.escape(domain)}/en-us/news/game-updates/[a-z0-9-]+"
    rel_pattern = r"/en-us/news/game-updates/[a-z0-9-]+"

    matches: list[str] = []
    matches.extend(re.findall(abs_pattern, html, flags=re.IGNORECASE))
    matches.extend(re.findall(rel_pattern, html, flags=re.IGNORECASE))
    if not matches:
        return None

    # Keep page order and de-duplicate (case-insensitive).
    seen: set[str] = set()
    ordered: list[str] = []
    for m in matches:
        url = m
        if url.startswith("/"):
            url = f"https://www.{domain}{url}"
        k = url.lower()
        if k in seen:
            continue
        seen.add(k)
        ordered.append(url)

    return ordered[0] if ordered else None


def _clean_title(title: str) -> str:
    t = title.strip()
    if " - " in t:
        t = t.split(" - ", 1)[0].strip()
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

    latest_url = _extract_latest_article_url(text, game)
    if not latest_url:
        raise PatchNotesError(0, "Could not find a patch notes article URL on source page.")

    title = ""
    async with session.get(latest_url) as article_resp:
        article_html = await article_resp.text()
        if article_resp.status == 200:
            title = _clean_title(_extract_title(article_html))

    return latest_url, title


async def fetch_page_title(session: aiohttp.ClientSession, url: str) -> str:
    async with session.get(url) as resp:
        html = await resp.text()
        if resp.status != 200:
            return ""
        return _clean_title(_extract_title(html))
