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
        logging.FileHandler('data/logs/economy.log')
    ]
)
logger = logging.getLogger('Economy')

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

async def setup(bot):
    try:
        await bot.add_cog(Economy(bot))
        logger.info("Economy cog loaded successfully")

    except Exception as e:
        logger.error(f"Failed to load Economy cog: {e}")
        raise e