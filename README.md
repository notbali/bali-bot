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

## Discord Developer Portal Setup

In your bot application:
- Enable **Message Content Intent** if using phrase triggers
- Enable **Server Members Intent** only if you set `DISCORD_ENABLE_MEMBERS_INTENT=1`
- Invite bot with:
  - `bot`
  - `applications.commands`

## Railway Deployment

This project is deployed on Railway.

Recommended settings:
- Start Command: `python bot.py`
- Environment: add the same variables from `.env` in Railway service variables

After deploy, logs should include:
- `Slash commands synced.`
- `Shard ID None has connected to Gateway`

## Data / Persistence Note

This bot currently uses SQLite (`bali_bot.sqlite3`).

If Railway service storage is reset/redeployed, SQLite data may be lost unless you use persistent storage.
For production persistence, migrate to a managed DB (Postgres recommended).

