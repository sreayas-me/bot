import discord, json
from discord.ext import commands

with open("data/config.json", "r") as f:
    config = json.load(f)

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

@bot.event
async def on_ready():
    bot.load_extension('cogs.syncroles')
    print(f'[?] Logged in as {bot.user.name} (ID: {bot.user.id})')

bot.run(config['TOKEN'])