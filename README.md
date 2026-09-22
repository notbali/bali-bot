# bali-bot

Discord bot for:
- Valorant rank tracking
- League of Legends rank tracking
- Server leaderboards
- Fun auto-replies and text commands

## Features

- `/valorant link`, `/valorant rank`, `/valorant unlink`
- `/league link`, `/league rank`, `/league unlink`
- `/leaderboard` (Valorant + League)
- Fun commands: `/say`, `/clap`, `/mock`
- Patch notes: `/patchnotes set-channel`, `/patchnotes post` (optional URL; Discord native link preview), `/patchnotes clear-channel` (auto-post hourly)
- Premier pings from [GO//NEXT](https://github.com/notbali/gonext): `/premier set-channel`, `/premier clear-channel`, `/premier check` (polls every 5 minutes; @s teammates on match days, 30 minutes before a match, and Sunday evenings for unset availability)
- Phrase triggers in chat (for example `chud`, `shut up momo`, `rara`)

## Local Run

1. Create and activate a virtual environment
2. Install dependencies
3. Copy `.env.example` to `.env` and fill values
4. Run:

```bash
python bot.py
```

## Required Environment Variables

- `DISCORD_TOKEN`
- `RIOT_API_KEY` (for League)

## Optional Environment Variables

- `HENRIK_API_KEY` (Valorant provider)
- `TRACKER_GG_API_KEY` (if using Tracker provider)
- `VALORANT_RANK_PROVIDER` (`auto`, `henrik`, `tracker`)
- `DISCORD_ENABLE_MESSAGE_CONTENT_INTENT` (`1` to enable phrase listener)
- `DISCORD_ENABLE_MEMBERS_INTENT` (`1` if Server Members Intent is enabled in Discord portal)
- `GONEXT_URL` / `GONEXT_BOT_SECRET` (Premier pings; the secret matches GO//NEXT's `BOT_API_SECRET`)

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

## Discord Developer Portal Setup

In your bot application:
- Enable **Message Content Intent** if using phrase triggers
- Enable **Server Members Intent** only if you set `DISCORD_ENABLE_MEMBERS_INTENT=1`
- Invite bot with:
  - `bot`
  - `applications.commands`

## Self-Hosted Deployment

The bot runs on a self-hosted Linux server (Python 3.10+). It only makes outbound
connections (Discord, Riot, GO//NEXT), so no ports need to be opened.

1. Clone the repo, create a virtual environment, and `pip install -r requirements.txt`
2. Put the variables above in `.env` next to `bot.py`
3. Run it as a service so it restarts after a crash or reboot, e.g. with systemd
   (`/etc/systemd/system/bali-bot.service`, adjusting paths and user):

```ini
[Unit]
Description=bali-bot
After=network-online.target
Wants=network-online.target

[Service]
User=bali
WorkingDirectory=/home/bali/bali-bot
ExecStart=/home/bali/bali-bot/.venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then `sudo systemctl enable --now bali-bot` and follow logs with `journalctl -u bali-bot -f`.

After start, logs should include:
- `Slash commands synced.`
- `Shard ID None has connected to Gateway`

## Data / Persistence Note

This bot uses SQLite (`bali_bot.sqlite3`, next to `bot.py`). It persists on the server's disk, including
which GO//NEXT pings have already been posted, so back it up if you move servers.
