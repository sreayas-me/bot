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
        logging.FileHandler('data/logs/Help.log')
    ]
)
logger = logging.getLogger('Help')

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help", aliases=["h"])
    async def help(self, ctx):
        await ctx.reply("help")

async def setup(bot):
    try:
        await bot.add_cog(Help(bot))
        logger.info("Help cog loaded successfully")

    except Exception as e:
        logger.error(f"Failed to load Help cog: {e}")
        raise e