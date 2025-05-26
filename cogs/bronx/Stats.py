import discord
from discord.ext import commands
from cogs.logging.logger import CogLogger
from utils.db import db

logger = CogLogger('Stats')
guilds = [1259717095382319215, 1299747094449623111, 1142088882222022786]
class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.main_guilds = self.bot.MAIN_GUILD_IDS

    async def cog_check(self, ctx):
        """Check if the guild has permission to use this cog's commands"""
        return ctx.guild.id in self.main_guilds

    @commands.command(name="stats", aliases=["st"])
    @commands.is_owner()
    async def stats(self, ctx):
        stats = await db.get_stats(ctx.guild.id)
        
        embed = discord.Embed(
            description=f"""
            `messages {stats.get('messages', 0)}`
            `members gained {stats.get('gained', 0)}`
            `members lost {stats.get('lost', 0)}`
            `total g/l {stats.get('gained', 0) - stats.get('lost', 0)}`
            """,
            color=discord.Color.random()
        )
        embed.set_thumbnail(url=self.bot.user.avatar.url)
        await ctx.reply(embed=embed)

    @commands.command(name="resetstats", aliases=["rst"])
    @commands.is_owner()
    async def resetstats(self, ctx):
        if await db.reset_stats(ctx.guild.id):
            await ctx.reply("Stats have been reset for this guild!")
        else:
            await ctx.reply("Failed to reset stats!")

async def setup(bot):
    try:
        await bot.add_cog(Stats(bot))
        logger.info("Stats cog loaded successfully")

    except Exception as e:
        logger.error(f"Failed to load Stats cog: {e}")
        raise e