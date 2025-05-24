import discord
from discord.ext import commands
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('data/logs/sync_roles.log')
    ]
)
logger = logging.getLogger('Welcoming')

class Welcoming(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
@commands.Cog.listener()
async def on_member_join(self, member):
    """Sync roles when a member joins any server"""
    logger.info(f"Member joined: {member} in guild {member.guild.id}")
    await self.sync_roles(member, member.guild)
    if member.guild.id == 1259717095382319215:
        embed = discord.Embed(
            description="welcome to South Bronx...\n-# [Main Server](https://discord.gg/furryporn) |  [Backup Server](https://discord.gg/W563EnFwed) | [Appeal Server](https://discord.gg/6Th9dsw6rM)",
            color=discord.Color.random()
        )
        embed.set_author(name="Thanks for joining!", icon_url=member.avatar.url, url="https://discord.gg/6Th9dsw6rM")
        embed.set_footer(text="click the title to join the appeal server if you get banned", icon_url=member.guild.icon.url)
        await member.send(embed=embed)


async def setup(bot):
    try:
        await bot.add_cog(Welcoming(bot))
        logger.info("Welcoming cog loaded successfully")

    except Exception as e:
        logger.error(f"Failed to load Welcoming cog: {e}")
        raise e