import discord
from discord.ext import commands
import yt_dlp
import asyncio

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Your optimized yt-dlp and FFmpeg settings
ydl_opts = {
    'format': 'bestaudio[ext=m4a]/bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'source_address': '0.0.0.0',
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -threads 1',
    'options': '-vn -bufsize 64k'
}

# --- NEW: Queue Variables ---
music_queue = []
is_fetching = False

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

# --- NEW: Background Queue Manager ---
async def play_next(ctx):
    global is_fetching
    
    # Check if there are songs waiting in the list
    if len(music_queue) > 0:
        is_fetching = True
        url = music_queue.pop(0) # Grab the first song in line
        
        try:
            def extract_video_info():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(url, download=False)
            
            info = await asyncio.to_thread(extract_video_info)
            audio_url = info['url']
            title = info.get('title', 'Audio')

            # The magic trick: When this song finishes, trigger this function again!
            def after_playing(error):
                asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)

            source = discord.FFmpegPCMAudio(audio_url, **ffmpeg_options)
            ctx.voice_client.play(source, after=after_playing)
            await ctx.send(f"[Playing] Now playing: {title}")
            
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")
            # If a link is broken, skip it and try playing the next one automatically
            asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
            
        finally:
            is_fetching = False
            
    else:
        await ctx.send("The queue is empty.")

@bot.command()
async def play(ctx, url: str):
    global is_fetching
    
    if ctx.author.voice is None:
        await ctx.send("You need to be in a voice channel to use this command.")
        return

    voice_channel = ctx.author.voice.channel

    if ctx.voice_client is None:
        await voice_channel.connect()
    else:
        await ctx.voice_client.move_to(voice_channel)

    # Add the requested link to the back of the queue
    music_queue.append(url)
    
    # If the bot is already busy playing/fetching, just tell the user it was added
    if ctx.voice_client.is_playing() or is_fetching:
        await ctx.send(f"[Added] Added to queue! (Position: {len(music_queue)})")
    else:
        # If the bot is completely quiet, kickstart the queue manager
        await play_next(ctx)

# --- NEW: Skip Command ---
@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        await ctx.send("[Skip] Skipping current track...")
        # Stopping the audio triggers our 'after_playing' function, loading the next song!
        ctx.voice_client.stop() 
    else:
        await ctx.send("Nothing is playing right now.")

@bot.command()
async def stop(ctx):
    global music_queue
    # Wipe the list completely so the bot doesn't keep playing after we tell it to stop
    music_queue.clear() 
    
    if ctx.voice_client:
        ctx.voice_client.stop()
        await ctx.voice_client.disconnect()
        await ctx.send("Disconnected and wiped the queue.")
    else:
        await ctx.send("I am not in a voice channel.")

bot.run('YOUR_BOT_TOKEN_HERE')