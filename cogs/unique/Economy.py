import discord
import random
import json
import logging
from discord.ext import commands

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(f"bronxbot.{self.__class__.__name__}")
        self.logger.info(f"Initializing {self.__class__.__name__} cog")
        self.currency = "💰"
        self.logger.debug(f"Currency symbol set to: {self.currency}")

    @commands.command(name="balance", aliases=["bal"])
    async def check_balance(self, ctx, member: discord.Member = None):
        """Check a user's balance"""
        member = member or ctx.author
        self.logger.info(f"Balance check for {member.display_name}")
        # TODO: replace with actual economy logic
        balance = random.randint(100, 1000)
        await ctx.send(f"{member.mention}'s balance: {balance}{self.currency}")
        self.logger.debug(f"Balance returned: {balance}{self.currency}")

    @commands.command(name="pay")
    async def pay_user(self, ctx, member: discord.Member, amount: int):
        """Pay another user"""
        self.logger.info(f"Payment attempt from {ctx.author} to {member} for {amount}{self.currency}")
        try:
            if amount <= 0:
                raise ValueError("Amount must be positive")
            # TODO: replace with actual economy logic
            await ctx.send(f"Paid {member.mention} {amount}{self.currency}!")
            self.logger.info(f"Payment successful")
        except Exception as e:
            self.logger.error(f"Payment failed: {str(e)}", exc_info=True)
            await ctx.send(f"Error: {str(e)}")

async def setup(bot):
    logger = logging.getLogger("bronxbot.Economy")
    try:
        cog = Economy(bot)
        await bot.add_cog(cog)
        logger.info("Economy cog loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load Economy cog: {str(e)}", exc_info=True)
        raise