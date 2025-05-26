import discord
import random
import json
import datetime
import asyncio
from discord.ext import commands
from cogs.logging.logger import CogLogger
from utils.error_handler import ErrorHandler

class Utility(commands.Cog, ErrorHandler):
    def __init__(self, bot):
        ErrorHandler.__init__(self)
        self.bot = bot
        self.logger = CogLogger(self.__class__.__name__)
        self.bot.launch_time = discord.utils.utcnow()
        self.logger.info("Utility cog initialized")

    @commands.command(name="ping", aliases=["pong"])
    async def ping(self, ctx):
        latency = round(self.bot.latency * 1000)
        self.logger.debug(f"Ping command used by {ctx.author} - {latency}ms")
        await ctx.send(f"`{latency}ms`")

    @commands.command(aliases=['av'])
    async def avatar(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        self.logger.info(f"Avatar requested for {user.display_name}")
        await ctx.reply(f"```{user.display_name}'s avatar```\n{user.display_avatar.url}")

    @commands.command(aliases=['cleanup'])
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, limit: int = 10):
        """delete recent messages (default: 10)"""
        try:
            if 0 < limit <= 100:
                self.logger.info(f"Purging {limit} messages in {ctx.channel.name}")
                await ctx.channel.purge(limit=limit+1)
                msg = await ctx.send(f"`deleted {limit} messages`")
                await asyncio.sleep(3)
                await msg.delete()
            else:
                self.logger.warning(f"Invalid purge limit {limit} from {ctx.author}")
                await ctx.reply("`limit must be 1-100`")
        except Exception as e:
            self.logger.error(f"Purge failed: {str(e)}", exc_info=True)
            await ctx.reply("`An error occurred during purge`")

    @commands.command(aliases=['si'])
    async def serverinfo(self, ctx):
        guild = ctx.guild
        
        embed = discord.Embed(
            description=(f"**{guild.name}**\n\n"
                      f"Members: `{guild.member_count}`\n"
                      f"Created: `{guild.created_at.strftime('%Y-%m-%d')}`\n"
                      f"Roles: `{len(guild.roles)}`\n"
                      f"Channels: `{len(guild.channels)}`"),
            color=0x2b2d31
        )
        await ctx.reply(embed=embed)

    @commands.command(aliases=['ui'])
    async def userinfo(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        
        embed = discord.Embed(
            description=(f"**{user.display_name}**\n\n"
                      f"Joined: `{user.joined_at.strftime('%Y-%m-%d')}`\n"
                      f"Registered: `{user.created_at.strftime('%Y-%m-%d')}`\n"
                      f"Top Role: `{user.top_role.name}`"),
            color=user.color or 0x2b2d31
        )
        await ctx.reply(embed=embed)

    @commands.command(aliases=["ask", "yn", "yesno"])
    async def poll(self, ctx, *, question):
        embed = discord.Embed(
            description=f"❓ {question}\n\n✅ Yes | ❌ No",
            color=0x2b2d31
        )
        msg = await ctx.send(embed=embed)
        await msg.add_reaction('✅')
        await msg.add_reaction('❌')

    @commands.command(aliases=['calc'])
    async def calculate(self, ctx, *, expression):
        """evaluate a math expression"""
        try:
            # Basic security check to prevent dangerous eval usage
            allowed_chars = set('0123456789+-*/().,% ')
            if not all(c in allowed_chars for c in expression):
                self.logger.warning(f"Potentially unsafe expression: {expression}")
                return await ctx.reply("```only basic math operations allowed```")
            
            result = eval(expression)
            self.logger.debug(f"Calculation: {expression} = {result}")
            await ctx.reply(f"```{expression} = {result}```")
        except Exception as e:
            self.logger.warning(f"Invalid expression: {expression} - {str(e)}")
            await ctx.reply("```invalid expression```")
    
    @commands.command()
    async def uptime(self, ctx):
        """show bot uptime"""
        delta = discord.utils.utcnow() - self.bot.launch_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)
        self.logger.debug(f"Uptime requested: {days}d {hours}h {minutes}m {seconds}s")
        embed = discord.Embed(description=f"```{days} days, {hours} hours, {minutes} minutes, {seconds} seconds```", color=0x2b2d31)
        await ctx.reply(embed=embed)

    @commands.command(aliases=['time'])
    async def timestamp(self, ctx, style: str = 'f'):
        """generate discord timestamps"""
        valid = ['t', 'T', 'd', 'D', 'f', 'F', 'R']
        if style not in valid:
            self.logger.warning(f"Invalid timestamp style: {style}")
            return await ctx.reply(f"```invalid style. choose from: {', '.join(valid)}```")
        now = int(discord.utils.utcnow().timestamp())
        self.logger.debug(f"Generated timestamp style {style} for {ctx.author}")
        await ctx.reply(f"```<t:{now}:{style}> → <t:{now}:{style}>```\n`copy-paste the gray part`")

    @commands.command(aliases=['timeleft'])
    async def countdown(self, ctx, future_time: str):
        """calculate time remaining"""
        try:
            target = datetime.datetime.strptime(future_time, "%Y-%m-%d")
            delta = target - discord.utils.utcnow()
            self.logger.info(f"Countdown calculated: {delta.days} days remaining")
            await ctx.reply(f"```{delta.days} days remaining```")
        except ValueError:
            self.logger.warning(f"Invalid date format: {future_time}")
            await ctx.reply("```invalid format. use YYYY-MM-DD```")
        except Exception as e:
            self.logger.error(f"Countdown error: {str(e)}", exc_info=True)
            await ctx.reply(f"```{e}```")
    
    @commands.command(aliases=['shorten'])
    async def tinyurl(self, ctx, *, url: str):
        """shorten a URL"""
        if not url.startswith(('http://', 'https://')):
            url = f'https://{url}'
        self.logger.debug(f"URL shortening requested for: {url}")
        
        # Check if bot has aiohttp session
        if not hasattr(self.bot, 'session'):
            return await ctx.reply("```URL shortening unavailable```")
            
        try:
            async with self.bot.session.get(f"https://tinyurl.com/api-create.php?url={url}") as resp:
                result = await resp.text()
                self.logger.debug(f"URL shortened to: {result}")
                await ctx.reply(f"```{result}```")
        except Exception as e:
            self.logger.error(f"URL shortening failed: {str(e)}")
            await ctx.reply("```URL shortening failed```")

    @commands.command()
    async def lottery(self, ctx, max_num: int = 100, picks: int = 6):
        """generate lottery numbers"""
        if picks > max_num:
            self.logger.warning(f"Invalid lottery params: picks={picks} > max={max_num}")
            return await ctx.reply("```picks cannot exceed max number```")
        nums = random.sample(range(1, max_num+1), picks)
        self.logger.debug(f"Generated lottery numbers: {nums}")
        await ctx.reply(f"```{' '.join(map(str, sorted(nums)))}```")

    @commands.command(aliases=['color'])
    async def hexcolor(self, ctx, hex_code: str):
        """show a color preview"""
        hex_code = hex_code.strip('#')
        if len(hex_code) not in (3, 6):
            self.logger.warning(f"Invalid hex code: {hex_code}")
            return await ctx.reply("```invalid hex code```")
        self.logger.debug(f"Color preview generated for: #{hex_code}")
        url = f"https://singlecolorimage.com/get/{hex_code}/200x200"
        embed = discord.Embed(color=int(hex_code.ljust(6, '0'), 16))
        embed.set_image(url=url)
        await ctx.reply(embed=embed)

    @commands.command(aliases=['steal', 'stl', 'addemoji'])
    @commands.has_permissions(manage_emojis=True)
    async def emojisteal(self, ctx, emoji: discord.PartialEmoji):
        """add an emoji to this server"""
        self.logger.info(f"Emoji steal attempted: {emoji.name}")
        
        # Check if bot has aiohttp session
        if not hasattr(self.bot, 'session'):
            return await ctx.reply("```emoji stealing unavailable```")
            
        try:
            async with self.bot.session.get(emoji.url) as resp:
                if resp.status != 200:
                    self.logger.error(f"Failed to download emoji: {emoji.url}")
                    return await ctx.reply("```failed to download emoji```")
                data = await resp.read()
            
            added = await ctx.guild.create_custom_emoji(
                name=emoji.name,
                image=data
            )
            self.logger.info(f"Emoji added: {added}")
            await ctx.reply(f"```added emoji: {added}```")
        except Exception as e:
            self.logger.error(f"Emoji add failed: {str(e)}", exc_info=True)
            await ctx.reply("```missing permissions or slot full```")

    @commands.command(aliases=['firstmsg'])
    async def firstmessage(self, ctx, channel: discord.TextChannel = None):
        """fetch a channel's first message"""
        channel = channel or ctx.channel
        self.logger.debug(f"First message requested in #{channel.name}")
        async for msg in channel.history(limit=1, oldest_first=True):
            await ctx.reply(f"```first message in #{channel.name}```\n{msg.jump_url}")

    @commands.Cog.listener() 
    async def on_command_error(self, ctx, error):
        if ctx.command and ctx.command.cog_name == self.__class__.__name__:
            await self.handle_error(ctx, error)

    def get_command_help(self) -> list[discord.Embed]:
        """Get paginated help embeds for this cog"""
        pages = []
        
        # Server Info Commands Page
        info_embed = discord.Embed(
            title="🔧 Utility Commands - Information",
            color=discord.Color.blue()
        )
        info_commands = ['serverinfo', 'userinfo', 'avatar', 'uptime']
        for cmd_name in info_commands:
            cmd = self.bot.get_command(cmd_name)
            if cmd:
                info_embed.add_field(
                    name=f"{cmd.name} {cmd.signature}",
                    value=cmd.help or "No description",
                    inline=False
                )
        pages.append(info_embed)

        # Time Commands Page
        time_embed = discord.Embed(
            title="🔧 Utility Commands - Time",
            color=discord.Color.blue()
        )
        time_commands = ['timestamp', 'countdown', 'uptime']
        for cmd_name in time_commands:
            cmd = self.bot.get_command(cmd_name)
            if cmd:
                time_embed.add_field(
                    name=f"{cmd.name} {cmd.signature}",
                    value=cmd.help or "No description",
                    inline=False
                )
        pages.append(time_embed)

        # Misc Utility Commands Page
        misc_embed = discord.Embed(
            title="🔧 Utility Commands - Miscellaneous",
            color=discord.Color.blue()
        )
        misc_commands = ['ping', 'calculate', 'tinyurl', 'hexcolor']
        for cmd_name in misc_commands:
            cmd = self.bot.get_command(cmd_name)
            if cmd:
                misc_embed.add_field(
                    name=f"{cmd.name} {cmd.signature}",
                    value=cmd.help or "No description",
                    inline=False
                )
        pages.append(misc_embed)

        return pages

async def setup(bot):
    logger = CogLogger("Utility")
    try:
        await bot.add_cog(Utility(bot))
        logger.info("Utility cog loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load Utility cog: {e}")
        raise