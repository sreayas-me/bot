import discord
import random
import json
import logging
from discord.ext import commands
import datetime
import asyncio
from cogs.logging.logger import CogLogger

# this is super wip
class Giveaway(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = CogLogger(self.__class__.__name__)
        self.bot.launch_time = discord.utils.utcnow()
        self.logger.info("Giveaway cog initialized")

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason=None):
        await member.kick(reason=reason)
        await ctx.send(f"**{member.display_name}**")

async def setup(bot):
    logger = CogLogger("Giveaway")
    try:
        await bot.add_cog(Giveaway(bot))
        logger.info("Giveaway cog loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load Giveaway cog: {e}")
        raise