import discord
import random
import json
from discord.ext import commands
import logging
import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('data/logs/utility.log')
    ]
)
logger = logging.getLogger('Utility')

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.launch_time = discord.utils.utcnow()


    @commands.command(name="ping", aliases=["pong"])
    async def ping(self, ctx):
        await ctx.send(f"`{round(self.bot.latency * 1000)}ms`")

    @commands.command(aliases=['av'])
    async def avatar(self, ctx, user: discord.Member = None):
        """get a user's avatar"""
        user = user or ctx.author
        await ctx.reply(f"```{user.display_name}'s avatar```\n{user.display_avatar.url}")

    @commands.command(aliases=['si'])
    async def serverinfo(self, ctx):
        """show server information"""
        guild = ctx.guild
        embed = discord.Embed(color=0x2b2d31)
        embed.set_author(name=f"server info: {guild.name}", icon_url=guild.icon.url if guild.icon else None)
        
        info = f"```members: {guild.member_count}\n"
        info += f"created: {guild.created_at.strftime('%Y-%m-%d')}\n"
        info += f"roles: {len(guild.roles)}\n"
        info += f"channels: {len(guild.channels)}```"
        
        embed.description = info
        await ctx.reply(embed=embed)

    @commands.command(aliases=['ui'])
    async def userinfo(self, ctx, user: discord.Member = None):
        """get information about a user"""
        user = user or ctx.author
        embed = discord.Embed(color=0x2b2d31)
        embed.set_author(name=f"user info: {user.display_name}", icon_url=user.display_avatar.url)
        
        info = f"```joined: {user.joined_at.strftime('%Y-%m-%d')}\n"
        info += f"registered: {user.created_at.strftime('%Y-%m-%d')}\n"
        info += f"top role: {user.top_role.name}```"
        
        embed.description = info
        await ctx.reply(embed=embed)

    @commands.command(aliases=['poll'])
    async def vote(self, ctx, *, question):
        """create a simple yes/no poll"""
        embed = discord.Embed(color=0x2b2d31, description=f"```{question}```")
        embed.set_author(name=f"poll by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        msg = await ctx.send(embed=embed)
        await msg.add_reaction('✅')
        await msg.add_reaction('❌')

    @commands.command(aliases=['calc'])
    async def calculate(self, ctx, *, expression):
        """evaluate a math expression"""
        try:
            result = eval(expression)
            await ctx.reply(f"```{expression} = {result}```")
        except:
            await ctx.reply("```invalid expression```")
    
    @commands.command()
    async def uptime(self, ctx):
        """show bot uptime"""
        delta = discord.utils.utcnow() - self.bot.launch_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)
        embed = discord.Embed(description=f"```{days} days, {hours} hours, {minutes} minutes, {seconds} seconds```", color=0x2b2d31)
        await ctx.reply(embed=embed)

    @commands.command(aliases=['time'])
    async def timestamp(self, ctx, style: str = 'f'):
        """generate discord timestamps (styles: t, T, d, D, f, F, R)

        Usage: .time [style]"""
        valid = ['t', 'T', 'd', 'D', 'f', 'F', 'R']
        if style not in valid:
            return await ctx.reply(f"```invalid style. choose from: {', '.join(valid)}```")
        now = int(discord.utils.utcnow().timestamp())
        await ctx.reply(f"```<t:{now}:{style}> → <t:{now}:{style}>```\n`copy-paste the gray part`")

    @commands.command(aliases=['timeleft'])
    async def countdown(self, ctx, future_time: str):
        """calculate time remaining (format: YYYY-MM-DD)

        Usage: .timeleft [YYYY-MM-DD]
        """
        try:
            target = datetime.strptime(future_time, "%Y-%m-%d")
            delta = target - discord.utils.utcnow()
            await ctx.reply(f"```{delta.days} days remaining```")
        except ValueError:
            await ctx.reply("```invalid format. use YYYY-MM-DD```")

        except Exception as e:
            await ctx.reply(f"```{e}```")
    
    @commands.command(aliases=['shorten'])
    async def tinyurl(self, ctx, *, url: str):
        """shorten a URL"""
        if not url.startswith(('http://', 'https://')):
            url = f'https://{url}'
        async with self.bot.session.get(f"https://tinyurl.com/api-create.php?url={url}") as resp:
            await ctx.reply(f"```{await resp.text()}```")
    


async def setup(bot):
    try:
        await bot.add_cog(Utility(bot))
        logger.info("Utility cog loaded successfully")

    except Exception as e:
        logger.error(f"Failed to load Utility cog: {e}")
        raise e