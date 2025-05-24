import discord
from discord.ext import commands

class SyncRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_member_join(self, member): # on join
        pass

    @commands.Cog.listener()
    async def on_member_update(self, before, after): # on role change
        pass

    @commands.Cog.listener()
    async def on_member_remove(self, member): # on leave
        pass

    @commands.Cog.listener()
    async def on_ready(self):
        print("[!] SyncRoles cog loaded")

def setup(bot):
    bot.add_cog(SyncRoles(bot))