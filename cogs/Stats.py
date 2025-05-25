import discord
import json
from discord.ext import commands
import logging
import datetime
#from dateutil.parser import parse 

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('data/logs/stats.log')
    ]
)
logger = logging.getLogger('Stats')

class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.guild.id == 1259717095382319215:
            with open("data/stats.json", "r") as f:
                data = json.load(f)
                data["messages"] += 1
            with open("data/stats.json", "w") as f:
                json.dump(data, f, indent=2)


    @commands.command(name="stats", aliases=["st"])
    @commands.is_owner()
    async def stats(self, ctx):
        with open("data/stats.json", "r") as f:
            data = json.load(f)
            dt = data["timestamp"] 
            #unix_timestamp = int(dt.timestamp())

        embed = discord.Embed(
            description=f"""
            `messages {data["messages"]}`
            `members gained {data["gained"]}`
            `members lost {data["lost"]}`
            `total g/l {data["gained"] - data["lost"]}`
            """,
            color=discord.Color.random()
        )
        embed.set_thumbnail(url=self.bot.user.avatar.url)
        embed.timestamp = dt
        await ctx.reply(embed=embed)

    @commands.command(name="resetstats", aliases=["rst"])
    @commands.is_owner()
    async def resetstats(self, ctx):
        with open("data/stats.json", "w") as f:
            json.dump({"gained": 0, "lost": 0, "messages": 0, "timestamp": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")}, f, indent=2)
        await ctx.reply("Stats have been reset!")

async def setup(bot):
    try:
        await bot.add_cog(Stats(bot))
        logger.info("Stats cog loaded successfully")

    except Exception as e:
        logger.error(f"Failed to load Stats cog: {e}")
        raise e