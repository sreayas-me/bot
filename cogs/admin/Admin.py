import discord
from discord.ext import commands
from cogs.logging.logger import CogLogger
from utils.db import db
import json
import datetime
import random
import asyncio
import aiohttp
import os
import traceback
from typing import Optional, List
from cogs.Help import HelpPaginator

logger = CogLogger('Admin')

class Admin(commands.Cog):
    """Admin-only commands for bot management"""
    def __init__(self, bot):
        self.bot = bot
        self.logger = logger
        self.data_file = "data/shop.json"
        
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        
        self.last_global_buff = None
        self.global_buff_task = None 
        self.buff_types = {
            # Economy Buffs
            "money": {
                "name": "Money Boost",
                "description": "Increases money earned from all sources",
                "commands": ["work", "daily", "slots"]
            },
            "luck": {"name": "Lucky Charm", "description": "Increases winning chances in games", "commands": ["slots", "blackjack", "coinflip"]},
            "multiplier": {"name": "Prize Multiplier", "description": "Multiplies all rewards", "commands": ["all"]},
            "xp": {"name": "XP Boost", "description": "Increases XP gained from actions", "commands": ["chat", "work"]},
            "slots": {"name": "Slots Luck", "description": "Increases slots winning chance", "commands": ["slots"]},
            "daily": {"name": "Daily Bonus", "description": "Increases daily reward amount", "commands": ["daily"]},
            
            # Crime & Protection
            "rob": {"name": "Thief's Luck", "description": "Increases rob success rate", "commands": ["rob"]},
            "protection": {"name": "Bank Protection", "description": "Reduces money lost from robberies", "commands": ["passive"]},
            "stealth": {"name": "Stealth Master", "description": "Reduces chance of getting caught", "commands": ["rob", "heist"]},
            "escape": {"name": "Quick Escape", "description": "Higher chance to escape police", "commands": ["rob", "heist"]},
            
            # Gambling & Games
            "blackjack": {"name": "Card Sharp", "description": "Better blackjack winning odds", "commands": ["blackjack"]},
            "poker": {"name": "Poker Face", "description": "Improved poker winnings", "commands": ["poker"]},
            "dice": {"name": "Lucky Dice", "description": "Better rolls in dice games", "commands": ["dice", "roll"]},
            "jackpot": {"name": "Jackpot Hunter", "description": "Better chances in jackpot games", "commands": ["jackpot"]},
            
            # Trading & Economy
            "trade": {"name": "Merchant's Blessing", "description": "Better shop prices", "commands": ["buy", "sell"]},
            "interest": {"name": "Bank Interest", "description": "Increases bank interest rate", "commands": ["bank"]},
            "market": {"name": "Market Insight", "description": "Better prices when trading items", "commands": ["trade", "market"]},
            "finder": {"name": "Treasure Finder", "description": "Find better items while exploring", "commands": ["explore", "search"]},
            
            # Special Buffs
            "combo": {"name": "Combo Master", "description": "Chain wins for increasing rewards", "commands": ["all games"]},
            "recovery": {"name": "Loss Recovery", "description": "Partial refund on losses", "commands": ["all games"]},
            "streak": {"name": "Streak Protection", "description": "Chance to keep streak on loss", "commands": ["daily", "work"]},
            "vip": {"name": "VIP Status", "description": "Premium rewards and bonuses", "commands": ["all"]}
        }
        self.load_shop_data()

    def load_shop_data(self) -> None:
        """Load shop data from file"""
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                self.shop_data = data.get("global", {"items": {}, "potions": {}, "buffs": {}})
                self.server_shops = data.get("servers", {})
        except FileNotFoundError:
            self.shop_data = {"items": {}, "potions": {}, "buffs": {}}
            self.server_shops = {}
            self.save_shop_data()

    def save_shop_data(self) -> None:
        """Save shop data to file"""
        with open(self.data_file, 'w') as f:
            json.dump({
                "global": self.shop_data,
                "servers": self.server_shops
            }, f, indent=2)

    def get_server_shop(self, guild_id: int) -> dict:
        """Get server-specific shop data"""
        return self.server_shops.get(str(guild_id), {"items": {}, "potions": {}})

    @commands.group(name="shopm", aliases=["ashop", "adminshop"], invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def adminshop_group(self, ctx):
        """Server shop management commands
        shopManagement commands"""
        if not ctx.invoked_subcommand:
            embed = discord.Embed(
                description=(
                    "**Server Shop Management**\n"
                    "`.adminshop add <name> <price> <description>` - Add server item\n"
                    "`.adminshop potion <name> <price> <type> <mult> <duration>` - Add server potion\n"
                    "`.adminshop remove <name>` - Remove from server shop\n"
                    "`.adminshop list` - List server items\n\n"
                    "**Global Shop (Bot Admin Only)**\n"
                    "`.adminshop global ...` - Manage global shop"
                ),
                color=0x2b2d31
            )
            await ctx.send(embed=embed)

    @adminshop_group.command(name="add")
    @commands.has_permissions(administrator=True)
    async def adminshop_add(self, ctx, name: str = None, price: int = None, *, description: str = None):
        """Add an item to the server shop"""
        await self.server_add_item(ctx, name, price, description)

    def parse_duration(self, duration_str: str) -> int:
        """Parse duration string into minutes
        Accepts formats: 10h, 10m, 1h, 5m 2s, 2s, 29s, 2.9s, 3.9m, 1e2s"""
        try:
            total_seconds = 0
            parts = duration_str.lower().split()
            
            for part in parts:
                if 'e' in part:  # Scientific notation
                    num = float(part.rstrip('s'))
                    total_seconds += num
                    continue
                    
                number = ''
                unit = ''
                for char in part:
                    if char.isdigit() or char == '.':
                        number += char
                    else:
                        unit += char
                
                value = float(number)
                if unit == 'h':
                    total_seconds += value * 3600
                elif unit == 'm':
                    total_seconds += value * 60
                elif unit == 's':
                    total_seconds += value
                    
            return max(1, round(total_seconds / 60))  # Convert to minutes, minimum 1
            
        except Exception:
            return None

    def parse_multiplier(self, multiplier_str: str) -> float:
        """Parse multiplier string into float
        Accepts formats: 2.3x, 2x, 150%, 30%, 15x"""
        try:
            multiplier_str = multiplier_str.lower().strip()
            if multiplier_str.endswith('%'):
                # Convert percentage to multiplier (30% -> 1.3)
                return 1 + (float(multiplier_str[:-1]) / 100)
            elif multiplier_str.endswith('x'):
                return float(multiplier_str[:-1])
            else:
                return float(multiplier_str)
        except Exception:
            return None

    @adminshop_group.command(name="potion")
    @commands.has_permissions(administrator=True)
    async def adminshop_potion(self, ctx, name: str = None, price: int = None, type: str = None,
                        multiplier_str: str = None, duration_str: str = None, *, description: str = None):
        """Add a potion to the server shop"""
        if not any([name, price, type, multiplier_str, duration_str]):
            embed = discord.Embed(
                title="Potion Creation Guide",
                description=(
                    "**Usage:** `.adminshop potion <name> <price> <type> <multiplier> <duration> [description]`\n\n"
                    "**Available Buff Types:**\n" + 
                    "\n".join(f"• **{k}** - {v['name']}: {v['description']}" for k,v in self.buff_types.items()) +
                    "\n\n**Multiplier Formats:**\n"
                    "• Percentage: `30%`, `150%`\n"
                    "• Multiplier: `1.3x`, `2x`, `15x`\n"
                    "\n**Duration Formats:**\n"
                    "• Hours: `2h`, `1.5h`\n"
                    "• Minutes: `30m`, `5m`\n"
                    "• Seconds: `90s`, `1e2s`\n"
                    "• Combined: `1h 30m`, `5m 30s`"
                ),
                color=0x2b2d31
            )
            await ctx.reply(embed=embed)
            return

        # Parse multiplier and duration
        if multiplier_str:
            multiplier = self.parse_multiplier(multiplier_str)
            if multiplier is None:
                return await ctx.reply("❌ Invalid multiplier format! Use `2x`, `150%`, etc.")
        else:
            multiplier = None

        if duration_str:
            duration = self.parse_duration(duration_str)
            if duration is None:
                return await ctx.reply("❌ Invalid duration format! Use `1h`, `30m`, `90s`, etc.")
        else:
            duration = None

        await self.server_add_potion(ctx, name, price, type, multiplier, duration, description)

    @adminshop_group.command(name="remove")
    @commands.has_permissions(administrator=True)
    async def adminshop_remove(self, ctx, *, name: str):
        """Remove item from server shop"""
        await self.server_remove(ctx, name)

    @adminshop_group.command(name="list") 
    @commands.has_permissions(administrator=True)
    async def adminshop_list(self, ctx):
        """List server shop items"""
        await self.server_list(ctx)

    @adminshop_group.group(name="global", invoke_without_command=True)
    @commands.is_owner()
    async def adminshop_global(self, ctx):
        """Global shop management
        gshopManagement commands"""
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                description=(
                    "**Global Shop Management**\n"
                    "`.adminshop global add <name> <price> <desc>` - Add item\n"
                    "`.adminshop global potion <name> <price> <type> <mult> <dur>` - Add potion\n"
                    "`.adminshop global remove <name>` - Remove item\n"
                    "`.adminshop global list` - List items"
                ),
                color=0x2b2d31
            )
            await ctx.send(embed=embed)

    @adminshop_global.command(name="potion")
    @commands.is_owner()
    async def global_shop_potion(self, ctx, name: str = None, price: int = None, type: str = None,
                          multiplier_str: str = None, duration_str: str = None, *, description: str = None):
        """Add a potion to the global shop"""
        # Parse multiplier and duration
        if multiplier_str:
            multiplier = self.parse_multiplier(multiplier_str)
            if multiplier is None:
                return await ctx.reply("❌ Invalid multiplier format! Use `2x`, `150%`, etc.")
        else:
            multiplier = None

        if duration_str:
            duration = self.parse_duration(duration_str)
            if duration is None:
                return await ctx.reply("❌ Invalid duration format! Use `1h`, `30m`, `90s`, etc.")
        else:
            duration = None

        # Validate inputs
        if not all([name, price, type, multiplier, duration]):
            return await ctx.invoke(self.adminshop_potion)

        if type not in self.buff_types:
            embed = discord.Embed(description="❌ Invalid buff type", color=0x2b2d31)
            return await ctx.reply(embed=embed)

        # Add potion to global shop
        potion_id = name.lower().replace(" ", "_")
        self.shop_data["potions"][potion_id] = {
            "name": name,
            "price": price,
            "type": type,
            "multiplier": multiplier,
            "duration": duration,
            "description": description or self.buff_types[type]["description"]
        }

        self.save_shop_data()
        
        embed = discord.Embed(
            description=f"✨ Added potion **{name}** to global shop\n"
                      f"Type: {type}\n"
                      f"Effect: {multiplier}x for {duration}min\n"
                      f"Price: {price} 💰",
            color=0x2b2d31
        )
        await ctx.reply(embed=embed)

    async def display_shop(self, ctx, shop_data, title="Shop", show_admin=False):
        """Display shop contents with pagination"""
        pages = []
        
        # Overview with flash sales
        overview = discord.Embed(
            title=title,
            description=f"Your Balance: **{await db.get_wallet_balance(ctx.author.id)}** {self.currency}\n\n",
            color=0x2b2d31
        )
        
        # Add items
        if shop_data.get("items"):
            items_text = []
            for name, item in shop_data["items"].items():
                items_text.append(
                    f"**{item['name']}** - {item['price']} {self.currency}\n"
                    f"{item['description']}\n"
                    f"`buy {name}` to purchase\n"
                )
            if items_text:
                overview.add_field(
                    name="📦 Items",
                    value="\n".join(items_text[:3]) + "\n*Use the arrows to see more items*",
                    inline=False
                )
                
        # Add potions
        if shop_data.get("potions"):
            potions_text = []
            for name, potion in shop_data["potions"].items():
                potions_text.append(
                    f"**{potion['name']}** - {potion['price']} {self.currency}\n"
                    f"{potion['multiplier']}x {potion['type']} buff for {potion['duration']}min\n"
                    f"`buy {name}` to purchase\n"
                )
            if potions_text:
                overview.add_field(
                    name="🧪 Potions", 
                    value="\n".join(potions_text[:3]) + "\n*Use the arrows to see more potions*",
                    inline=False
                )
        
        pages.append(overview)
        
        # Create detail pages for items
        items_chunk = list(shop_data.get("items", {}).items())
        for i in range(0, len(items_chunk), 5):
            chunk = items_chunk[i:i+5]
            embed = discord.Embed(title="📦 Items", color=0x2b2d31)
            for item_id, item in chunk:
                embed.add_field(
                    name=f"{item['name']} ({item['price']} {self.currency})",
                    value=f"{item['description']}\n`buy {item_id}` to purchase",
                    inline=False
                )
            pages.append(embed)

        # Create detail pages for potions  
        potions_chunk = list(shop_data.get("potions", {}).items())
        for i in range(0, len(potions_chunk), 5):
            chunk = potions_chunk[i:i+5]
            embed = discord.Embed(title="🧪 Potions", color=0x2b2d31)
            for potion_id, potion in chunk:
                embed.add_field(
                    name=f"{potion['name']} ({potion['price']} {self.currency})",
                    value=f"{potion['multiplier']}x {potion['type']} for {potion['duration']}min\n"
                          f"{potion['description']}\n`buy {potion_id}` to purchase",
                    inline=False
                )
            pages.append(embed)

        if not pages:
            return await ctx.send("Shop is empty!")

        view = HelpPaginator(pages, ctx.author)
        view.update_buttons()
        message = await ctx.reply(embed=pages[0], view=view)
        view.message = message

    def load_shop_data(self) -> None:
        """Load shop data from file"""
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                self.shop_data = data.get("global", {"items": {}, "potions": {}, "buffs": {}})
                self.server_shops = data.get("servers", {})
        except FileNotFoundError:
            self.shop_data = {"items": {}, "potions": {}, "buffs": {}}
            self.server_shops = {}
            self.save_shop_data()

    def save_shop_data(self) -> None:
        """Save shop data to file"""
        with open(self.data_file, 'w') as f:
            json.dump({
                "global": self.shop_data,
                "servers": self.server_shops
            }, f, indent=2)

    def get_server_shop(self, guild_id: int) -> dict:
        """Get server-specific shop data"""
        return self.server_shops.get(str(guild_id), {"items": {}, "potions": {}})

    @commands.command(name="sshop", aliases=["servershop"])
    @commands.has_permissions(administrator=True)
    async def server_shop(self, ctx):
        """Server shop management commands"""
        embed = discord.Embed(
            description=(
                "**Server Shop Management**\n"
                "`.adminshop add <name> <price> <description>` - Add server item\n"
                "`.adminshop potion <name> <price> <type> <mult> <duration>` - Add server potion\n"
                "`.adminshop remove <name>` - Remove from server shop\n"
                "`.adminshop list` - List server items\n\n"
                "**Global Shop (Bot Admin Only)**\n"
                "`.adminshop global ...` - Manage global shop"
            ),
            color=0x2b2d31
        )
        await ctx.send(embed=embed)

    @commands.group(name="adminshop", aliases=["ashop"], invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def adminshop_group(self, ctx):
        """Server shop management commands"""
        embed = discord.Embed(
            description=(
                "**Server Shop Management**\n"
                "`.adminshop add <name> <price> <description>` - Add server item\n"
                "`.adminshop potion <name> <price> <type> <mult> <duration>` - Add server potion\n"
                "`.adminshop remove <name>` - Remove from server shop\n"
                "`.adminshop list` - List server items\n\n"
                "**Global Shop (Bot Admin Only)**\n"
                "`.adminshop global ...` - Manage global shop"
            ),
            color=0x2b2d31
        )
        await ctx.send(embed=embed)

    @adminshop_group.command(name="add")
    @commands.has_permissions(administrator=True)
    async def adminshop_add(self, ctx, name: str = None, price: int = None, *, description: str = None):
        """Add an item to the server shop"""
        await self.server_add_item(ctx, name, price, description)

    @adminshop_group.command(name="potion")
    @commands.has_permissions(administrator=True)
    async def adminshop_potion(self, ctx, name: str = None, price: int = None, type: str = None,
                        multiplier_str: str = None, duration_str: str = None, *, description: str = None):
        """Add a potion to the server shop"""
        if not any([name, price, type, multiplier_str, duration_str]):
            embed = discord.Embed(
                title="Potion Creation Guide",
                description=(
                    "**Usage:** `.adminshop potion <name> <price> <type> <multiplier> <duration> [description]`\n\n"
                    "**Available Buff Types:**\n" + 
                    "\n".join(f"• **{k}** - {v['name']}: {v['description']}" for k,v in self.buff_types.items()) +
                    "\n\n**Multiplier Formats:**\n"
                    "• Percentage: `30%`, `150%`\n"
                    "• Multiplier: `1.3x`, `2x`, `15x`\n"
                    "\n**Duration Formats:**\n"
                    "• Hours: `2h`, `1.5h`\n"
                    "• Minutes: `30m`, `5m`\n"
                    "• Seconds: `90s`, `1e2s`\n"
                    "• Combined: `1h 30m`, `5m 30s`"
                ),
                color=0x2b2d31
            )
            await ctx.reply(embed=embed)
            return

        # Parse multiplier and duration
        if multiplier_str:
            multiplier = self.parse_multiplier(multiplier_str)
            if multiplier is None:
                return await ctx.reply("❌ Invalid multiplier format! Use `2x`, `150%`, etc.")
        else:
            multiplier = None

        if duration_str:
            duration = self.parse_duration(duration_str)
            if duration is None:
                return await ctx.reply("❌ Invalid duration format! Use `1h`, `30m`, `90s`, etc.")
        else:
            duration = None

        await self.server_add_potion(ctx, name, price, type, multiplier, duration, description)

    @adminshop_group.command(name="remove")
    @commands.has_permissions(administrator=True)
    async def adminshop_remove(self, ctx, *, name: str):
        """Remove item from server shop"""
        await self.server_remove(ctx, name)

    @adminshop_group.command(name="list") 
    @commands.has_permissions(administrator=True)
    async def adminshop_list(self, ctx):
        """List server shop items"""
        await self.server_list(ctx)

    @adminshop_group.group(name="global", invoke_without_command=True)
    @commands.is_owner()
    async def adminshop_global(self, ctx):
        """Global shop management"""
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                description=(
                    "**Global Shop Management**\n"
                    "`.adminshop global add <name> <price> <desc>` - Add item\n"
                    "`.adminshop global potion <name> <price> <type> <mult> <dur>` - Add potion\n"
                    "`.adminshop global remove <name>` - Remove item\n"
                    "`.adminshop global list` - List items"
                ),
                color=0x2b2d31
            )
            await ctx.send(embed=embed)

    @adminshop_global.command(name="potion")
    @commands.is_owner()
    async def global_shop_potion(self, ctx, name: str = None, price: int = None, type: str = None,
                          multiplier_str: str = None, duration_str: str = None, *, description: str = None):
        """Add a potion to the global shop"""
        # Parse multiplier and duration
        if multiplier_str:
            multiplier = self.parse_multiplier(multiplier_str)
            if multiplier is None:
                return await ctx.reply("❌ Invalid multiplier format! Use `2x`, `150%`, etc.")
        else:
            multiplier = None

        if duration_str:
            duration = self.parse_duration(duration_str)
            if duration is None:
                return await ctx.reply("❌ Invalid duration format! Use `1h`, `30m`, `90s`, etc.")
        else:
            duration = None

        # Validate inputs
        if not all([name, price, type, multiplier, duration]):
            return await ctx.invoke(self.adminshop_potion)

        if type not in self.buff_types:
            embed = discord.Embed(description="❌ Invalid buff type", color=0x2b2d31)
            return await ctx.reply(embed=embed)

        # Add potion to global shop
        potion_id = name.lower().replace(" ", "_")
        self.shop_data["potions"][potion_id] = {
            "name": name,
            "price": price,
            "type": type,
            "multiplier": multiplier,
            "duration": duration,
            "description": description or self.buff_types[type]["description"]
        }

        self.save_shop_data()
        
        embed = discord.Embed(
            description=f"✨ Added potion **{name}** to global shop\n"
                      f"Type: {type}\n"
                      f"Effect: {multiplier}x for {duration}min\n"
                      f"Price: {price} 💰",
            color=0x2b2d31
        )
        await ctx.reply(embed=embed)

    async def display_shop(self, ctx, shop_data, title="Shop", show_admin=False):
        """Display shop contents with pagination"""
        pages = []
        
        # Overview with flash sales
        overview = discord.Embed(
            title=title,
            description=f"Your Balance: **{await db.get_wallet_balance(ctx.author.id)}** {self.currency}\n\n",
            color=0x2b2d31
        )
        
        # Add items
        if shop_data.get("items"):
            items_text = []
            for name, item in shop_data["items"].items():
                items_text.append(
                    f"**{item['name']}** - {item['price']} {self.currency}\n"
                    f"{item['description']}\n"
                    f"`buy {name}` to purchase\n"
                )
            if items_text:
                overview.add_field(
                    name="📦 Items",
                    value="\n".join(items_text[:3]) + "\n*Use the arrows to see more items*",
                    inline=False
                )
                
        # Add potions
        if shop_data.get("potions"):
            potions_text = []
            for name, potion in shop_data["potions"].items():
                potions_text.append(
                    f"**{potion['name']}** - {potion['price']} {self.currency}\n"
                    f"{potion['multiplier']}x {potion['type']} buff for {potion['duration']}min\n"
                    f"`buy {name}` to purchase\n"
                )
            if potions_text:
                overview.add_field(
                    name="🧪 Potions", 
                    value="\n".join(potions_text[:3]) + "\n*Use the arrows to see more potions*",
                    inline=False
                )
        
        pages.append(overview)
        
        # Create detail pages for items
        items_chunk = list(shop_data.get("items", {}).items())
        for i in range(0, len(items_chunk), 5):
            chunk = items_chunk[i:i+5]
            embed = discord.Embed(title="📦 Items", color=0x2b2d31)
            for item_id, item in chunk:
                embed.add_field(
                    name=f"{item['name']} ({item['price']} {self.currency})",
                    value=f"{item['description']}\n`buy {item_id}` to purchase",
                    inline=False
                )
            pages.append(embed)

        # Create detail pages for potions  
        potions_chunk = list(shop_data.get("potions", {}).items())
        for i in range(0, len(potions_chunk), 5):
            chunk = potions_chunk[i:i+5]
            embed = discord.Embed(title="🧪 Potions", color=0x2b2d31)
            for potion_id, potion in chunk:
                embed.add_field(
                    name=f"{potion['name']} ({potion['price']} {self.currency})",
                    value=f"{potion['multiplier']}x {potion['type']} for {potion['duration']}min\n"
                          f"{potion['description']}\n`buy {potion_id}` to purchase",
                    inline=False
                )
            pages.append(embed)

        if not pages:
            return await ctx.send("Shop is empty!")

        view = HelpPaginator(pages, ctx.author)
        view.update_buttons()
        message = await ctx.reply(embed=pages[0], view=view)
        view.message = message

    async def rotate_global_buff(self):
        """Rotate global buffs every 15 minutes"""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                # Select new buff that's different from last one
                available_buffs = list(self.buff_types.keys())
                if self.last_global_buff:
                    available_buffs.remove(self.last_global_buff)
                
                new_buff = random.choice(available_buffs)
                self.last_global_buff = new_buff
                
                # Apply global buff
                expiry = datetime.datetime.now() + datetime.timedelta(minutes=15)
                await db.add_global_buff({
                    "type": new_buff,
                    "multiplier": 1.5,
                    "expires_at": expiry.timestamp()
                })
                
                # Announce in log channel
                channel = self.bot.get_channel(1314685928614264852)
                if channel:
                    buff_info = self.buff_types[new_buff]
                    embed = discord.Embed(
                        description=(
                            f"🌟 **new global buff active**\n"
                            f"**{buff_info['name']}**\n"
                            f"{buff_info['description']}\n"
                            f"Duration: 15 minutes\n"
                            f"Affects: {', '.join(buff_info['commands'])}"
                        ),
                        color=0x2b2d31
                    )
                    await channel.send(embed=embed)
                
                await asyncio.sleep(900)
                
            except Exception as e:
                self.logger.error(f"Error in global buff rotation: {e}")
                await asyncio.sleep(60)

    @commands.command(name="trigger")
    @commands.cooldown(1, 900, commands.BucketType.user)
    async def trigger_buff(self, ctx, buff_type: str = None):
        """Trigger the next global buff (costs 300,000, requires 5M net worth)"""
        is_owner = await self.bot.is_owner(ctx.author)
        
        if not is_owner:
            # Check requirements for non-owners
            wallet = await db.get_wallet_balance(ctx.author.id)
            bank = await db.get_bank_balance(ctx.author.id)
            net_worth = wallet + bank
            
            if net_worth < 5_000_000:
                embed = discord.Embed(description="❌ You need a net worth of 5,000,000 to use this command!", color=0x2b2d31)
                return await ctx.reply(embed=embed)
                
            if wallet < 300_000:
                embed = discord.Embed(description="❌ You need 300,000 in your wallet!", color=0x2b2d31)
                return await ctx.reply(embed=embed)

        if not buff_type:
            embed = discord.Embed(
                description=(
                    "**Available Global Buffs**\n" +
                    ("Cost: Free (Bot Owner)\n" if is_owner else "Cost: 300,000 💰\n") +
                    ("" if is_owner else "Requirement: 5M net worth\n") +
                    "\n**Usage:** `.trigger <buff>`\n\n" +
                    "**Available Buffs:**\n" +
                    "\n".join(f"• **{k}** - {v['description']}\n  *Affects: {', '.join(v['commands'])}*" 
                            for k,v in self.buff_types.items())
                ),
                color=0x2b2d31
            )
            return await ctx.reply(embed=embed)

        if buff_type not in self.buff_types:
            embed = discord.Embed(description="❌ Invalid buff type!", color=0x2b2d31)
            return await ctx.reply(embed=embed)

        if not is_owner:
            await db.update_wallet(ctx.author.id, -300_000)
        
        expiry = datetime.datetime.now() + datetime.timedelta(minutes=15)
        await db.add_global_buff({
            "type": buff_type,
            "multiplier": 1.5,
            "expires_at": expiry.timestamp(),
            "triggered_by": ctx.author.id
        })

        buff_info = self.buff_types[buff_type]
        embed = discord.Embed(
            description=(
                f"✨ **Global Buff Triggered**\n"
                f"**{buff_info['name']}** is now active for 15 minutes!\n"
                f"{buff_info['description']}\n"
                f"Affects: {', '.join(buff_info['commands'])}\n\n"
                f"Triggered by: {ctx.author.mention}"
            ),
            color=0x2b2d31
        )
        await ctx.reply(embed=embed)

    async def server_list(self, ctx):
        """List items in server shop"""
        shop_data = self.get_server_shop(ctx.guild.id)
        
        if not shop_data["items"] and not shop_data["potions"]:
            return await ctx.reply("This server's shop is empty!")

        embed = discord.Embed(title=f"{ctx.guild.name}'s Shop", color=0x2b2d31)
        
        # List items
        if shop_data["items"]:
            items_text = []
            for item_id, item in shop_data["items"].items():
                items_text.append(
                    f"**{item['name']}** - {item['price']} 💰\n"
                    f"{item['description']}"
                )
            if items_text:
                embed.add_field(
                    name="📦 Items",
                    value="\n\n".join(items_text),
                    inline=False
                )
        
        # List potions
        if shop_data["potions"]:
            potions_text = []
            for potion_id, potion in shop_data["potions"].items():
                potions_text.append(
                    f"**{potion['name']}** - {potion['price']} 💰\n"
                    f"{potion['multiplier']}x {potion['type']} buff for {potion['duration']}min"
                )
            if potions_text:
                embed.add_field(
                    name="🧪 Potions",
                    value="\n\n".join(potions_text),
                    inline=False
                )

        await ctx.reply(embed=embed)

    async def server_add_potion(self, ctx, name: str, price: int, type: str, multiplier: float, duration: int, description: str = None):
        """Add a potion to the server shop"""
        # Validate inputs
        if not all([name, price, type, multiplier, duration]):
            embed = discord.Embed(description="❌ Missing required arguments", color=0x2b2d31)
            return await ctx.reply(embed=embed)

        if type not in self.buff_types:
            embed = discord.Embed(description="❌ Invalid buff type", color=0x2b2d31)
            return await ctx.reply(embed=embed)

        if price < 0:
            embed = discord.Embed(description="❌ Price cannot be negative", color=0x2b2d31)
            return await ctx.reply(embed=embed)

        if multiplier <= 0:
            embed = discord.Embed(description="❌ Multiplier must be positive", color=0x2b2d31)
            return await ctx.reply(embed=embed)

        if duration <= 0:
            embed = discord.Embed(description="❌ Duration must be positive", color=0x2b2d31)
            return await ctx.reply(embed=embed)

        # Add potion to server shop
        guild_id = str(ctx.guild.id)
        if guild_id not in self.server_shops:
            self.server_shops[guild_id] = {"items": {}, "potions": {}}

        potion_id = name.lower().replace(" ", "_")
        self.server_shops[guild_id]["potions"][potion_id] = {
            "name": name,
            "price": price,
            "type": type,
            "multiplier": multiplier,
            "duration": duration,
            "description": description or self.buff_types[type]["description"]
        }

        self.save_shop_data()
        
        embed = discord.Embed(
            description=f"✨ Added potion **{name}** to server shop\n"
                      f"Type: {type}\n"
                      f"Effect: {multiplier}x for {duration}min\n"
                      f"Price: {price} 💰",
            color=0x2b2d31
        )
        await ctx.reply(embed=embed)

    @commands.Cog.listener()
    async def on_ready(self):
        """Cog loaded - print status"""
        self.logger.info(f"{self.__class__.__name__} loaded")

async def setup(bot):
    """Initialize the Admin cog with proper error handling"""
    try:
        data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
        os.makedirs(data_dir, exist_ok=True)
        
        if not hasattr(bot, 'session'):
            bot.session = aiohttp.ClientSession()
    
        db.ensure_connected()
        await bot.add_cog(Admin(bot))
        return True
        
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"Failed to load Admin cog:\n{tb}")
        raise RuntimeError(f"Admin cog setup failed: {str(e)}") from e
