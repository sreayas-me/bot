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

    @commands.command(aliases=['mock'])
    async def spongebob(self, ctx, *, text):
        """mOcK sOme tExT"""
        result = ''.join([char.upper() if i % 2 == 0 else char.lower() for i, char in enumerate(text)])
        await ctx.reply(f"```{result}```")

    @commands.command(aliases=['choose'])
    async def pick(self, ctx, *options):
        """pick a random option

        Usage: pick [option1] [option2] ... [optionN]
        """
        if not options:
            return await ctx.reply("```provide some options to choose from```")
        await ctx.reply(f"```i choose: {random.choice(options)}```")

    @commands.command(aliases=['smallcaps'])
    async def tinytext(self, ctx, *, text: str):
        """convert to ᵗⁱⁿʸ ᶜᵃᵖˢ"""
        mapping = str.maketrans(
            'abcdefghijklmnopqrstuvwxyz',
            'ᵃᵇᶜᵈᵉᶠᵍʰⁱʲᵏˡᵐⁿᵒᵖᵠʳˢᵗᵘᵛʷˣʸᶻ'
        )
        await ctx.reply(f"```{text.lower().translate(mapping)}```")

    @commands.command(aliases=['flip'])
    async def reverse(self, ctx, *, text: str):
        """ʇxǝʇ ǝsɹǝʌǝɹ"""
        await ctx.reply(f"```{text[::-1]}```")

async def setup(bot):
    try:
        await bot.add_cog(Fun(bot))
        logger.info("Fun cog loaded successfully")

    except Exception as e:
        logger.error(f"Failed to load Fun cog: {e}")
        raise e