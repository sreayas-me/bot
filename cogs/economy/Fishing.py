from discord.ext import commands
from cogs.logging.logger import CogLogger
from utils.db import async_db as db
import discord
import random
import uuid
import datetime
import asyncio

class Fishing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = CogLogger(self.__class__.__name__)
        self.currency = "<:bronkbuk:1377389238290747582>"
        self.DEFAULT_FISHING_ITEMS = {
            "bait_shop": {
                "beginner_bait": {
                    "name": "Beginner Bait",
                    "price": 0,
                    "amount": 10,
                    "description": "Basic bait for catching fish",
                    "catch_rates": {"normal": 1.0, "rare": 0.1}
                },
                "pro_bait": {
                    "name": "Pro Bait",
                    "price": 50,
                    "amount": 10,
                    "description": "Better chances for rare fish",
                    "catch_rates": {"normal": 1.2, "rare": 0.3, "event": 0.1}
                }
            }
        }

    @commands.command(name="fish", aliases=["fishing"])
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def fish(self, ctx):
        """Go fishing! Requires a rod and bait."""
        fishing_items = await db.get_fishing_items(ctx.author.id)
        
        if not fishing_items["rods"]:
            embed = discord.Embed(
                title="🎣 First Time Fishing!",
                description="You need a fishing rod and bait to start fishing!\nVisit the shop to get your free beginner gear:",
                color=0x2b2d31
            )
            embed.add_field(
                name="Free Starter Pack",
                value="• Beginner Rod (0 coins)\n• 10x Beginner Bait (0 coins)",
                inline=False
            )
            return await ctx.reply(embed=embed)
        
        if not fishing_items["bait"]:
            return await ctx.reply("❌ You need bait to go fishing! Buy some from `.shop bait`")
        
        rod = fishing_items["rods"][0]
        bait = fishing_items["bait"][0]
        
        if not await db.remove_bait(ctx.author.id, bait["id"]):
            return await ctx.reply("❌ Failed to use bait!")
            
        base_chances = {
            "normal": 0.7 * bait.get("catch_rates", {}).get("normal", 1.0),
            "rare": 0.2 * bait.get("catch_rates", {}).get("rare", 0.1),
            "event": 0.08 * bait.get("catch_rates", {}).get("event", 0.0),
            "mutated": 0.02 * bait.get("catch_rates", {}).get("mutated", 0.0)
        }
        
        rod_mult = rod.get("multiplier", 1.0)
        chances = {k: v * rod_mult for k, v in base_chances.items()}
        
        roll = random.random()
        cumulative = 0
        caught_type = "normal"
        
        for fish_type, chance in chances.items():
            cumulative += chance
            if roll <= cumulative:
                caught_type = fish_type
                break
                
        value_range = {
            "normal": (10, 100),
            "rare": (100, 500),
            "event": (500, 2000),
            "mutated": (2000, 10000)
        }[caught_type]
        
        fish = {
            "id": str(uuid.uuid4()),
            "type": caught_type,
            "name": f"{caught_type.title()} Fish",
            "value": random.randint(*value_range),
            "caught_at": datetime.datetime.utcnow().isoformat(),
            "bait_used": bait["id"],
            "rod_used": rod["id"]
        }
        
        if await db.add_fish(ctx.author.id, fish):
            embed = discord.Embed(
                title="🎣 Caught a Fish!",
                description=f"You caught a **{fish['name']}**!\nValue: **{fish['value']}** {self.currency}",
                color=discord.Color.blue()
            )
            
            if caught_type in ["rare", "event", "mutated"]:
                embed.set_footer(text="Wow! That's a special catch!")
            
            await ctx.reply(embed=embed)
        else:
            await ctx.reply("❌ Failed to store your catch!")

    @commands.command(name="fish_inv", aliases=["finv"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def fish_inventory(self, ctx):
        """View your fishing inventory"""
        fishing_items = await db.get_fishing_items(ctx.author.id)
        fish = await db.get_fish(ctx.author.id)
        
        pages = []
        
        # Equipment page
        equip_embed = discord.Embed(
            title="🎣 Fishing Equipment",
            color=discord.Color.blue()
        )
        
        rods_text = ""
        for rod in fishing_items["rods"]:
            rods_text += f"**{rod['name']}**\n• Multiplier: {rod['multiplier']}x\n• {rod['description']}\n\n"
        equip_embed.add_field(
            name="🎣 Fishing Rods",
            value=rods_text or "No rods",
            inline=False
        )
        
        bait_text = ""
        for bait in fishing_items["bait"]:
            bait_text += f"**{bait['name']}** (x{bait.get('amount', 1)})\n• {bait['description']}\n\n"
        equip_embed.add_field(
            name="🪱 Bait",
            value=bait_text or "No bait",
            inline=False
        )
        
        pages.append(equip_embed)
        
        # Fish collection pages
        if fish:
            fish_by_type = {}
            for f in fish:
                fish_by_type.setdefault(f["type"], []).append(f)
                
            for fish_type, fish_list in fish_by_type.items():
                embed = discord.Embed(
                    title=f"🐟 {fish_type.title()} Fish Collection",
                    color=discord.Color.blue()
                )
                
                total_value = sum(f["value"] for f in fish_list)
                embed.description = f"Total Value: **{total_value}** {self.currency}\nAmount: {len(fish_list)}"
                
                for fish in sorted(fish_list, key=lambda x: x["value"], reverse=True)[:5]:
                    embed.add_field(
                        name=f"{fish['name']} ({fish['value']} {self.currency})",
                        value=f"Caught: {fish['caught_at'].split('T')[0]}",
                        inline=False
                    )
                    
                pages.append(embed)
        else:
            pages.append(discord.Embed(
                title="🐟 Fish Collection",
                description="You haven't caught any fish yet!\nUse `.fish` to start fishing.",
                color=discord.Color.blue()
            ))
            
        view = discord.ui.View()
        if len(pages) > 1:
            view.add_item(discord.ui.Button(label="Next Page", style=discord.ButtonStyle.primary))
        
        await ctx.reply(embed=pages[0], view=view)

    @commands.command(name="sell_fish", aliases=["sellf"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def sell_fish(self, ctx, fish_id: str = "all"):
        """Sell fish from your inventory"""
        fish = await db.get_fish(ctx.author.id)
        if not fish:
            return await ctx.reply("You don't have any fish to sell!")
            
        if fish_id.lower() == "all":
            total_value = sum(f["value"] for f in fish)
            if await db.update_balance(ctx.author.id, total_value):
                await db.clear_fish(ctx.author.id)
                embed = discord.Embed(
                    title="🐟 Fish Sold!",
                    description=f"Sold {len(fish)} fish for **{total_value}** {self.currency}",
                    color=discord.Color.green()
                )
                return await ctx.reply(embed=embed)
            await ctx.reply("❌ Failed to sell fish!")
        else:
            fish_to_sell = next((f for f in fish if f["id"] == fish_id), None)
            if not fish_to_sell:
                return await ctx.reply("❌ Fish not found in your inventory!")
                
            if await db.update_balance(ctx.author.id, fish_to_sell["value"]):
                await db.remove_fish(ctx.author.id, fish_id)
                embed = discord.Embed(
                    title="🐟 Fish Sold!",
                    description=f"Sold {fish_to_sell['name']} for **{fish_to_sell['value']}** {self.currency}",
                    color=discord.Color.green()
                )
                return await ctx.reply(embed=embed)
            await ctx.reply("❌ Failed to sell fish!")

async def setup(bot):
    await bot.add_cog(Fishing(bot))