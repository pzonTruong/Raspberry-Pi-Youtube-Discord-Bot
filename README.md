# Pi-Yt Music Discord Bot

A simple Discord music bot that plays audio from YouTube links in voice channels using `bot.py`.

## What it does

- Joins a voice channel when a user issues `!play <url>`
- Streams audio using `yt_dlp` and `ffmpeg`
- Supports queueing additional tracks
- Includes `!skip` and `!stop` commands

## Files

- `bot.py` — main bot implementation
- `GUIDE.md` — Raspberry Pi setup and usage instructions

## Quick start

1. Install Python and `ffmpeg`.
2. Install the dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install discord.py yt_dlp python-dotenv
```

3. Create a `.env` file in the project root with your bot token:

```env
DISCORD_TOKEN=your_discord_bot_token_here
```

4. Run the bot:

```bash
python3 bot.py
```

## Commands

- `!play <url>` — queue a YouTube/audio link and play it
- `!pause` — pause or resume playback
- `!queue` — show upcoming queue items
- `!skip` — skip the current track
- `!stop` — clear the queue and disconnect

## Raspberry Pi

See `GUIDE.md` for Raspberry Pi-specific installation and running instructions.

## Notes

- The bot requires `ffmpeg` to stream audio.
- The bot loads its token from the `DISCORD_TOKEN` environment variable, usually set in a `.env` file.
- Keep your Discord bot token secret.
- The queue is stored only in memory and resets when the bot restarts.
