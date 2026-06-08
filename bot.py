import discord
from discord.ext import commands
import yt_dlp
import asyncio
from datetime import datetime
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ModuleNotFoundError:
    pass

# --- Custom Terminal Logger ---
def log_event(message, level="INFO"):
    colors = {
        "INFO": "\033[96m",    # Cyan
        "PLAY": "\033[92m",    # Green
        "QUEUE": "\033[93m",   # Yellow
        "SKIP": "\033[95m",    # Magenta
        "ERROR": "\033[91m",   # Red
        "RESET": "\033[0m"     # Reset
    }
    time_now = datetime.now().strftime("%H:%M:%S")
    color = colors.get(level, colors["RESET"])
    print(f"\033[90m[{time_now}]\033[0m {color}[{level}]\033[0m {message}")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Optimized yt-dlp settings (IPv6 bypass and lightweight format)
ydl_opts = {
    'format': 'bestaudio[ext=m4a]/bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'source_address': '0.0.0.0', 
}

# Optimized FFmpeg settings (Single thread limit and buffered streaming)
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -threads 1',
    'options': '-vn -bufsize 64k'
}

music_queue = []
is_fetching = False

@bot.event
async def on_ready():
    log_event(f"Logged in successfully as {bot.user}", "INFO")
    log_event("Waiting for commands...", "INFO")

# --- Background Queue Manager ---
async def play_next(ctx):
    global is_fetching
    
    if len(music_queue) > 0:
        is_fetching = True
        url = music_queue.pop(0)
        
        try:
            log_event(f"Extracting audio data from YouTube...", "INFO")
            
            def extract_video_info():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(url, download=False)
            
            # Offload heavy extraction to background thread
            info = await asyncio.to_thread(extract_video_info)
            audio_url = info['url']
            title = info.get('title', 'Audio')

            def after_playing(error):
                if error:
                    log_event(f"Playback error: {error}", "ERROR")
                log_event(f"Finished playing: {title}", "INFO")
                # Trigger the next song automatically
                asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)

            source = discord.FFmpegPCMAudio(audio_url, **ffmpeg_options)
            ctx.voice_client.play(source, after=after_playing)
            
            log_event(f"Started playing: {title}", "PLAY")
            await ctx.send(f"[Playing] Now playing: {title}")
            
        except Exception as e:
            log_event(f"Failed to play track: {str(e)}", "ERROR")
            await ctx.send(f"[Error] An error occurred: {str(e)}")
            # Skip broken links and try the next one
            asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
            
        finally:
            is_fetching = False
    else:
        log_event("Queue is empty. Waiting.", "INFO")

# --- Bot Commands ---
@bot.command()
async def play(ctx, url: str):
    global is_fetching
    
    if ctx.author.voice is None:
        await ctx.send("You need to be in a voice channel to use this command.")
        return

    voice_channel = ctx.author.voice.channel

    if ctx.voice_client is None:
        log_event(f"Joining voice channel: {voice_channel.name}", "INFO")
        await voice_channel.connect()
    else:
        await ctx.voice_client.move_to(voice_channel)

    music_queue.append(url)
    
    if ctx.voice_client.is_playing() or is_fetching:
        log_event(f"Track added to queue. (Queue size: {len(music_queue)})", "QUEUE")
        await ctx.send(f"[Added] Added to queue! (Position: {len(music_queue)})")
    else:
        await play_next(ctx)

@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        log_event("User triggered skip command.", "SKIP")
        await ctx.send("[Skip] Skipping current track...")
        ctx.voice_client.stop() 
    else:
        await ctx.send("Nothing is playing right now.")

@bot.command()
async def stop(ctx):
    global music_queue
    log_event("User triggered stop command. Wiping queue.", "INFO")
    music_queue.clear() 
    
    if ctx.voice_client:
        ctx.voice_client.stop()
        await ctx.voice_client.disconnect()
        log_event("Disconnected from voice channel.", "INFO")
        await ctx.send("[Disconnected] Disconnected and wiped the queue.")

# Grab the secure token and run
TOKEN = os.getenv('DISCORD_TOKEN', 'YOUR_BOT_TOKEN_HERE')
bot.run(TOKEN)