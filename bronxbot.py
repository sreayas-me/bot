import discord
import json
import random
from discord.ext import commands

with open("data/config.json", "r") as f:
    config = json.load(f)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.reactions = True


bot = commands.Bot(command_prefix='!', intents=intents)

async def load_cogs():
    for file in ["cogs.ModMail", "cogs.SyncRoles", "cogs.VoteBans", "cogs.Welcoming", "cogs.Stats"]:
        try:
            await bot.load_extension(file)
        except Exception as e:
            print(f"Failed to load cog {file}: {e}")

@bot.event
async def on_ready():
    await load_cogs()
    print(f'[?] Logged in as {bot.user.name} (ID: {bot.user.id})')

# FIXME: remove this if hosting locally, it wont make any sense

tips = [
    "i was made in 3 hours",
    "use !help to get started",
    "use !help <command> for more info",
    "try !ban",
    "try !vban",
    "try the modmail feature if you need help",
    "did you know this bot is open source?",
    "this bot is hosted on ks' crusty old pc"   
]

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    elif message.content == bot.user.mention:
        if str(message.author.id) in config['OWNER_IDS']:
            return await message.reply(f"hola, **{random.choice(config['OWNER_REPLY'])}**\n-# `{round(bot.latency * 1000, 2)}ms`")
        await message.reply(f"hi, **{message.author.name}**\n-# {random.choice(tips)}")
    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        pass
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"**{error.command.label}** is on cooldown. Please try again in {round(error.retry_after, 2)} seconds.")
    else:
        raise error

bot.run(config['TOKEN'])