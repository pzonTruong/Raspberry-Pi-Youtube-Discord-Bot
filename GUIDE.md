# Pi-Yt Music Discord Bot Guide

## Overview

This guide explains how to set up and run `bot.py` on a Raspberry Pi. The bot lets Discord users queue YouTube audio into a voice channel using commands like `!play`, `!skip`, and `!stop`.

## Prerequisites

1. Raspberry Pi running Raspberry Pi OS or another Debian-based Linux.
2. Internet access for package installation and Discord/YouTube streaming.
3. A Discord bot token and a server where you can invite the bot.

## Install required system packages

Open a terminal on the Pi and run:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip ffmpeg
```

> `ffmpeg` is required to stream audio into Discord voice channels.

## Set up the project

From the project folder:

```bash
cd ~/Pi-Yt-Music-Discord-Bot
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install discord.py yt_dlp python-dotenv
```

If you prefer not to use a virtual environment, install packages globally with:

```bash
pip3 install --upgrade discord.py yt_dlp python-dotenv
```

## Configure the bot token

Open `bot.py` and replace `YOUR_BOT_TOKEN_HERE` with your actual Discord bot token, or use a `.env` file.

### Option 1: Hardcode the token (not recommended)

```python
bot.run('YOUR_BOT_TOKEN_HERE')
```

### Option 2: Use a `.env` file (recommended)

Create a file named `.env` in the project root with this content:

```env
DISCORD_TOKEN=your_discord_bot_token_here
```

Then run the bot normally. The script loads `DISCORD_TOKEN` from the environment automatically.

> Keep your `.env` file secret and do not commit it to git. Add `.env` to `.gitignore` if you create one.

## Invite the bot to your server

1. Go to the Discord Developer Portal.
2. Open your application and go to the "OAuth2" section.
3. Under "URL Generator", select these scopes:
   - `bot`
   - `applications.commands` (optional if you plan to extend commands later)
4. Under Bot Permissions, add:
   - `Connect`
   - `Speak`
   - `Send Messages`
   - `View Channels`
5. Copy the generated invite URL and open it in your browser.
6. Add the bot to your server.

## Run the bot on Raspberry Pi

From the project folder with the virtual environment activated:

```bash
python3 bot.py
```

If you want the bot to keep running after you close the terminal, use `screen` or `tmux`:

```bash
sudo apt install -y screen
screen -S discord-bot
python3 bot.py
```

Then detach with `Ctrl+A D`.

## Using the bot in Discord

In a voice-enabled server channel with the bot present:

- `!play <url>` — add a YouTube or audio URL to the queue and play it.
- `!skip` — skip the current track.
- `!stop` — stop playback, clear the queue, and disconnect the bot.

Example:

```text
!play https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

## Notes for Raspberry Pi users

- Use a Raspberry Pi 4 or later for better performance, especially if multiple tracks are queued.
- Keep `ffmpeg` installed and up to date.
- If voice connection fails, confirm the bot has permission to join and speak in the channel.
- The bot does not save queue state across restarts.

## Troubleshooting

### Bot does not start

- Confirm Python and required packages are installed.
- Check that `bot.py` contains your valid token.
- Run `python3 bot.py` and watch for error messages.

### Audio does not play

- Ensure `ffmpeg` is installed.
- Ensure the bot is connected to the same voice channel as the user.
- Verify the URL is a supported YouTube/audio link.

### Permission issues

- Confirm the bot has `Connect` and `Speak` permissions in the voice channel.
- Confirm the bot can send messages in the text channel.

## Optional improvements

- Use an environment variable for the bot token instead of hardcoding.
- Add logging or a startup script to start the bot automatically on boot.
- Enable a `requirements.txt` file for easier dependency management.
