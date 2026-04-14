import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parent / "bali_bot.sqlite3"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_conn():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS links (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                valorant_name TEXT,
                valorant_tag TEXT,
                valorant_region TEXT,
                league_name TEXT,
                league_tag TEXT,
                league_platform TEXT,
                twoxko_name TEXT,
                twoxko_tag TEXT,
                PRIMARY KEY (guild_id, user_id)
            )
            """
        )


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any]:
    if row is None:
        return {}
    return {k: row[k] for k in row.keys()}


def get_link(guild_id: int, user_id: int) -> dict[str, Any]:
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT * FROM links WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        return _row_to_dict(cur.fetchone())


def save_link(
    guild_id: int,
    user_id: int,
    *,
    valorant_name: str | None = None,
    valorant_tag: str | None = None,
    valorant_region: str | None = None,
    league_name: str | None = None,
    league_tag: str | None = None,
    league_platform: str | None = None,
    twoxko_name: str | None = None,
    twoxko_tag: str | None = None,
    _clear_valorant: bool = False,
    _clear_league: bool = False,
    _clear_2xko: bool = False,
) -> None:
    cur = get_link(guild_id, user_id)

    def pick(
        key: str,
        new_val: str | None,
        cleared: bool,
    ) -> str | None:
        if cleared:
            return None
        if new_val is not None:
            return new_val
        return cur.get(key)

    vn = pick("valorant_name", valorant_name, _clear_valorant)
    vt = pick("valorant_tag", valorant_tag, _clear_valorant)
    vr = pick("valorant_region", valorant_region, _clear_valorant)
    ln = pick("league_name", league_name, _clear_league)
    lt = pick("league_tag", league_tag, _clear_league)
    lp = pick("league_platform", league_platform, _clear_league)
    tk_n = pick("twoxko_name", twoxko_name, _clear_2xko)
    tk_t = pick("twoxko_tag", twoxko_tag, _clear_2xko)

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO links (guild_id, user_id, valorant_name, valorant_tag, valorant_region,
                league_name, league_tag, league_platform, twoxko_name, twoxko_tag)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET
                valorant_name = excluded.valorant_name,
                valorant_tag = excluded.valorant_tag,
                valorant_region = excluded.valorant_region,
                league_name = excluded.league_name,
                league_tag = excluded.league_tag,
                league_platform = excluded.league_platform,
                twoxko_name = excluded.twoxko_name,
                twoxko_tag = excluded.twoxko_tag
            """,
            (guild_id, user_id, vn, vt, vr, ln, lt, lp, tk_n, tk_t),
        )


def clear_game(guild_id: int, user_id: int, game: str) -> None:
    if game == "valorant":
        save_link(guild_id, user_id, _clear_valorant=True)
    elif game == "league":
        save_link(guild_id, user_id, _clear_league=True)
    elif game == "2xko":
        save_link(guild_id, user_id, _clear_2xko=True)


def all_links_for_guild(guild_id: int) -> list[dict[str, Any]]:
    with get_conn() as conn:
        cur = conn.execute("SELECT * FROM links WHERE guild_id = ?", (guild_id,))
        return [_row_to_dict(r) for r in cur.fetchall()]


def parse_riot_id(s: str) -> tuple[str, str] | None:
    s = s.strip()
    if "#" not in s:
        return None
    name, tag = s.rsplit("#", 1)
    name, tag = name.strip(), tag.strip()
    if not name or not tag:
        return None
    return name, tag
