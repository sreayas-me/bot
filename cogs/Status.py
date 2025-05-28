import discord
from discord.ext import commands
import datetime
from cogs.logging.logger import CogLogger
from cogs.Help import HelpPaginator

class Status(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = CogLogger(self.__class__.__name__)
        self.shard_stats = {}  # Track stats per shard
        self.update_shard_stats()

    def update_shard_stats(self):
        """Update stats for all shards"""
        for shard_id in range(self.bot.shard_count):
            guilds = [g for g in self.bot.guilds if g.shard_id == shard_id]
            users = sum(g.member_count for g in guilds)
            
            if shard_id not in self.shard_stats:
                self.shard_stats[shard_id] = {
                    'start_time': discord.utils.utcnow(),
                    'last_seen': discord.utils.utcnow(),
                    'status': 'online'
                }
            
            self.shard_stats[shard_id].update({
                'guild_count': len(guilds),
                'user_count': users,
                'latency': self.bot.latencies[shard_id][1] * 1000,
                'last_seen': discord.utils.utcnow()
            })

    @commands.command(name="shards", aliases=["status"])
    async def shards(self, ctx):
        """View bot shard status"""
        self.update_shard_stats()
        
        pages = []
        overview = discord.Embed(
            title="🔋 Shard Status",
            color=ctx.author.color or discord.Color.blue()
        )
        
        total_guilds = sum(s['guild_count'] for s in self.shard_stats.values())
        total_users = sum(s['user_count'] for s in self.shard_stats.values())
        avg_latency = sum(s['latency'] for s in self.shard_stats.values()) / len(self.shard_stats)
        
        overview.description = (
            f"**Total Servers:** `{total_guilds:,}`\n"
            f"**Total Users:** `{total_users:,}`\n"
            f"**Average Latency:** `{avg_latency:.1f}ms`\n"
            f"**Shards:** `{self.bot.shard_count}`\n\n"
            "**Shard Status**\n"
        )
        
        # Add short status for first few shards
        for shard_id, stats in list(self.shard_stats.items())[:3]:
            status = stats['status']
            emoji = "🟢" if status == "online" else "🔴"
            overview.description += (
                f"{emoji} Shard {shard_id}: `{stats['guild_count']} servers` | "
                f"`{stats['latency']:.1f}ms`\n"
            )
        
        if len(self.shard_stats) > 3:
            overview.description += "*Use the arrows to see more shards*"
            
        pages.append(overview)
        
        # Create detail pages - 5 shards per page
        shards = list(self.shard_stats.items())
        for i in range(0, len(shards), 5):
            embed = discord.Embed(
                title="🔋 Shard Details",
                color=ctx.author.color or discord.Color.blue()
            )
            
            for shard_id, stats in shards[i:i+5]:
                uptime = discord.utils.utcnow() - stats['start_time']
                days, hours = uptime.days, uptime.seconds//3600
                minutes = (uptime.seconds//60) % 60
                
                status = stats['status']
                emoji = "🟢" if status == "online" else "🔴"
                
                embed.add_field(
                    name=f"{emoji} Shard {shard_id}",
                    value=(
                        f"**Servers:** `{stats['guild_count']:,}`\n"
                        f"**Users:** `{stats['user_count']:,}`\n"
                        f"**Latency:** `{stats['latency']:.1f}ms`\n"
                        f"**Uptime:** `{days}d {hours}h {minutes}m`"
                    ),
                    inline=False
                )
            
            pages.append(embed)
        
        view = HelpPaginator(pages, ctx.author)
        view.update_buttons()
        message = await ctx.reply(embed=pages[0], view=view)
        view.message = message

    @commands.Cog.listener()
    async def on_shard_ready(self, shard_id):
        """Track when a shard comes online"""
        self.logger.info(f"Shard {shard_id} ready")
        if shard_id not in self.shard_stats:
            self.shard_stats[shard_id] = {}
        self.shard_stats[shard_id].update({
            'start_time': discord.utils.utcnow(),
            'last_seen': discord.utils.utcnow(),
            'status': 'online'
        })
        self.update_shard_stats()

    @commands.Cog.listener() 
    async def on_shard_disconnect(self, shard_id):
        """Track when a shard disconnects"""
        self.logger.warning(f"Shard {shard_id} disconnected")
        if shard_id in self.shard_stats:
            self.shard_stats[shard_id]['status'] = 'offline'

async def setup(bot):
    await bot.add_cog(Status(bot))
