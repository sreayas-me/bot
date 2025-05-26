import discord
import random
import json
from discord.ext import commands
from cogs.logging.logger import CogLogger
from utils.db import db

logger = CogLogger('Welcoming')

async def welcomeEmbed(member):
    with open('data/welcome.json', 'r') as f:
        data = json.load(f)
    character_key = random.choice(list(data['characters'].keys()))
    character_url = data['characters'][character_key]
    
    return discord.Embed(
        description=f"\"{random.choice(data['messages'])}\"\n\n[main](https://discord.gg/furryporn) • [backup](https://discord.gg/W563EnFwed) • [appeal](https://discord.gg/6Th9dsw6rM)",
        color=discord.Color.random()
    ).set_author(
        name=character_key.lower(),
        icon_url=character_url,
        url="https://discord.gg/6Th9dsw6rM"
    ).set_footer(text="click name to appeal if banned")

class Welcoming(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.main_guilds = self.bot.MAIN_GUILD_IDS
    
    async def cog_check(self, ctx):
        """Check if the guild has permission to use this cog's commands"""
        return ctx.guild.id in self.main_guilds

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id not in self.main_guilds:
            return

        """Sync roles when a member joins any server"""
        logger.info(f"[+] Member joined: {member.name} in guild {member.guild.id}")

        randomEmoji = random.choice(member.guild.emojis)

        greeting = ["hi", "yo", "hola", "bonjour", "hhhjhhhiiiiii", "haiiiiii :3", "haaaaaaaiiiiiii", "hello", "hhiihihihiihihi"]

        if member.guild.id == 1259717095382319215:
            channel = member.guild.get_channel(1368768246475391037)
            await channel.send(f"{member.mention} {random.choice(greeting)} {randomEmoji}")
            embed = await welcomeEmbed(member)
            await member.send(embed=embed)
            await db.store_stats(member.guild.id, "gained")

    @commands.command()
    async def welcometest(self, ctx):
        await ctx.author.send(embed=await welcomeEmbed(ctx.author))  

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if member.guild.id not in self.main_guilds:
            return
            
        logger.info(f"[-] Member left: {member} in guild {member.guild.id}")
        if member.guild.id == 1259717095382319215:
            await db.store_stats(member.guild.id, "lost")

async def setup(bot):
    try:
        await bot.add_cog(Welcoming(bot))
        logger.info("Welcoming cog loaded successfully")

    except Exception as e:
        logger.error(f"Failed to load Welcoming cog: {e}")
        raise e