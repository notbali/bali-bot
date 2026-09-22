import db


def test_premier_channel_round_trip():
    assert db.get_premier_channel(1) is None
    db.set_premier_channel(1, 555)
    assert db.get_premier_channel(1) == 555
    db.set_premier_channel(1, 777)
    assert db.get_premier_channel(1) == 777


def test_clear_premier_channel():
    db.set_premier_channel(1, 555)
    db.clear_premier_channel(1)
    assert db.get_premier_channel(1) is None


def test_all_premier_channels():
    db.set_premier_channel(1, 555)
    db.set_premier_channel(2, 666)
    assert sorted((r["guild_id"], r["channel_id"]) for r in db.all_premier_channels()) == [(1, 555), (2, 666)]


def test_posted_ping_keys_are_per_guild():
    assert not db.premier_ping_posted(1, "match-day:m1")
    db.mark_premier_ping_posted(1, "match-day:m1")
    assert db.premier_ping_posted(1, "match-day:m1")
    assert not db.premier_ping_posted(2, "match-day:m1")


def test_marking_a_ping_twice_is_harmless():
    db.mark_premier_ping_posted(1, "k")
    db.mark_premier_ping_posted(1, "k")
    assert db.premier_ping_posted(1, "k")
