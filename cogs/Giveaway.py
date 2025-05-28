import discord
import random
import json
import logging
from discord.ext import commands
import datetime
import asyncio
from cogs.logging.logger import CogLogger
from utils.error_handler import ErrorHandler

# this is super wip
class Giveaway(commands.Cog, ErrorHandler):
    def __init__(self, bot):
        ErrorHandler.__init__(self)
        self.bot = bot
        self.logger = CogLogger(self.__class__.__name__)
        self.bot.launch_time = discord.utils.utcnow()
        self.logger.info("Giveaway cog initialized")

    @commands.command()
    @commands.has_permissions(manage_guild=True)
    async def giveaway(self, ctx):
        """Start a giveaway"""
        await ctx.reply("Giveaway started!")

    @giveaway.error
    async def giveaway_error(self, ctx, error):
        """Handle giveaway command errors"""
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply("❌ You don't have permission to giveaway members!")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.reply("❌ Member not found!")
        else:
            await self.handle_error(ctx, error, "giveaway")

async def setup(bot):
    logger = CogLogger("Giveaway")
    try:
        await bot.add_cog(Giveaway(bot))
    except Exception as e:
        logger.error(f"Failed to load Giveaway cog: {e}")
        raise