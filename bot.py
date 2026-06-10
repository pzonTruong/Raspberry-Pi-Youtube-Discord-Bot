import discord
from discord.ext import commands
import yt_dlp
import asyncio
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

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

# Improved audio configurations to prevent the speed bug
ydl_opts = {
    'format': 'bestaudio[ext=m4a]/bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'source_address': '0.0.0.0', 
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -ar 48000 -ac 2 -filter:a "aresample=async=1"'
}

# Queue, History, and Auto-Leave Tracking
music_queue = []
history_stack = []
current_track_url = None
is_fetching = False
idle_task = None

@bot.event
async def on_ready():
    log_event(f"Logged in successfully as {bot.user}", "INFO")
    log_event("Waiting for commands...", "INFO")

# --- Interactive Control Panel Buttons ---
class MusicControlView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=None)
        self.ctx = ctx

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        global music_queue, current_track_url
        await interaction.response.defer()
        
        if len(history_stack) < 2:  
            return
            
        log_event("User clicked Previous button.", "SKIP")
        history_stack.pop() 
        prev_url = history_stack.pop()
        
        if current_track_url:
            music_queue.insert(0, current_track_url)
        music_queue.insert(0, prev_url)
        
        if self.ctx.voice_client:
            self.ctx.voice_client.stop()

    @discord.ui.button(label="Pause/Resume", style=discord.ButtonStyle.primary)
    async def pause_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.ctx.voice_client:
            if self.ctx.voice_client.is_playing():
                self.ctx.voice_client.pause()
                log_event("Playback paused via UI button.", "INFO")
                await self.ctx.send("[Paused] Audio playback has been paused.")
            elif self.ctx.voice_client.is_paused():
                self.ctx.voice_client.resume()
                log_event("Playback resumed via UI button.", "INFO")
                await self.ctx.send("[Resumed] Audio playback has been resumed.")

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger)
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        global music_queue
        music_queue.clear()
        if self.ctx.voice_client:
            log_event("User clicked Stop button.", "INFO")
            self.ctx.voice_client.stop()

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.ctx.voice_client and self.ctx.voice_client.is_playing():
            log_event("User clicked Next button.", "SKIP")
            self.ctx.voice_client.stop()

    @discord.ui.button(label="Show Queue", style=discord.ButtonStyle.success)
    async def queue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(music_queue) == 0:
            await interaction.response.send_message("[Queue] The queue is currently empty.", ephemeral=True)
            return
            
        queue_list = ""
        for i, url in enumerate(music_queue[:5], 1):
            queue_list += f"{i}. {url}\n"
        if len(music_queue) > 5:
            queue_list += f"...and {len(music_queue) - 5} more tracks."
            
        await interaction.response.send_message(f"[Queue] Upcoming songs:\n{queue_list}", ephemeral=True)

# --- Auto-Leave Inactivity Manager ---
async def manage_idle_timeout(ctx):
    global idle_task
    if idle_task is not None:
        idle_task.cancel()
    idle_task = asyncio.create_task(idle_countdown(ctx))

async def idle_countdown(ctx):
    await asyncio.sleep(60) 
    if ctx.voice_client and not ctx.voice_client.is_playing() and len(music_queue) == 0:
        log_event("Bot was idle for 1 minute. Auto-disconnecting.", "INFO")
        await ctx.voice_client.disconnect()
        await ctx.send("[Disconnected] Left voice channel due to 1 minute of inactivity.")

# --- Background Queue Manager ---
async def play_next(ctx):
    global is_fetching, current_track_url, idle_task
    
    if idle_task is not None:
        idle_task.cancel()
        idle_task = None

    if len(music_queue) > 0:
        is_fetching = True
        current_track_url = music_queue.pop(0)
        history_stack.append(current_track_url)
        
        try:
            log_event("Extracting audio data and thumbnail from YouTube...", "INFO")
            
            def extract_video_info():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(current_track_url, download=False)
            
            info = await asyncio.to_thread(extract_video_info)
            audio_url = info['url']
            title = info.get('title', 'Audio')
            thumbnail = info.get('thumbnail', None)

            def after_playing(error):
                if error:
                    log_event(f"Playback error: {error}", "ERROR")
                log_event(f"Finished playing: {title}", "INFO")
                asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)

            source = discord.FFmpegPCMAudio(audio_url, **ffmpeg_options)
            ctx.voice_client.play(source, after=after_playing)
            log_event(f"Started playing: {title}", "PLAY")
            
            embed = discord.Embed(
                title=title, 
                description=f"Status: Now Playing\nRequested by: {ctx.author.name}", 
                color=0x2b2d31
            )
            if thumbnail:
                embed.set_image(url=thumbnail)
                
            view = MusicControlView(ctx)
            await ctx.send(embed=embed, view=view)
            
        except Exception as e:
            log_event(f"Failed to play track: {str(e)}", "ERROR")
            await ctx.send(f"[Error] An error occurred: {str(e)}")
            asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
            
        finally:
            is_fetching = False
    else:
        log_event("Queue is empty. Initiating 1-minute auto-leave countdown.", "INFO")
        await manage_idle_timeout(ctx)

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
async def pause(ctx):
    if ctx.voice_client:
        if ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            log_event("Playback paused via text command.", "INFO")
            await ctx.send("[Paused] Audio playback has been paused.")
        elif ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            log_event("Playback resumed via text command.", "INFO")
            await ctx.send("[Resumed] Audio playback has been resumed.")
        else:
            await ctx.send("[Info] Nothing is currently playing or paused.")
    else:
        await ctx.send("[Error] I am not connected to a voice channel.")

@bot.command()
async def queue(ctx):
    if len(music_queue) == 0:
        await ctx.send("[Queue] The queue is currently empty.")
        return
        
    queue_list = ""
    for i, url in enumerate(music_queue[:10], 1):
        queue_list += f"{i}. {url}\n"
    if len(music_queue) > 10:
        queue_list += f"...and {len(music_queue) - 10} more tracks."
        
    await ctx.send(f"[Queue] Upcoming songs:\n{queue_list}")

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
        await ctx.send("[Disconnected] Disconnected and wiped the queue.")

TOKEN = os.getenv('DISCORD_TOKEN')
bot.run(TOKEN)