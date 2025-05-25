import discord
import random
import json
import logging
from discord.ext import commands
import datetime
import asyncio

# this is super wip
class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(f"bronxbot.{self.__class__.__name__}")
        self.bot.launch_time = discord.utils.utcnow()
        self.logger.info("Moderation cog initialized")

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason=None):
        await member.kick(reason=reason)
        await ctx.send(f"**{member.display_name}**")

async def setup(bot):
    logger = logging.getLogger("bronxbot.Moderation")
    try:
        await bot.add_cog(Moderation(bot))
        logger.info("Moderation cog loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load Moderation cog: {e}")
        raise