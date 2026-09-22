import aiohttp
import pytest
from aiohttp import web

from services.gonext import GonextError, Ping, allowed_mentions_for, fetch_due_pings, parse_pings


def test_parse_pings_reads_the_sites_payload():
    payload = {"pings": [{"key": "match-day:m1", "content": "hi <@1>", "mentionUserIds": ["1"]}]}
    assert parse_pings(payload) == [Ping(key="match-day:m1", content="hi <@1>", mention_user_ids=[1])]


@pytest.mark.parametrize(
    "payload",
    [None, {}, {"pings": "nope"}, {"pings": [{"key": "k"}]}, {"pings": [{"key": 1, "content": "x", "mentionUserIds": []}]}],
)
def test_parse_pings_rejects_malformed_payloads(payload):
    with pytest.raises(GonextError):
        parse_pings(payload)


def test_allowed_mentions_only_notify_the_listed_users():
    mentions = allowed_mentions_for(Ping(key="k", content="@everyone <@1>", mention_user_ids=[1, 2]))
    assert mentions.everyone is False
    assert mentions.roles is False
    assert sorted(u.id for u in mentions.users) == [1, 2]


async def _serve(handler):
    app = web.Application()
    app.router.add_get("/api/bot/pings", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    return runner, f"http://127.0.0.1:{port}"


@pytest.mark.asyncio
async def test_fetch_due_pings_sends_the_secret_and_parses_the_reply():
    seen = {}

    async def handler(request):
        seen["auth"] = request.headers.get("Authorization")
        return web.json_response({"pings": [{"key": "k", "content": "c", "mentionUserIds": []}]})

    runner, base = await _serve(handler)
    try:
        async with aiohttp.ClientSession() as session:
            pings = await fetch_due_pings(session, base + "/", "s3cret")
    finally:
        await runner.cleanup()

    assert seen["auth"] == "Bearer s3cret"
    assert pings == [Ping(key="k", content="c", mention_user_ids=[])]


@pytest.mark.asyncio
async def test_fetch_due_pings_raises_on_an_error_status():
    async def handler(request):
        return web.json_response({"error": "Unauthorized."}, status=401)

    runner, base = await _serve(handler)
    try:
        async with aiohttp.ClientSession() as session:
            with pytest.raises(GonextError, match="401"):
                await fetch_due_pings(session, base, "wrong")
    finally:
        await runner.cleanup()
