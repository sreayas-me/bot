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
guilds = [1259717095382319215, 1299747094449623111, 1142088882222022786]
class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.guild.id in guilds:
            with open("data/stats.json", "r") as f:
                data = json.load(f)
                data["stats"][str(message.guild.id)]["messages"] += 1
            with open("data/stats.json", "w") as f:
                json.dump(data, f, indent=2)


    @commands.command(name="stats", aliases=["st"])
    @commands.is_owner()
    async def stats(self, ctx):
        with open("data/stats.json", "r") as f:
            data = json.load(f)
            dt = data["stats"][str(ctx.guild.id)]["timestamp"] 
            #unix_timestamp = int(dt.timestamp())

        embed = discord.Embed(
            description=f"""
            `messages {data["stats"][str(ctx.guild.id)]["messages"]}`
            `members gained {data["stats"][str(ctx.guild.id)]["gained"]}`
            `members lost {data["stats"][str(ctx.guild.id)]["lost"]}`
            `total g/l {data["stats"][str(ctx.guild.id)]["gained"] - data["stats"][str(ctx.guild.id)]["lost"]}`
            """,
            color=discord.Color.random()
        )
        embed.set_thumbnail(url=self.bot.user.avatar.url)
        #embed.timestamp = dt
        await ctx.reply(embed=embed)

    @commands.command(name="resetstats", aliases=["rst"])
    @commands.is_owner()
    async def resetstats(self, ctx):
        with open("data/stats.json", "r") as f:
            data = json.load(f)
            data["stats"][str(ctx.guild.id)]["messages"] = 0
            data["stats"][str(ctx.guild.id)]["gained"] = 0
            data["stats"][str(ctx.guild.id)]["lost"] = 0
            data["stats"][str(ctx.guild.id)]["timestamp"] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        with open("data/stats.json", "w") as f:
            json.dump(data, f, indent=2)
        await ctx.reply("Stats have been reset for this guild!")

async def setup(bot):
    try:
        await bot.add_cog(Stats(bot))
        logger.info("Stats cog loaded successfully")

    except Exception as e:
        logger.error(f"Failed to load Stats cog: {e}")
        raise e