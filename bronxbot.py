import discord
import json
from discord.ext import commands

with open("data/config.json", "r") as f:
    config = json.load(f)

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

async def load_cogs():
    try:
        await bot.load_extension('cogs.SyncRoles')
        print("[+] Successfully loaded SyncRoles cog")
    except Exception as e:
        print(f"[-] Failed to load SyncRoles cog: {e}")

@bot.event
async def on_ready():
    await load_cogs()
    print(f'[?] Logged in as {bot.user.name} (ID: {bot.user.id})')

bot.run(config['TOKEN'])