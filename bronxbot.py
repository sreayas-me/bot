import discord
import json
import random
import time
import sys
import os
from discord.ext import commands
from typing import Dict, List, Tuple

# config
with open("data/config.json", "r") as f:
    config = json.load(f)

# setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.reactions = True

class BronxBot(commands.AutoShardedBot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_time = time.time()
        self.cog_load_times = {}
        self.restart_channel = None
        self.restart_message = None

    async def load_cog_with_timing(self, cog_name: str) -> Tuple[bool, float]:
        """Load a cog and measure its loading time"""
        start_time = time.time()
        try:
            await self.load_extension(cog_name)
            load_time = time.time() - start_time
            self.cog_load_times[cog_name] = load_time
            return True, load_time
        except Exception as e:
            load_time = time.time() - start_time
            self.cog_load_times[cog_name] = load_time
            return False, load_time

# Replace bot initialization
bot = BronxBot(command_prefix='.', intents=intents)
bot.remove_command('help')

# loading config
COG_DATA = {
    "cogs": {
        "cogs.misc.Cypher": "cog", 
        "cogs.misc.MathRace": "cog", 
        "cogs.misc.TicTacToe": "cog",
        "cogs.bronx.Stats": "other", 
        "cogs.bronx.VoteBans": "other", 
        "cogs.bronx.Welcoming": "other",
        "cogs.unique.Economy": "disabled", 
        "cogs.unique.Multiplayer": "fun", 
        "cogs.Fun": "fun",
        "cogs.unique.SyncRoles": "success", 
        "cogs.Help": "success", 
        "cogs.ModMail": "success", 
        "cogs.Utility": "cog"
    },
    "colors": {
        "error": "\033[31m",      # Red
        "success": "\033[32m",    # Green
        "warning": "\033[33m",    # Yellow
        "info": "\033[34m",       # Blue
        "default": "\033[37m",    # White
        "disabled": "\033[90m",   # Bright Black (Gray)
        "fun": "\033[35m",        # Magenta
        "cog": "\033[36m",        # Cyan
        "other": "\033[94m"       # Bright Blue
    }
}

class CogLoader:
    """Handles loading and displaying cog status with colored output"""
    
    @staticmethod
    def get_color_escape(color_name: str) -> str:
        """Return ANSI escape sequence for color name"""
        return COG_DATA['colors'].get(color_name, COG_DATA['colors']['default'])
    
    @classmethod
    async def load_all_cogs(cls, bot: BronxBot) -> Tuple[int, int]:
        """Load all cogs and return success/error counts"""
        start_time = time.time()
        results = []
        max_cog_length = max(len(cog) for cog in COG_DATA['cogs'])
        
        total_success = 0
        total_errors = 0
        
        for cog, cog_type in COG_DATA['cogs'].items():
            color_code = cls.get_color_escape(cog_type)
            success, load_time = await bot.load_cog_with_timing(cog)
            
            if success:
                status = "LOADED"
                status_color = cls.get_color_escape('success')
                total_success += 1
            else:
                status = "ERROR"
                status_color = cls.get_color_escape('error')
                total_errors += 1
            
            cog_display = f"{color_code}{cog.ljust(max_cog_length)}\033[0m"
            status_display = f"{status_color}{status}\033[0m"
            time_display = f"{load_time:.2f}s"
            
            result_line = f"[bronxbot] {cog_display} : {status_display} ({time_display})"
            results.append((cog_type, result_line))
        
        total_time = time.time() - start_time
        results.append(('info', f"\nTotal loading time: {total_time:.2f}s"))
        
        cls.display_results(results)
        return total_success, total_errors

    @staticmethod
    def display_results(results: List[Tuple[str, str]]) -> None:
        """Display cog loading results in organized format"""
        results.sort(key=lambda x: x[0])
        print(f"{CogLoader.get_color_escape('info')}=== COG LOADING STATUS ===\033[0m")
    
        for _, line in results:
            print(line)
        
        success_count = sum(1 for _, line in results if "LOADED" in line)
        error_count = len(results) - success_count
        summary_color = CogLoader.get_color_escape('success') if error_count == 0 else CogLoader.get_color_escape('warning')
        
        print(f"\n{summary_color}[SUMMARY] Loaded {success_count}/{len(results)} cogs ({error_count} errors)\033[0m")

# Bot events
@bot.event
async def on_ready():
    """Called when the bot is ready"""
    if bot.restart_channel and bot.restart_message:
        try:
            channel = await bot.fetch_channel(bot.restart_channel)
            message = await channel.fetch_message(bot.restart_message)
            
            total_time = time.time() - bot.start_time
            embed = discord.Embed(
                description=f"✅ Restart completed in `{total_time:.2f}s`\n\n"
                           f"**Cog Load Times:**\n" + 
                           "\n".join([f"`{cog.split('.')[-1]}: {time:.2f}s`" 
                                    for cog, time in sorted(bot.cog_load_times.items())]),
                color=discord.Color.green()
            )
            await message.edit(embed=embed)
        except Exception as e:
            print(f"Failed to update restart message: {e}")

    success, errors = await CogLoader.load_all_cogs(bot)
    status_msg = (
        f"[?] Logged in as {bot.user.name} (ID: {bot.user.id})\n"
        f"[!] Shards: {bot.shard_count}, Latency: {round(bot.latency * 1000, 2)}ms\n"
        f"[+] Cogs: {success} loaded, {errors} errors"
    )
    print(status_msg)
    
    activity = discord.Activity(
        type=discord.ActivityType.playing,
        name=f"with {len(bot.guilds)} servers | .help"
    )
    await bot.change_presence(activity=activity)

@bot.event
async def on_message(message: discord.Message):
    """Handle message events"""
    if message.author.bot:
        return
    
    tips = [
        "I was made in 3 hours", 
        "Zhang Yong", 
        "Use .help to get started",
        "Try .help <command> for more info", 
        "Try the modmail feature if you need help",
        "Did you know this bot is open source?", 
        "This bot is hosted on KS's crusty old PC",
        ".md gets smarter over time, so try it out!", 
        ".jackpot is fun with friends"
    ]
    
    if message.content == bot.user.mention:
        if str(message.author.id) in config['OWNER_IDS']:
            response = random.choice(config['OWNER_REPLY'])
        else:
            response = random.choice(tips)
        
        await message.reply(
            f"Hi, **{message.author.name}**\n"
            f"-# {response}\n"
            f"`{round(bot.latency * 1000, 2)}ms`"
        )
    
    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx: commands.Context, error: Exception):
    """Handle command errors"""
    if isinstance(error, commands.CommandNotFound):
        print(f"[!] Command not found: {ctx.command}")
        return
    else:
        raise error

@bot.command(name="restart", aliases=["reboot"])
@commands.is_owner()
async def restart(ctx):
    """Restart the bot"""
    embed = discord.Embed(
        description="🔄 Restarting bot...",
        color=discord.Color.orange()
    )
    msg = await ctx.reply(embed=embed)
    
    # Save restart info to file
    with open("data/restart_info.json", "w") as f:
        json.dump({
            "channel_id": ctx.channel.id,
            "message_id": msg.id
        }, f)
    
    # Execute the restart
    os.execv(sys.executable, ['python'] + sys.argv)

# Add restart info loading at startup
if os.path.exists("data/restart_info.json"):
    try:
        with open("data/restart_info.json", "r") as f:
            restart_info = json.load(f)
            bot.restart_channel = restart_info["channel_id"]
            bot.restart_message = restart_info["message_id"]
        os.remove("data/restart_info.json")
    except Exception as e:
        print(f"Failed to load restart info: {e}")

if __name__ == "__main__":
    bot.run(config['TOKEN'])