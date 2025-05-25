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
        logging.FileHandler('data/logs/fun.log')
    ]
)
logger = logging.getLogger('Fun')

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

async def setup(bot):
    try:
        await bot.add_cog(Fun(bot))
        logger.info("Fun cog loaded successfully")

    except Exception as e:
        logger.error(f"Failed to load Fun cog: {e}")
        raise e