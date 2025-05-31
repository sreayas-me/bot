from discord.ext import commands
from cogs.logging.logger import CogLogger
from utils.db import async_db as db
from typing import Dict, List, Optional
from collections import Counter
import discord
import random
import asyncio
import hashlib
from datetime import datetime, timedelta
import math

class EconomyShopView(discord.ui.View):
    def __init__(self, pages, author, timeout=180):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.author = author
        self.current_page = 0
        self.message = None
        
        if len(self.pages) <= 1:
            self.clear_items()
            delete_btn = discord.ui.Button(
                label="🗑️ Close",
                style=discord.ButtonStyle.danger,
                custom_id="delete"
            )
            delete_btn.callback = self.delete_shop
            self.add_item(delete_btn)
        else:
            self.update_buttons()
    
    def update_buttons(self):
        self.clear_items()
        
        prev_btn = discord.ui.Button(
            label="◀ Previous",
            style=discord.ButtonStyle.secondary,
            disabled=self.current_page == 0
        )
        prev_btn.callback = self.previous_page
        self.add_item(prev_btn)
        
        page_info_btn = discord.ui.Button(
            label=f"Page {self.current_page + 1}/{len(self.pages)}",
            style=discord.ButtonStyle.primary,
            disabled=True
        )
        self.add_item(page_info_btn)
        
        next_btn = discord.ui.Button(
            label="Next ▶",
            style=discord.ButtonStyle.secondary,
            disabled=self.current_page == len(self.pages) - 1
        )
        next_btn.callback = self.next_page
        self.add_item(next_btn)
        
        delete_btn = discord.ui.Button(
            label="🗑️",
            style=discord.ButtonStyle.danger,
            custom_id="delete"
        )
        delete_btn.callback = self.delete_shop
        self.add_item(delete_btn)
        
        if len(self.pages) >= 3:
            options = []
            for i in range(len(self.pages)):
                options.append(discord.SelectOption(
                    label=f"Page {i + 1}",
                    value=str(i),
                    description=f"Go to page {i + 1} of the shop",
                    emoji="🛍️"
                ))
            
            page_select = discord.ui.Select(
                placeholder="🛍️ Jump to page...",
                options=options,
                row=1
            )
            page_select.callback = self.select_page
            self.add_item(page_select)
    
    async def previous_page(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            return await interaction.response.send_message("❌ This isn't your shop menu!", ephemeral=True)
        
        self.current_page = max(0, self.current_page - 1)
        self.update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)
    
    async def next_page(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            return await interaction.response.send_message("❌ This isn't your shop menu!", ephemeral=True)
        
        self.current_page = min(len(self.pages) - 1, self.current_page + 1)
        self.update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)
    
    async def select_page(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            return await interaction.response.send_message("❌ This isn't your shop menu!", ephemeral=True)
        
        self.current_page = int(interaction.data['values'][0])
        self.update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)
    
    async def delete_shop(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            return await interaction.response.send_message("❌ Only the command author can close this shop!", ephemeral=True)
        
        await interaction.response.defer()
        if self.message:
            try:
                await self.message.delete()
            except discord.NotFound:
                pass

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        
        if self.message:
            try:
                if self.pages and len(self.pages) > 0:
                    embed = self.pages[self.current_page].copy()
                    embed.set_footer(text="⏰ This shop menu has expired")
                    await self.message.edit(embed=embed, view=self)
                else:
                    await self.message.edit(view=self)
            except (discord.NotFound, discord.HTTPException):
                pass

class ShopStats:
    def __init__(self, shop_cog):
        self.shop = shop_cog
        
    async def get_popular_items(self, limit=5):
        """Get most purchased items from database"""
        try:
            pipeline = [
                {"$group": {"_id": "$item_id", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": limit}
            ]
            return await db.db.purchases.aggregate(pipeline).to_list(length=limit)
        except:
            return []
    
    def get_item_name(self, item_id):
        """Get item name from item ID"""
        all_items = {**self.shop.SHOP_ITEMS, **self.shop.FISHING_ITEMS, **self.shop.UPGRADE_ITEMS}
        return all_items.get(item_id, {}).get('name', item_id.replace('_', ' ').title())
    
    async def show_shop_stats(self, ctx):
        """Display shop statistics"""
        embed = discord.Embed(title="📊 Shop Statistics", color=0x9b59b6)
        
        # Most popular items
        popular = await self.get_popular_items()
        if popular:
            popular_text = []
            for i, item in enumerate(popular, 1):
                item_name = self.get_item_name(item['_id'])
                popular_text.append(f"{i}. {item_name} ({item['count']} purchases)")
            
            embed.add_field(
                name="🏆 Most Popular Items",
                value="\n".join(popular_text),
                inline=False
            )
        
        # Total transactions today
        try:
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_purchases = await db.db.purchases.count_documents({
                "timestamp": {"$gte": today_start}
            })
            
            embed.add_field(
                name="📈 Today's Activity",
                value=f"{today_purchases} purchases made today",
                inline=True
            )
        except:
            embed.add_field(
                name="📈 Today's Activity",
                value="Statistics unavailable",
                inline=True
            )
        
        await ctx.reply(embed=embed)

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = CogLogger(self.__class__.__name__)
        self.currency = "<:bronkbuk:1377389238290747582>"
        self.SHOP_ITEMS = {
            "vip": {
                "name": "VIP Role",
                "price": 10000,
                "description": "Get a special VIP role"
            },
            "color": {
                "name": "Custom Color",
                "price": 5000,
                "description": "Create a custom colored role"
            }
        }
        
        # Fishing shop items
        self.FISHING_ITEMS = {
            "beginner_rod": {
                "name": "Beginner Rod",
                "price": 0,
                "description": "Basic fishing rod for beginners",
                "type": "rod",
                "multiplier": 1.0,
                "id": "beginner_rod"
            },
            "beginner_bait": {
                "name": "Beginner Bait",
                "price": 0,
                "description": "Basic bait for catching fish (Pack of 10)",
                "type": "bait",
                "catch_rates": {"normal": 1.0, "rare": 0.1},
                "amount": 10,
                "id": "beginner_bait"
            },
            "pro_bait": {
                "name": "Pro Bait",
                "price": 50,
                "description": "Better chances for rare fish (Pack of 10)",
                "type": "bait",
                "catch_rates": {"normal": 1.2, "rare": 0.3, "event": 0.1},
                "amount": 10,
                "id": "pro_bait"
            },
            "advanced_rod": {
                "name": "Advanced Rod",
                "price": 500,
                "description": "Better fishing rod with 1.5x multiplier",
                "type": "rod",
                "multiplier": 1.5,
                "id": "advanced_rod"
            }
        }

        # Seasonal events
        self.SEASONAL_EVENTS = {
            "halloween": {
                "active_months": [10],  # October
                "items": {
                    "spooky_rod": {
                        "name": "🎃 Spooky Rod",
                        "price": 666,
                        "description": "A haunted fishing rod with ghostly powers",
                        "type": "rod",
                        "multiplier": 2.0,
                        "special_effect": "ghost_catch",
                        "limited": True
                    }
                }
            }
        }

        # Initialize shop stats
        self.stats = ShopStats(self)

    def get_current_seasonal_items(self):
        """Get items that are currently available due to seasonal events"""
        current_month = datetime.now().month
        seasonal_items = {}
        
        for event_name, event_data in self.SEASONAL_EVENTS.items():
            if current_month in event_data["active_months"]:
                seasonal_items.update(event_data["items"])
        
        return seasonal_items

    @commands.command(aliases=['shop'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def shop_menu(self, ctx, category: str = None):
        """View shop items by category"""
        if not category:
            await self._show_shop_menu(ctx)
            return
            
        if category.lower() == "fishing":
            await self._show_fishing_shop(ctx)
        elif category.lower() == "bait":
            await self._show_bait_shop(ctx)
        elif category.lower() in ["items", "general"]:
            await self._show_general_shop(ctx)
        else:
            await ctx.reply(f"❌ Unknown shop category: `{category}`\nAvailable: `fishing`, `bait`, `items`")

    async def _show_fishing_shop(self, ctx):
        """Show the fishing shop with rods and bait"""
        user_fishing_items = await db.get_fishing_items(ctx.author.id)
        user_balance = await db.get_wallet_balance(ctx.author.id, ctx.guild.id)
        
        embed = discord.Embed(
            title="🎣 Fishing Shop",
            description=f"Your Balance: **{user_balance}** {self.currency}\n\n",
            color=0x1e90ff
        )
        
        # Show rods
        rod_text = ""
        for rod_id, rod in self.FISHING_ITEMS.items():
            if rod["type"] != "rod":
                continue
                
            # Check if user already has this rod
            has_rod = any(r["id"] == rod_id for r in user_fishing_items.get("rods", []))
            
            if rod["price"] == 0 and has_rod:
                rod_text += f"~~**{rod['name']}**~~ - Already owned\n"
            else:
                price_text = "FREE" if rod["price"] == 0 else f"{rod['price']} {self.currency}"
                rod_text += f"**{rod['name']}** - {price_text}\n"
                rod_text += f"• {rod['description']}\n"
                rod_text += f"• Multiplier: {rod['multiplier']}x\n"
                rod_text += f"• `{ctx.prefix}buy {rod_id}`\n\n"
        
        embed.add_field(name="🎣 Fishing Rods", value=rod_text or "No rods available", inline=False)
        
        # Show bait
        bait_text = ""
        for bait_id, bait in self.FISHING_ITEMS.items():
            if bait["type"] != "bait":
                continue
                
            # For free bait, check if user has any bait at all
            if bait["price"] == 0:
                has_any_bait = len(user_fishing_items.get("bait", [])) > 0
                if has_any_bait:
                    bait_text += f"~~**{bait['name']}**~~ - You already have bait\n"
                    continue
            
            price_text = "FREE" if bait["price"] == 0 else f"{bait['price']} {self.currency}"
            bait_text += f"**{bait['name']}** - {price_text}\n"
            bait_text += f"• {bait['description']}\n"
            bait_text += f"• `{ctx.prefix}buy {bait_id}`\n\n"
        
        embed.add_field(name="🪱 Bait", value=bait_text or "No bait available", inline=False)
        
        embed.set_footer(text=f"Use {ctx.prefix}buy <item_id> to purchase items")
        await ctx.reply(embed=embed)

    async def _show_bait_shop(self, ctx):
        """Show only bait items"""
        user_fishing_items = await db.get_fishing_items(ctx.author.id)
        user_balance = await db.get_wallet_balance(ctx.author.id, ctx.guild.id)
        
        embed = discord.Embed(
            title="🪱 Bait Shop",
            description=f"Your Balance: **{user_balance}** {self.currency}\n\n",
            color=0x8b4513
        )
        
        bait_text = ""
        for bait_id, bait in self.FISHING_ITEMS.items():
            if bait["type"] != "bait":
                continue
                
            # For free bait, check if user has any bait at all
            if bait["price"] == 0:
                has_any_bait = len(user_fishing_items.get("bait", [])) > 0
                if has_any_bait:
                    bait_text += f"~~**{bait['name']}**~~ - You already have bait\n\n"
                    continue
            
            price_text = "FREE" if bait["price"] == 0 else f"{bait['price']} {self.currency}"
            bait_text += f"**{bait['name']}** - {price_text}\n"
            bait_text += f"• {bait['description']}\n"
            bait_text += f"• Amount: {bait.get('amount', 1)} pieces\n"
            
            # Show catch rates
            catch_rates = bait.get('catch_rates', {})
            if catch_rates:
                bait_text += f"• Catch rates: "
                rates = []
                for fish_type, rate in catch_rates.items():
                    rates.append(f"{fish_type.title()}: {rate}x")
                bait_text += ", ".join(rates) + "\n"
            
            bait_text += f"• `{ctx.prefix}buy {bait_id}`\n\n"
        
        embed.add_field(name="Available Bait", value=bait_text or "No bait available", inline=False)
        await ctx.reply(embed=embed)

    async def _show_general_shop(self, ctx):
        """Show general shop items"""
        user_balance = await db.get_wallet_balance(ctx.author.id, ctx.guild.id)
        
        embed = discord.Embed(
            title="🎁 General Shop",
            description=f"Your Balance: **{user_balance}** {self.currency}\n\n",
            color=0x00ff00
        )
        
        for item_id, item in self.SHOP_ITEMS.items():
            embed.add_field(
                name=f"{item['name']} - {item['price']} {self.currency}",
                value=f"{item['description']}\n`{ctx.prefix}buy {item_id}`",
                inline=False
            )
        
        await ctx.reply(embed=embed)

    @commands.command(aliases=['gshop'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def globalshop(self, ctx):
        """View available items in the global shop"""
        pages = []
        
        available_items = list(self.SHOP_ITEMS.items())
        flash_items = random.sample(available_items, min(3, len(available_items)))
        
        item_counts = {}
        for item_id, _ in flash_items:
            item_counts[item_id] = item_counts.get(item_id, 0) + 1
        
        discounted_items = {}
        for item_id, count in item_counts.items():
            if count > 1:
                discount = 0.45 if count == 3 else 0.20
                discounted_items[item_id] = discount

        overview = discord.Embed(
            description=f"🛍️ **Global Shop**\n\nYour Balance: **{await db.get_wallet_balance(ctx.author.id)}** $BB\n\n"
                    f"**🔥 Flash Sales**\n",
            color=discord.Color.blue()
        )
        
        for item_id, _ in flash_items:
            item = self.SHOP_ITEMS[item_id]
            if item_id in discounted_items:
                discount = discounted_items[item_id]
                discounted_price = int(item['price'] * (1 - discount))
                overview.description += f"**{item['name']}** - ~~{item['price']}~~ **{discounted_price}** {self.currency} "
                overview.description += f"(**{int(discount * 100)}% OFF!**)\n"
            else:
                overview.description += f"**{item['name']}** - {item['price']} {self.currency}\n"
        
        pages.append(overview)
        
        items = list(self.SHOP_ITEMS.items())
        for i in range(0, len(items), 4):
            page_items = items[i:i+4]
            content = []
            
            for item_id, item in page_items:
                if item_id in discounted_items:
                    discount = discounted_items[item_id]
                    discounted_price = int(item['price'] * (1 - discount))
                    content.append(f"**{item['name']}** - ~~{item['price']}~~ **{discounted_price}** {self.currency} "
                                f"(**{int(discount * 100)}% OFF!**)")
                else:
                    content.append(f"**{item['name']}** - {item['price']} {self.currency}")
                content.append(f"{item['description']}")
                content.append(f"`buy {item_id}` to purchase\n")
            
            pages.append(discord.Embed(
                description="\n".join(content),
                color=discord.Color.blue()
            ).set_footer(text=f"Balance: {await db.get_wallet_balance(ctx.author.id)} {self.currency}"))

        view = EconomyShopView(pages, ctx.author)
        message = await ctx.reply(embed=pages[0], view=view)
        view.message = message

    @commands.command()
    async def buy(self, ctx, *, args: str = None):
        """Buy items from the shop"""
        try:
            if not args:
                await self._show_shop_menu(ctx)
                return
                
            parsed_items = self._parse_buy_args(args)
            
            if not parsed_items:
                await ctx.reply(f"❌ Invalid format. Use `{ctx.prefix}buy <item_id> [amount]`")
                return
                
            if len(parsed_items) == 1 and parsed_items[0][0].lower() == "help":
                await self._show_buy_help(ctx)
                return
                
            await self._process_bulk_purchase(ctx, parsed_items)
            
        except Exception as e:
            self.logger.error(f"Buy command error: {e}")
            await ctx.reply("❌ Failed to complete purchase. Please try again later.")

    def _parse_buy_args(self, args: str) -> list:
        parts = args.split()
        items = []
        
        i = 0
        while i < len(parts):
            item_id = parts[i]
            amount = 1
            
            if i + 1 < len(parts) and parts[i + 1].isdigit():
                amount = int(parts[i + 1])
                i += 2
            else:
                i += 1
                
            items.append((item_id, amount))
            
        return items

    async def _show_shop_menu(self, ctx):
        embed = discord.Embed(
            title="🛍️ Shop Menu",
            description="Choose a category to browse items:",
            color=0x00ff00
        )
        
        categories = {
            "fishing": "🎣 Fishing Gear",
            "bait": "🪱 Bait Only", 
            "items": "🎁 General Items",
            "upgrades": "⬆️ Upgrades"
        }
        
        # Convert to list of tuples to maintain order
        category_list = list(categories.items())
        
        # Add fields in pairs
        for i in range(0, len(category_list), 2):
            # Get current pair of items
            items = category_list[i:i+2]
            
            # Add first item of pair
            embed.add_field(
                name=items[0][1],
                value=f"`{ctx.prefix}shop {items[0][0]}`",
                inline=True
            )
            
            # Add second item if exists, otherwise add empty field
            if len(items) > 1:
                embed.add_field(
                    name=items[1][1],
                    value=f"`{ctx.prefix}shop {items[1][0]}`",
                    inline=True
                )
            else:
                # Add empty field to maintain alignment if odd number
                embed.add_field(name="\u200b", value="\u200b", inline=True)
        
        # Quick Buy (always on new line)
        embed.add_field(
            name="💡 Quick Buy",
            value=f"`{ctx.prefix}buy <item_id> [amount]`\n`{ctx.prefix}buy help` for more options",
            inline=False
        )
        
        await ctx.reply(embed=embed)

    async def _show_buy_help(self, ctx):
        embed = discord.Embed(
            title="💡 Buy Command Help",
            color=0x3498db
        )
        
        examples = [
            (f"`{ctx.prefix}buy beginner_rod`", "Get your free starter rod"),
            (f"`{ctx.prefix}buy beginner_bait`", "Get your free starter bait"),
            (f"`{ctx.prefix}buy pro_bait 5`", "Buy 5 pro bait packs"),
            (f"`{ctx.prefix}buy vip`", "Buy VIP role"),
        ]
        
        for command, description in examples:
            embed.add_field(
                name=command,
                value=description,
                inline=False
            )
        
        embed.add_field(
            name="📝 Notes",
            value=f"• Use `{ctx.prefix}shop <category>` to see available items\n• Free items are only available once\n• Amounts default to 1 if not specified",
            inline=False
        )
        
        await ctx.reply(embed=embed)

    async def _process_bulk_purchase(self, ctx, items: list):
        user_id = ctx.author.id
        guild_id = ctx.guild.id
        
        purchase_plan = []
        total_cost = 0

        for item_id, amount in items:
            if amount <= 0:
                await ctx.reply(f"❌ Invalid amount for {item_id}. Amount must be positive.")
                return
                
            if amount > 100:
                await ctx.reply(f"❌ Amount too large for {item_id}. Maximum 100 per item.")
                return
                
            item = await self._find_item_in_shops(item_id, user_id)
            if not item:
                await ctx.reply(f"❌ Item `{item_id}` not found in any shop.")
                return
            
            # Check if item is no longer available (like free items already owned)
            if item.get("unavailable"):
                await ctx.reply(f"❌ {item['name']} is not available for purchase. {item.get('reason', '')}")
                return
                
            if not self._item_supports_multiple(item) and amount > 1:
                await ctx.reply(f"❌ `{item['name']}` can only be purchased once at a time.")
                return
                
            # Apply bulk discount if applicable
            base_price = item['price']
            if amount >= 10:
                discount = min(0.2, 0.05 * math.floor(amount / 5))  # 5% per 5 items, max 20%
                item_cost = int(base_price * amount * (1 - discount))
            else:
                item_cost = base_price * amount
                
            total_cost += item_cost
            purchase_plan.append((item, amount, item_cost))
        
        wallet_balance = await db.get_wallet_balance(user_id, guild_id)
        if wallet_balance < total_cost:
            await ctx.reply(f"❌ Insufficient funds. Need **{total_cost:,}** {self.currency}, you have **{wallet_balance:,}** {self.currency}.")
            return
        
        if total_cost > 10000 or len(purchase_plan) > 3:
            if not await self._confirm_purchase(ctx, purchase_plan, total_cost):
                return
        
        await self._execute_bulk_purchase(ctx, purchase_plan, total_cost)

    def _item_supports_multiple(self, item: dict) -> bool:
        single_purchase_types = ["role", "rod"]
        single_purchase_items = ["vip", "color_role", "beginner_rod", "advanced_rod"]
        
        if item.get("type") in single_purchase_types:
            return False
        if item.get("id") in single_purchase_items:
            return False
        if "upgrade" in item.get("id", "").lower():
            return False
            
        return True

    async def _find_item_in_shops(self, item_id: str, user_id: int = None) -> dict:
        # Check fishing items first
        if item_id in self.FISHING_ITEMS:
            item = self.FISHING_ITEMS[item_id].copy()
            
            # For free items, check if user already has them
            if item["price"] == 0 and user_id:
                user_fishing_items = await db.get_fishing_items(user_id)
                
                if item["type"] == "rod":
                    # Check if user already has this specific rod
                    has_rod = any(r["id"] == item_id for r in user_fishing_items.get("rods", []))
                    if has_rod:
                        item["unavailable"] = True
                        item["reason"] = "You already own this rod."
                        return item
                        
                elif item["type"] == "bait":
                    # For free bait, check if user has any bait at all
                    if item_id == "beginner_bait":
                        has_any_bait = len(user_fishing_items.get("bait", [])) > 0
                        if has_any_bait:
                            item["unavailable"] = True
                            item["reason"] = "You already have bait."
                            return item
            
            return item
            
        # Check general shop items
        if item_id in self.SHOP_ITEMS:
            return self.SHOP_ITEMS[item_id].copy()
            
        # Check seasonal items
        seasonal_items = self.get_current_seasonal_items()
        if item_id in seasonal_items:
            return seasonal_items[item_id].copy()
            
        # Check database shop items (for future expansion)
        shop_types = ["items", "fishing", "potions", "upgrades"]
        
        for shop_type in shop_types:
            try:
                collection = getattr(db.db, f"shop_{shop_type}", None)
                if collection:
                    item = await collection.find_one({"id": item_id})
                    if item:
                        item['_shop_type'] = shop_type
                        return item
            except:
                continue
                
        return None

    async def _confirm_purchase(self, ctx, purchase_plan: list, total_cost: int) -> bool:
        embed = discord.Embed(
            title="🛒 Confirm Purchase",
            color=0xffa500
        )
        
        items_text = []
        for item, amount, cost in purchase_plan:
            if cost == 0:
                items_text.append(f"**{amount}x** {item['name']} - FREE")
            else:
                items_text.append(f"**{amount}x** {item['name']} - {cost:,} {self.currency}")
        
        embed.add_field(
            name="Items to Purchase:",
            value="\n".join(items_text),
            inline=False
        )
        
        if total_cost == 0:
            embed.add_field(
                name="Total Cost:",
                value="**FREE**",
                inline=False
            )
        else:
            embed.add_field(
                name="Total Cost:",
                value=f"**{total_cost:,}** {self.currency}",
                inline=False
            )
        
        embed.set_footer(text="React with ✅ to confirm or ❌ to cancel (30s timeout)")
        
        message = await ctx.reply(embed=embed)
        await message.add_reaction("✅")
        await message.add_reaction("❌")
        
        def check(reaction, user):
            return (user == ctx.author and 
                    str(reaction.emoji) in ["✅", "❌"] and 
                    reaction.message.id == message.id)
        
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            return str(reaction.emoji) == "✅"
        except asyncio.TimeoutError:
            await message.edit(embed=discord.Embed(
                title="⏰ Purchase Cancelled",
                description="Purchase confirmation timed out.",
                color=0xff0000
            ))
            return False

    async def _execute_bulk_purchase(self, ctx, purchase_plan: list, total_cost: int):
        user_id = ctx.author.id
        guild_id = ctx.guild.id
        
        # Only deduct money if there's a cost
        if total_cost > 0:
            if not await db.update_wallet(user_id, -total_cost, guild_id):
                await ctx.reply("❌ Failed to deduct payment. Purchase cancelled.")
                return
            
        successful_purchases = []
        failed_purchases = []
        refund_amount = 0
        
        for item, amount, item_cost in purchase_plan:
            for i in range(amount):
                success = await self._purchase_single_item(user_id, item, guild_id)
                if success:
                    successful_purchases.append(item['name'])
                else:
                    failed_purchases.append(item['name'])
                    refund_amount += item['price']
        
        if refund_amount > 0:
            await db.update_wallet(user_id, refund_amount, guild_id)
        
        await self._send_purchase_results(ctx, successful_purchases, failed_purchases, total_cost - refund_amount)

    async def _purchase_single_item(self, user_id: int, item: dict, guild_id: int) -> bool:
        try:
            if item.get("type") == "rod":
                return await db.add_fishing_item(user_id, item, "rod")
            elif item.get("type") == "bait":
                return await db.add_fishing_item(user_id, item, "bait")
            elif item.get("type") == "potion":
                return await db.add_potion(user_id, item)
            elif item.get("type") == "bank":
                return await db.increase_bank_limit(user_id, item.get("amount", 0), guild_id)
            else:
                # General item - add to inventory
                result = await db.db.users.update_one(
                    {"_id": str(user_id)},
                    {"$push": {"inventory": item}},
                    upsert=True
                )
                return result.modified_count > 0 or result.upserted_id is not None
                
        except Exception as e:
            self.logger.error(f"Failed to purchase {item.get('name', 'unknown')}: {e}")
            return False

    async def _send_purchase_results(self, ctx, successful: list, failed: list, total_spent: int):
        embed = discord.Embed(
            title="🛍️ Purchase Complete",
            color=0x00ff00 if not failed else 0xffa500
        )
        
        if successful:
            from collections import Counter
            item_counts = Counter(successful)
            success_text = []
            for item_name, count in item_counts.items():
                if count > 1:
                    success_text.append(f"✅ **{count}x** {item_name}")
                else:
                    success_text.append(f"✅ {item_name}")
            
            embed.add_field(
                name="Successfully Purchased:",
                value="\n".join(success_text),
                inline=False
            )
        
        if failed:
            failed_counts = Counter(failed)
            failed_text = []
            for item_name, count in failed_counts.items():
                if count > 1:
                    failed_text.append(f"❌ **{count}x** {item_name}")
                else:
                    failed_text.append(f"❌ {item_name}")
            
            embed.add_field(
                name="Failed Purchases:",
                value="\n".join(failed_text),
                inline=False
            )
        
        if total_spent == 0:
            embed.add_field(
                name="💸 Total Spent:",
                value="**FREE**",
                inline=True
            )
        else:
            embed.add_field(
                name="💸 Total Spent:",
                value=f"**{total_spent:,}** {self.currency}",
                inline=True
            )
        
        new_balance = await db.get_wallet_balance(ctx.author.id, ctx.guild.id)
        embed.add_field(
            name="💰 Remaining Balance:",
            value=f"**{new_balance:,}** {self.currency}",
            inline=True
        )
        
        await ctx.reply(embed=embed)

    @commands.command(name="inventory", aliases=["inv"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def inventory(self, ctx):
        """View your inventory"""
        items = await db.get_inventory(ctx.author.id, ctx.guild.id)
        if not items:
            return await ctx.reply("Your inventory is empty!")
        
        pages = []
        chunks = [items[i:i+6] for i in range(0, len(items), 6)]
        
        for page_num, chunk in enumerate(chunks, 1):
            embed = discord.Embed(
                title=f"🎒 {ctx.author.name}'s Inventory",
                color=ctx.author.color or discord.Color.blue()
            )
            
            for item in chunk:
                quantity = item.get('quantity', 1)
                name = item.get('name', 'Unknown Item')
                
                if quantity > 1:
                    name = f"**{quantity}x** {name}"
                
                if item.get("type") == "potion":
                    name = f"🧪 {name}"
                elif item.get("type") == "special":
                    name = f"⭐ {name}"
                elif item.get("type") == "consumable":
                    name = f"🍖 {name}"
                
                value = item.get("description", "No description")[:100]
                if len(item.get("description", "")) > 100:
                    value += "..."
                
                embed.add_field(name=name, value=value, inline=False)
            
            if len(chunks) > 1:
                embed.set_footer(text=f"Page {page_num}/{len(chunks)} • {len(items)} total items")
            else:
                embed.set_footer(text=f"{len(items)} items in inventory")
            pages.append(embed)
        
        view = EconomyShopView(pages, ctx.author)
        await ctx.reply(embed=pages[0], view=view)

    @commands.command(name="use")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def use_item(self, ctx, item_id: str):
        """Use an item from your inventory"""
        items = await db.get_inventory(ctx.author.id, ctx.guild.id)
        
        item = next((item for item in items if item.get("id") == item_id), None)
        if not item:
            return await ctx.reply("❌ Item not found in your inventory!")

        if item["type"] == "potion":
            if await db.add_potion(ctx.author.id, item):
                await db.remove_from_inventory(ctx.author.id, ctx.guild.id, item_id)
                embed = discord.Embed(
                    description=f"🧪 Used **{item['name']}**!\n" \
                              f"{item['multiplier']}x {item['buff_type']} buff active for {item['duration']} minutes",
                    color=discord.Color.green()
                )
                await ctx.reply(embed=embed)
            else:
                await ctx.reply("❌ Failed to use potion!")
                
        elif item["type"] == "consumable":
            await db.remove_from_inventory(ctx.author.id, ctx.guild.id, item_id)
            embed = discord.Embed(
                description=f"✨ Used **{item['name']}**!",
                color=discord.Color.green()
            )
            await ctx.reply(embed=embed)
            
        else:
            await ctx.reply("❌ This item cannot be used!")

    @commands.command(name="search", aliases=["find", "shopsearch"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def search_shop(self, ctx, *, query: str):
        """Search for items across all shop categories"""
        if len(query) < 2:
            return await ctx.reply("❌ Search query must be at least 2 characters long.")
        
        results = []
        
        # Search in all shop dictionaries
        all_items = {**self.SHOP_ITEMS, **self.FISHING_ITEMS, **self.UPGRADE_ITEMS}
        
        for item_id, item in all_items.items():
            if (query.lower() in item['name'].lower() or 
                query.lower() in item['description'].lower() or
                query.lower() in item_id.lower()):
                results.append((item_id, item))
        
        if not results:
            return await ctx.reply(f"❌ No items found matching '{query}'")
        
        embed = discord.Embed(
            title=f"🔍 Search Results for '{query}'",
            color=0x3498db
        )
        
        for item_id, item in results[:10]:  # Limit to 10 results
            price_text = "FREE" if item['price'] == 0 else f"{item['price']} {self.currency}"
            
            # Add category indicator
            category = "🎣" if item.get('type') in ['rod', 'bait'] else "⬆️" if item_id in self.UPGRADE_ITEMS else "🎁"
            
            embed.add_field(
                name=f"{category} {item['name']} - {price_text}",
                value=f"{item['description']}\n`{ctx.prefix}buy {item_id}`",
                inline=False
            )
        
        if len(results) > 10:
            embed.set_footer(text=f"Showing first 10 of {len(results)} results")
        
        await ctx.reply(embed=embed)

    @commands.command(name="daily-deals", aliases=["deals", "dailydeals"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def daily_deals(self, ctx):
        """Show today's special deals"""
        # Rotate deals based on date
        today = datetime.now().strftime("%Y-%m-%d")
        seed = int(hashlib.md5(today.encode()).hexdigest()[:8], 16)
        random.seed(seed)
        
        # Select random items for daily deals from all categories
        all_items = list(self.SHOP_ITEMS.items()) + list(self.FISHING_ITEMS.items()) + list(self.UPGRADE_ITEMS.items())
        # Filter out free items
        paid_items = [(k, v) for k, v in all_items if v['price'] > 0]
        
        if not paid_items:
            return await ctx.reply("❌ No items available for daily deals.")
        
        deal_items = random.sample(paid_items, min(3, len(paid_items)))
        
        embed = discord.Embed(
            title="🔥 Today's Daily Deals",
            description="Special discounts that reset at midnight!",
            color=0xff6b6b
        )
        
        user_balance = await db.get_wallet_balance(ctx.author.id, ctx.guild.id)
        embed.add_field(
            name="💰 Your Balance",
            value=f"**{user_balance:,}** {self.currency}",
            inline=False
        )
        
        for item_id, item in deal_items:
            discount = random.uniform(0.15, 0.4)  # 15-40% off
            discounted_price = int(item['price'] * (1 - discount))
            
            # Add category indicator
            category = "🎣" if item.get('type') in ['rod', 'bait'] else "⬆️" if item_id in self.UPGRADE_ITEMS else "🎁"
            
            can_afford = "✅" if user_balance >= discounted_price else "❌"
            
            embed.add_field(
                name=f"{category} {item['name']} {can_afford}",
                value=f"~~{item['price']:,}~~ **{discounted_price:,}** {self.currency}\n"
                      f"**{int(discount*100)}% OFF!**\n"
                      f"{item['description'][:50]}{'...' if len(item['description']) > 50 else ''}\n"
                      f"`{ctx.prefix}buy {item_id}`",
                inline=True
            )
        
        embed.set_footer(text=f"Deals reset daily at midnight • Use {ctx.prefix}buy <item_id> to purchase")
        await ctx.reply(embed=embed)

    @commands.command(name="wishlist", aliases=["wl"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def wishlist(self, ctx, action: str = None, *, item_id: str = None):
        """Manage your wishlist"""
        if not action:
            return await self.show_wishlist(ctx)
        
        action = action.lower()
        if action == "add" and item_id:
            await self.add_to_wishlist(ctx, item_id)
        elif action == "remove" and item_id:
            await self.remove_from_wishlist(ctx, item_id)
        elif action == "clear":
            await self.clear_wishlist(ctx)
        else:
            await ctx.reply(f"Usage: `{ctx.prefix}wishlist [add/remove/clear] [item_id]`\n"
                          f"Or just `{ctx.prefix}wishlist` to view your list")

    async def show_wishlist(self, ctx):
        """Show user's wishlist"""
        try:
            wishlist = await db.db.wishlists.find_one({"user_id": str(ctx.author.id)})
            if not wishlist or not wishlist.get('items'):
                return await ctx.reply("📝 Your wishlist is empty! Use `{ctx.prefix}wishlist add <item_id>` to add items.")
            
            embed = discord.Embed(
                title=f"📝 {ctx.author.name}'s Wishlist",
                color=0xf39c12
            )
            
            user_balance = await db.get_wallet_balance(ctx.author.id, ctx.guild.id)
            embed.add_field(
                name="💰 Your Balance",
                value=f"**{user_balance:,}** {self.currency}",
                inline=False
            )
            
            affordable_count = 0
            total_cost = 0
            
            for item in wishlist['items']:
                can_afford = user_balance >= item['price']
                if can_afford:
                    affordable_count += 1
                
                total_cost += item['price']
                
                status = "✅ Can afford" if can_afford else "❌ Need more"
                price_text = "FREE" if item['price'] == 0 else f"{item['price']:,} {self.currency}"
                
                embed.add_field(
                    name=f"{item['name']} - {price_text}",
                    value=f"{status}\n`{ctx.prefix}buy {item['id']}`",
                    inline=True
                )
            
            embed.add_field(
                name="📊 Summary",
                value=f"Total items: **{len(wishlist['items'])}**\n"
                      f"Can afford: **{affordable_count}**\n"
                      f"Total cost: **{total_cost:,}** {self.currency}",
                inline=False
            )
            
            await ctx.reply(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Wishlist display error: {e}")
            await ctx.reply("❌ Failed to load wishlist. Please try again.")

    async def add_to_wishlist(self, ctx, item_id: str):
        """Add item to user's wishlist"""
        item = await self._find_item_in_shops(item_id, ctx.author.id)
        if not item:
            return await ctx.reply(f"❌ Item `{item_id}` not found in any shop.")
        
        if item.get("unavailable"):
            return await ctx.reply(f"❌ {item['name']} is not available for purchase. {item.get('reason', '')}")
        
        wishlist_item = {
            "id": item_id,
            "name": item["name"],
            "price": item["price"],
            "added_at": datetime.utcnow()
        }
        
        try:
            result = await db.db.wishlists.update_one(
                {"user_id": str(ctx.author.id)},
                {"$addToSet": {"items": wishlist_item}},
                upsert=True
            )
            
            if result.modified_count > 0 or result.upserted_id:
                await ctx.reply(f"✅ Added **{item['name']}** to your wishlist!")
            else:
                await ctx.reply(f"❌ **{item['name']}** is already in your wishlist!")
        except Exception as e:
            self.logger.error(f"Wishlist add error: {e}")
            await ctx.reply("❌ Failed to add item to wishlist. Please try again.")

    async def remove_from_wishlist(self, ctx, item_id: str):
        """Remove item from user's wishlist"""
        try:
            result = await db.db.wishlists.update_one(
                {"user_id": str(ctx.author.id)},
                {"$pull": {"items": {"id": item_id}}}
            )
            
            if result.modified_count > 0:
                await ctx.reply(f"✅ Removed item from your wishlist!")
            else:
                await ctx.reply("❌ Item not found in your wishlist.")
        except Exception as e:
            self.logger.error(f"Wishlist remove error: {e}")
            await ctx.reply("❌ Failed to remove item from wishlist. Please try again.")

    async def clear_wishlist(self, ctx):
        """Clear user's wishlist"""
        try:
            result = await db.db.wishlists.update_one(
                {"user_id": str(ctx.author.id)},
                {"$set": {"items": []}}
            )
            
            if result.modified_count > 0:
                await ctx.reply("✅ Cleared your wishlist!")
            else:
                await ctx.reply("❌ Your wishlist is already empty!")
        except Exception as e:
            self.logger.error(f"Wishlist clear error: {e}")
            await ctx.reply("❌ Failed to clear wishlist. Please try again.")

    @commands.command(name="shopstats", aliases=["shop-stats"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def shop_statistics(self, ctx):
        """View shop statistics and trends"""
        await self.stats.show_shop_stats(ctx)

async def setup(bot):
    await bot.add_cog(Shop(bot))