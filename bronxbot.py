import discord
import json
import random
import time
import sys
import os
import asyncio
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
    
    @staticmethod
    def categorize_error(error: Exception) -> Tuple[str, str]:
        """Categorize error and provide helpful message"""
        if isinstance(error, ImportError):
            return "Import Failed", "Missing required module or dependency"
        elif isinstance(error, SyntaxError):
            return "Syntax Error", f"Invalid syntax at line {error.lineno}"
        elif isinstance(error, AttributeError):
            return "Setup Failed", "Missing setup() function or invalid cog class"
        elif isinstance(error, TypeError):
            return "Type Error", "Invalid argument types in cog setup"
        elif isinstance(error, discord.ClientException):
            return "Discord Error", "Invalid event or command setup"
        else:
            return "Unknown Error", str(error)

    @classmethod
    async def load_cog_with_retries(cls, bot: BronxBot, cog: str, max_retries: int = 3) -> Tuple[bool, float, str]:
        """Attempt to load a cog with retries for critical cogs"""
        start_time = time.time()
        error_msg = ""
        
        for attempt in range(max_retries):
            try:
                success, load_time = await bot.load_cog_with_timing(cog)
                if success:
                    return True, load_time, ""
            except Exception as e:
                error_type, error_desc = cls.categorize_error(e)
                error_msg = f"{error_type}: {error_desc}"
                if attempt < max_retries - 1 and cog in ["cogs.Help", "cogs.ModMail", "cogs.unique.SyncRoles"]:
                    await asyncio.sleep(1)  # Wait before retry
                    continue
                break
        
        return False, time.time() - start_time, error_msg

    @classmethod
    async def load_all_cogs(cls, bot: BronxBot) -> Tuple[int, int]:
        """Load all cogs with enhanced error handling"""
        start_time = time.time()
        results = []
        failed_cogs = []
        max_cog_length = max(len(cog) for cog in COG_DATA['cogs'])
        
        for cog, cog_type in COG_DATA['cogs'].items():
            color_code = cls.get_color_escape(cog_type)
            success, load_time, error_msg = await cls.load_cog_with_retries(bot, cog)
            
            if success:
                status = "LOADED"
                status_color = cls.get_color_escape('success')
            else:
                status = "ERROR"
                status_color = cls.get_color_escape('error')
                failed_cogs.append((cog, error_msg))
            
            cog_display = f"{color_code}{cog.ljust(max_cog_length)}\033[0m"
            status_display = f"{status_color}{status}\033[0m"
            time_display = f"{load_time:.2f}s"
            
            result_line = f"[bronxbot] {cog_display} : {status_display} ({time_display})"
            if not success:
                result_line += f"\n         {cls.get_color_escape('error')}→ {error_msg}\033[0m"
            
            results.append((cog_type, result_line))
        
        total_time = time.time() - start_time
        results.append(('info', f"\nTotal loading time: {total_time:.2f}s"))
        
        # Add critical failures section if any essential cogs failed
        critical_cogs = {"cogs.Help", "cogs.ModMail", "cogs.unique.SyncRoles"}
        critical_failures = [cog for cog, _ in failed_cogs if cog in critical_cogs]
        if critical_failures:
            results.append(('error', "\n⚠️ Critical cog(s) failed to load:"))
            for cog in critical_failures:
                results.append(('error', f"  • {cog}"))
        
        cls.display_results(results)
        return len([r for r in results if "LOADED" in r[1]]), len(failed_cogs)

    @staticmethod
    def display_results(results: List[Tuple[str, str]]) -> None:
        """Display cog loading results with enhanced formatting"""
        results.sort(key=lambda x: x[0])
        print(f"{CogLoader.get_color_escape('info')}=== COG LOADING STATUS ===\033[0m")
    
        for _, line in results:
            print(line)
        
        success_count = sum(1 for _, line in results if "LOADED" in line)
        error_count = len(results) - success_count
        summary_color = CogLoader.get_color_escape('success') if error_count == 0 else CogLoader.get_color_escape('warning')
        
        print(f"\n{summary_color}[SUMMARY] Loaded {success_count}/{len(results)} cogs ({error_count} errors)\033[0m")

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