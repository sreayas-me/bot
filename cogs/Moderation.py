import discord
import random
import json
import logging
from discord.ext import commands
from datetime import timedelta
import datetime
import asyncio
from cogs.logging.logger import CogLogger
from utils.db import db
from utils.error_handler import ErrorHandler

# this is super wip
class Moderation(commands.Cog, ErrorHandler):
    def __init__(self, bot):
        ErrorHandler.__init__(self)
        self.bot = bot
        self.logger = CogLogger(self.__class__.__name__)
        self.bot.launch_time = discord.utils.utcnow()
        self.logger.info("Moderation cog initialized")

    async def log_action(self, guild_id: int, embed: discord.Embed):
        """Log moderation action to configured channel"""
        settings = await db.get_guild_settings(guild_id)
        if log_channel_id := settings.get("moderation", {}).get("log_channel"):
            if channel := self.bot.get_channel(log_channel_id):
                try:
                    await channel.send(embed=embed)
                except discord.HTTPException:
                    pass

    @commands.command(aliases=["to"])
    @commands.has_permissions(moderate_members=True)
    async def timeout(self, ctx, member: discord.Member, duration: str, *, reason=None):
        """Timeout a member (e.g. 1h, 1d, 1w)"""
        if member.top_role >= ctx.author.top_role:
            return await ctx.send("You can't timeout someone with a higher or equal role!")

        # Convert duration string to timedelta
        time_units = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days", "w": "weeks"}
        amount = int(''.join(filter(str.isdigit, duration)))
        unit = ''.join(filter(str.isalpha, duration)).lower()
        
        if unit not in time_units:
            return await ctx.send("Invalid duration format! Use s/m/h/d/w (e.g. 1h, 1d)")

        delta = timedelta(**{time_units[unit]: amount})
        
        try:
            await member.timeout(delta, reason=reason)
            embed = discord.Embed(
                description=f"timed out {member.mention} • {duration}\n{reason or 'no reason provided'}",
                color=discord.Color.orange()
            ).set_footer(text=f"by {ctx.author.name}")
            await ctx.send(embed=embed)
            await self.log_action(ctx.guild.id, embed)
        except discord.HTTPException as e:
            await ctx.send(f"failed to timeout: {e}")

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason=None):
        await member.kick(reason=reason)
        embed = discord.Embed(
            description=f"kicked {member.mention}\n{reason or 'no reason provided'}",
            color=discord.Color.red()
        ).set_footer(text=f"by {ctx.author.name}")
        await ctx.send(embed=embed)

    @timeout.error
    async def timeout_error(self, ctx, error):
        """Handle timeout command errors"""
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply("❌ You don't have permission to timeout members!")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.reply("❌ Member not found!")
        elif isinstance(error, commands.BadArgument):
            await ctx.reply("❌ Invalid duration format! Use s/m/h/d/w (e.g. 1h, 1d)")
        else:
            await self.handle_error(ctx, error, "timeout")

    @kick.error
    async def kick_error(self, ctx, error):
        """Handle kick command errors"""
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply("❌ You don't have permission to kick members!")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.reply("❌ Member not found!")
        else:
            await self.handle_error(ctx, error, "kick")

async def setup(bot):
    logger = CogLogger("Moderation")
    try:
        await bot.add_cog(Moderation(bot))
        logger.info("Moderation cog loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load Moderation cog: {e}")
        raise