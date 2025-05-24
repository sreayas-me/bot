import discord
import json
from discord.ext import commands

with open("data/config.json", "r") as f:
    config = json.load(f)

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

async def load_cogs():
    for file in ["cogs.ModMail", "cogs.SyncRoles", "cogs.VoteBans"]:
        try:
            await bot.load_extension(file)
        except Exception as e:
            print(f"Failed to load cog {file}: {e}")

@bot.event
async def on_ready():
    await load_cogs()
    print(f'[?] Logged in as {bot.user.name} (ID: {bot.user.id})')

bot.run(config['TOKEN'])