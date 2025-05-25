import discord
import random
import json
from discord.ext import commands
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('data/logs/utility.log')
    ]
)
logger = logging.getLogger('Utility')

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.command(name="ping", aliases=["pong"])
    async def ping(self, ctx):
        await ctx.send(f"`{round(self.bot.latency * 1000)}ms`")

async def setup(bot):
    try:
        await bot.add_cog(Utility(bot))
        logger.info("Utility cog loaded successfully")

    except Exception as e:
        logger.error(f"Failed to load Utility cog: {e}")
        raise e