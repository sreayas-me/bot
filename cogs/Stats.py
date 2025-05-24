import discord
import json
from discord.ext import commands
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('data/logs/stats.log')
    ]
)
logger = logging.getLogger('Stats')

class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.guild.id == 1259717095382319215:
            with open("data/stats.json", "r") as f:
                data = json.load(f)
                data["messages"] += 1
            with open("data/stats.json", "w") as f:
                json.dump(data, f, indent=2)

    @commands.command(name="stats", aliases=["st"])
    @commands.is_owner()
    async def stats(self, ctx):
        await ctx.send("```json\n" + json.dumps(self.bot.stats, indent=2) + "```")

async def setup(bot):
    try:
        await bot.add_cog(Stats(bot))
        logger.info("Stats cog loaded successfully")

    except Exception as e:
        logger.error(f"Failed to load Stats cog: {e}")
        raise e