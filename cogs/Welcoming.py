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
        logging.FileHandler('data/logs/welcoming.log')
    ]
)
logger = logging.getLogger('Welcoming')

async def welcomeEmbed(member):
    with open('data/messages.json', 'r') as f:
        data = json.load(f)
    character = random.choice(data['characters'])
    welcomeEmbed = discord.Embed(
        description=f"\"{random.choice(data['messages'])}\"\n-# [Main Server](https://discord.gg/furryporn) |  [Backup Server](https://discord.gg/W563EnFwed) | [Appeal Server](https://discord.gg/6Th9dsw6rM)",
        color=discord.Color.random()
    )
    welcomeEmbed.set_author(name=character.title(), icon_url=data['character'][character], url="https://discord.gg/6Th9dsw6rM")
    welcomeEmbed.set_footer(text="click the title to join the appeal server if you get banned", icon_url=member.guild.icon.url)
    return welcomeEmbed

class Welcoming(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
@commands.Cog.listener()
async def on_member_join(self, member):
    """Sync roles when a member joins any server"""
    logger.info(f"[+] Member joined: {member} in guild {member.guild.id}")
    await self.sync_roles(member, member.guild)

    randomEmoji = random.choice(member.guild.emojis)

    greeting = ["hi", "yo", "hola", "bonjour", "hhhjhhhiiiiii", "haiiiiii :3", "haaaaaaaiiiiiii", "hello", "hhiihihihiihihi"]

    if member.guild.id == 1259717095382319215:
        channel = member.guild.get_channel(1368768246475391037)
        await channel.send(f"{random.choice(greeting)} {member.mention} {randomEmoji}")
        embed = welcomeEmbed
        await member.send(embed=embed)
        with open("data/stats.json", "r") as f:
            data = json.load(f)
            data["stats"][str(member.guild.id)]["gained"] += 1
            with open("data/stats.json", "w") as f:
                json.dump(data, f, indent=2)

@commands.command()
async def welcometest(self, ctx):
    await ctx.author.send(embed=welcomeEmbed(ctx.author))

@commands.Cog.listener()
async def on_member_remove(self, member):
    logger.info(f"[-] Member left: {member} in guild {member.guild.id}")
    if member.guild.id == 1259717095382319215:
        with open("data/stats.json", "r") as f:
            data = json.load(f)
            data["stats"][str(member.guild.id)]["lost"] -= 1
            with open("data/stats.json", "w") as f:
                json.dump(data, f, indent=2)

async def setup(bot):
    try:
        await bot.add_cog(Welcoming(bot))
        logger.info("Welcoming cog loaded successfully")

    except Exception as e:
        logger.error(f"Failed to load Welcoming cog: {e}")
        raise e