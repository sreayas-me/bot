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
        self.currency = "<:bronkbuk:1377106993495412789>"
        self.db = db
        
        # Set up data file path
        self.data_file = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'shop.json')

        # Shop types configuration 
        self.SHOP_TYPES = {
            "items": {"name": "Item Shop", "description": "General items", "icon": "🛍️"},
            "potions": {"name": "Potion Shop", "description": "Buff and boost potions", "icon": "🧪"},
            "upgrades": {"name": "Upgrades Shop", "description": "Permanent upgrades", "icon": "⚡"},
            "fishing": {"name": "Fishing Shop", "description": "Fishing gear and items", "icon": "🎣"}
        }

        # Fishing configuration
        self.FISH_TYPES = {
            "normal": {
                "name": "Normal Fish",
                "rarity": 0.7,
                "value_range": (10, 100)
            },
            "rare": {
                "name": "Rare Fish", 
                "rarity": 0.2,
                "value_range": (100, 500)
            },
            "event": {
                "name": "Event Fish",
                "rarity": 0.08,
                "value_range": (500, 2000)
            },
            "mutated": {
                "name": "Mutated Fish",
                "rarity": 0.02,
                "value_range": (2000, 10000)
            }
        }

        # Add fishing shops
        self.SHOP_TYPES = {
            "bait": {
                "name": "Bait Shop",
                "description": "Buy fishing bait",
                "icon": "🪱"
            },
            "rod": {
                "name": "Rod Shop",
                "description": "Buy fishing rods",
                "icon": "🎣"
            },
            "fish": {
                "name": "Fish Shop",
                "description": "Buy and sell fish",
                "icon": "🐟"
            }
        }

        # Default items for fishing shops
        self.DEFAULT_FISHING_ITEMS = {
            "bait_shop": {
                "beginner_bait": {
                    "name": "Beginner Bait",
                    "price": 0,  # Free for first 10
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
                },
                "mutated_bait": {
                    "name": "Mutated Bait",
                    "price": 200,
                    "amount": 5,
                    "description": "Chance to catch mutated fish",
                    "catch_rates": {"normal": 1.5, "rare": 0.5, "event": 0.2, "mutated": 0.1}
                }
            },
            "rod_shop": {
                "beginner_rod": {
                    "name": "Beginner Rod",
                    "price": 0,  # Free for first one
                    "description": "Basic fishing rod",
                    "multiplier": 1.0
                },
                "pro_rod": {
                    "name": "Pro Rod",
                    "price": 5000,
                    "description": "50% better catch rates",
                    "multiplier": 1.5
                },
                "master_rod": {
                    "name": "Master Rod",
                    "price": 25000,
                    "description": "Double catch rates",
                    "multiplier": 2.0
                }
            }
        }

        self.load_shop_data()

    def load_shop_data(self) -> None:
        """Load shop data from file"""
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                self.shop_data = data.get("global", {
                    "items": {},
                    "potions": {},
                    "buffs": {},
                    "bait_shop": self.DEFAULT_FISHING_ITEMS["bait_shop"].copy(),
                    "rod_shop": self.DEFAULT_FISHING_ITEMS["rod_shop"].copy()
                })
                self.server_shops = data.get("servers", {})
        except FileNotFoundError:
            self.shop_data = {
                "items": {},
                "potions": {},
                "buffs": {},
                "bait_shop": self.DEFAULT_FISHING_ITEMS["bait_shop"].copy(),
                "rod_shop": self.DEFAULT_FISHING_ITEMS["rod_shop"].copy()
            }
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

    @commands.group(name="shop_admin", aliases=["sa"], invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def shop_admin(self, ctx):
        """Shop management commands"""
        embed = discord.Embed(
            title="Shop Management",
            description=(
                "**Available Commands:**\n"
                "`.shop_admin add <shop> <item_data>` - Add item to shop\n"
                "`.shop_admin remove <shop> <item_id>` - Remove item\n"
                "`.shop_admin list <shop>` - List items\n"
                "`.shop_admin edit <shop> <item_id> <field> <value>` - Edit item\n\n"
                "**Available Shops:**\n" +
                "\n".join(f"{data['icon']} `{shop}` - {data['description']}" 
                         for shop, data in self.SHOP_TYPES.items())
            ),
            color=0x2b2d31
        )
        await ctx.reply(embed=embed)

    @shop_admin.command(name="add")
    @commands.has_permissions(administrator=True)
    async def shop_add(self, ctx, shop_type: str, *, item_data: str):
        """Add an item to a shop. Format varies by shop type.
        
        Examples:
        Items: .shop_admin add items {"id": "vip", "name": "VIP Role", "price": 10000, "description": "Get VIP status"}
        Potions: .shop_admin add potions {"id": "luck_potion", "name": "Lucky Potion", "price": 1000, "type": "luck", "multiplier": 2.0, "duration": 60}
        Upgrades: .shop_admin add upgrades {"id": "bank_boost", "name": "Bank Boost", "price": 5000, "type": "bank", "amount": 10000}
        Fishing: .shop_admin add fishing {"id": "pro_rod", "name": "Pro Rod", "price": 5000, "type": "rod", "multiplier": 1.5}"""
        
        if shop_type not in self.SHOP_TYPES:
            return await ctx.reply(f"Invalid shop type! Use one of: {', '.join(self.SHOP_TYPES.keys())}")
            
        try:
            # Parse item data
            item = json.loads(item_data)
            
            # Validate required fields
            required_fields = {
                "items": ["id", "name", "price", "description"],
                "potions": ["id", "name", "price", "type", "multiplier", "duration"],
                "upgrades": ["id", "name", "price", "type"],
                "fishing": ["id", "name", "price", "type"]
            }
            
            if not all(field in item for field in required_fields[shop_type]):
                return await ctx.reply(f"Missing required fields: {required_fields[shop_type]}")
                
            # Add the item to database
            if await db.add_shop_item(item, shop_type, ctx.guild.id if ctx.guild else None):
                embed = discord.Embed(
                    description=f"✨ Added **{item['name']}** to {self.SHOP_TYPES[shop_type]['icon']} {shop_type} shop!",
                    color=0x2b2d31
                )
                await ctx.reply(embed=embed)
            else:
                await ctx.reply("❌ Failed to add item to shop")
                
        except json.JSONDecodeError:
            await ctx.reply("❌ Invalid JSON format! Make sure to use proper JSON syntax.")
        except Exception as e:
            await ctx.reply(f"❌ Error: {str(e)}")
            
    @shop_admin.command(name="remove")
    @commands.has_permissions(administrator=True)
    async def shop_remove(self, ctx, shop_type: str, item_id: str):
        """Remove an item from a shop"""
        if shop_type not in self.SHOP_TYPES:
            return await ctx.reply(f"Invalid shop type! Use one of: {', '.join(self.SHOP_TYPES.keys())}")
            
        collection = getattr(self.db.db, f"shop_{shop_type}", None)
        if not collection:
            return await ctx.reply("❌ Invalid shop collection!")
            
        result = await collection.delete_one({
            "id": item_id,
            "guild_id": str(ctx.guild.id) if ctx.guild else None
        })
        
        if result.deleted_count > 0:
            embed = discord.Embed(
                description=f"✨ Removed item `{item_id}` from {self.SHOP_TYPES[shop_type]['icon']} {shop_type} shop!",
                color=0x2b2d31
            )
            await ctx.reply(embed=embed)
        else:
            await ctx.reply("❌ Item not found in shop")
            
    @shop_admin.command(name="list")
    @commands.has_permissions(administrator=True)
    async def shop_list(self, ctx, shop_type: str):
        """List all items in a shop"""
        if shop_type not in self.SHOP_TYPES:
            return await ctx.reply(f"Invalid shop type! Use one of: {', '.join(self.SHOP_TYPES.keys())}")
            
        items = await db.get_shop_items(shop_type, ctx.guild.id if ctx.guild else None)
        
        if not items:
            return await ctx.reply(f"No items found in {shop_type} shop!")
            
        pages = []
        chunks = [items[i:i+5] for i in range(0, len(items), 5)]
        
        for chunk in chunks:
            embed = discord.Embed(
                title=f"{self.SHOP_TYPES[shop_type]['icon']} {self.SHOP_TYPES[shop_type]['name']}",
                color=0x2b2d31
            )
            
            for item in chunk:
                name = f"{item['name']} ({item['price']} {self.currency})"
                value = []
                
                value.append(f"ID: `{item['id']}`")
                if "description" in item:
                    value.append(item["description"])
                if "type" in item:
                    value.append(f"Type: {item['type']}")
                if "multiplier" in item:
                    value.append(f"Multiplier: {item['multiplier']}x")
                if "duration" in item:
                    value.append(f"Duration: {item['duration']}min")
                if "amount" in item:
                    value.append(f"Amount: {item['amount']}")
                    
                embed.add_field(
                    name=name,
                    value="\n".join(value),
                    inline=False
                )
                
            pages.append(embed)
            
        if len(pages) > 1:
            view = HelpPaginator(pages, ctx.author)
            view.update_buttons()
            message = await ctx.reply(embed=pages[0], view=view)
            view.message = message
        else:
            await ctx.reply(embed=pages[0])
            
    @shop_admin.command(name="edit")
    @commands.has_permissions(administrator=True)
    async def shop_edit(self, ctx, shop_type: str, item_id: str, field: str, *, value: str):
        """Edit a field of an existing shop item
        
        Example: .shop_admin edit potions luck_potion price 2000"""
        if shop_type not in self.SHOP_TYPES:
            return await ctx.reply(f"Invalid shop type! Use one of: {', '.join(self.SHOP_TYPES.keys())}")
            
        collection = getattr(self.db.db, f"shop_{shop_type}", None)
        if not collection:
            return await ctx.reply("❌ Invalid shop collection!")
            
        # Convert value to appropriate type
        try:
            if field in ["price", "duration", "amount"]:
                value = int(value)
            elif field in ["multiplier"]:
                value = float(value)
            elif value.lower() == "null":
                value = None
                
            # Update the item
            result = await collection.update_one(
                {
                    "id": item_id,
                    "guild_id": str(ctx.guild.id) if ctx.guild else None
                },
                {"$set": {field: value}}
            )
            
            if result.modified_count > 0:
                embed = discord.Embed(
                    description=f"✨ Updated `{field}` to `{value}` for item `{item_id}`!",
                    color=0x2b2d31
                )
                await ctx.reply(embed=embed)
            else:
                await ctx.reply("❌ Item not found or no changes made")
                
        except ValueError:
            await ctx.reply("❌ Invalid value type for this field!")
        except Exception as e:
            await ctx.reply(f"❌ Error: {str(e)}")

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

    @commands.command()
    @commands.is_owner()
    async def reset_economy(self, ctx, *, confirmation: str = None):
        """Reset everyone's balance, inventory, and economic data (Bot Owner Only)
        Usage: .reset_economy YES I WANT TO RESET EVERYTHING"""
        
        if confirmation != "YES I WANT TO RESET EVERYTHING":
            embed = discord.Embed(
                title="⚠️ Economy Reset",
                description=(
                    "**WARNING:** This will delete ALL economic data including:\n"
                    "- User balances (wallet & bank)\n"
                    "- Inventories\n"
                    "- Fish collections\n"
                    "- Active potions\n"
                    "- Shop data\n\n"
                    "To confirm, use the command:\n"
                    "`.reset_economy YES I WANT TO RESET EVERYTHING`"
                ),
                color=discord.Color.red()
            )
            return await ctx.reply(embed=embed)
            
        try:
            # Reset user data
            await self.db.users.update_many(
                {},
                {
                    "$set": {
                        "wallet": 0,
                        "bank": 0,
                        "bank_limit": 10000,
                        "inventory": [],
                        "fish": [],
                        "fishing_rods": [],
                        "fishing_bait": []
                    }
                }
            )
            
            # Reset active effects
            await self.db.active_potions.delete_many({})
            
            # Reset shop data to defaults
            self.shop_data = {
                "items": {},
                "potions": {},
                "buffs": {},
                "bait_shop": self.DEFAULT_FISHING_ITEMS["bait_shop"].copy(),
                "rod_shop": self.DEFAULT_FISHING_ITEMS["rod_shop"].copy()
            }
            self.server_shops = {}
            self.save_shop_data()
            
            await ctx.reply("✅ Successfully reset all economic data!")
            
        except Exception as e:
            self.logger.error(f"Failed to reset economy: {e}")
            await ctx.reply("❌ An error occurred while resetting the economy")

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
