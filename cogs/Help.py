import discord
from discord.ext import commands
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('data/logs/Help.log')
    ]
)
logger = logging.getLogger('Help')

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="help", aliases=["h"])
    async def help(self, ctx, *, command=None):
        """shows this help message"""
        try:
            if command:
                # Show help for specific command
                cmd = self.bot.get_command(command.lower())
                if not cmd:
                    return await ctx.reply(f"```no command found for '{command}'```")
                
                embed = discord.Embed(color=ctx.author.accent_color)
                embed.set_author(name=f"command help: {cmd.name}", icon_url=self.bot.user.display_avatar.url)
                
                description = f"```{cmd.help or 'no description provided'}```\n"
                description += f"```usage: {ctx.prefix}{cmd.name} {cmd.signature}```\n"
                
                if cmd.aliases:
                    description += f"```aliases: {', '.join(cmd.aliases)}```"
                
                embed.description = description
                return await ctx.reply(embed=embed)
            
            # Main help menu
            embed = discord.Embed(color=ctx.author.accent_color)
            embed.set_author(name="command list", icon_url=self.bot.user.display_avatar.url)
            
            description = "```use help [command] for more info```\n"
            
            for cog_name, cog in self.bot.cogs.items():
                if cog_name.lower() in ['economy']:  # Skip dev/debug cogs
                    continue
                    
                commands_list = [f"{ctx.prefix}{cmd.name}" for cmd in cog.get_commands()]
                if commands_list:
                    description += f"```{cog_name.lower()}:\n  {'  '.join(commands_list)}```\n"
            
            embed.description = description
            embed.set_footer(text=f"total commands: {len(self.bot.commands)}")
            
            await ctx.reply(embed=embed)
            
        except Exception as e:
            logger.error(f"error in help command: {e}")
            await ctx.reply("```an error occurred while processing the help command```")

async def setup(bot):
    try:
        await bot.add_cog(Help(bot))
        logger.info("help cog loaded successfully")
    except Exception as e:
        logger.error(f"failed to load help cog: {e}")
        raise e