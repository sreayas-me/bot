from discord.ext import commands
from cogs.logging.logger import CogLogger
from utils.db import async_db as db
from typing import Dict, List
import discord
import random
import asyncio

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
            },
            "bank_upgrade": {
                "name": "Bank Upgrade",
                "price": 2500,
                "description": "Increase bank limit by 5000"
            }
        }

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
            "items": "🎁 General Items",
            "fishing": "🎣 Fishing Gear", 
            "potions": "🧪 Potions & Buffs",
            "upgrades": "⬆️ Upgrades"
        }
        
        for category, display_name in categories.items():
            try:
                items = await db.get_shop_items(category, ctx.guild.id)
                item_count = len(items)
                embed.add_field(
                    name=display_name,
                    value=f"`!shop {category}` ({item_count} items)",
                    inline=True
                )
            except:
                embed.add_field(
                    name=display_name,
                    value=f"`{ctx.prefix}shop {category}` (??? items)",
                    inline=True
                )
        
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
            (f"`{ctx.prefix}buy vip`", "Buy 1 VIP role"),
            (f"`{ctx.prefix}buy basic_bait 5`", "Buy 5 basic bait"),
            (f"`{ctx.prefix}buy vip 1 basic_bait 10`", "Buy 1 VIP role and 10 basic bait"),
            (f"`{ctx.prefix}buy bank_upgrade 3 fishing_luck 2`", "Buy 3 bank upgrades and 2 fishing luck potions")
        ]
        
        for command, description in examples:
            embed.add_field(
                name=command,
                value=description,
                inline=False
            )
        
        embed.add_field(
            name="📝 Notes",
            value=f"• Use `{ctx.prefix}shop <category>` to see available items\n• Amounts default to 1 if not specified",
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
                
            item = await self._find_item_in_shops(item_id)
            if not item:
                await ctx.reply(f"❌ Item `{item_id}` not found in any shop.")
                return
                
            if not self._item_supports_multiple(item) and amount > 1:
                await ctx.reply(f"❌ `{item['name']}` can only be purchased once at a time.")
                return
                
            item_cost = item['price'] * amount
            total_cost += item_cost
            purchase_plan.append((item, amount, item_cost))
        
        wallet_balance = await db.get_wallet_balance(user_id, guild_id)
        if wallet_balance < total_cost:
            await ctx.reply(f"❌ Insufficient funds. Need **{total_cost:,}** coins, you have **{wallet_balance:,}** coins.")
            return
        
        if total_cost > 10000 or len(purchase_plan) > 3:
            if not await self._confirm_purchase(ctx, purchase_plan, total_cost):
                return
        
        await self._execute_bulk_purchase(ctx, purchase_plan, total_cost)

    def _item_supports_multiple(self, item: dict) -> bool:
        single_purchase_types = ["role"]
        single_purchase_items = ["vip", "color_role"]
        
        if item.get("type") in single_purchase_types:
            return False
        if item.get("id") in single_purchase_items:
            return False
        if "upgrade" in item.get("id", "").lower():
            return False
            
        return True

    async def _find_item_in_shops(self, item_id: str) -> dict:
        beginner_items = {
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
                "description": "Basic bait for catching fish",
                "type": "bait",
                "catch_rates": {"normal": 1.0, "rare": 0.1},
                "amount": 10,
                "id": "beginner_bait"
            }
        }
        
        if item_id in beginner_items:
            return beginner_items[item_id]
            
        shop_types = ["items", "fishing", "potions", "upgrades"]
        
        for shop_type in shop_types:
            collection = getattr(db.db, f"shop_{shop_type}", None)
            if collection:
                item = await collection.find_one({"id": item_id})
                if item:
                    item['_shop_type'] = shop_type
                    return item
        return None

    async def _confirm_purchase(self, ctx, purchase_plan: list, total_cost: int) -> bool:
        embed = discord.Embed(
            title="🛒 Confirm Purchase",
            color=0xffa500
        )
        
        items_text = []
        for item, amount, cost in purchase_plan:
            items_text.append(f"**{amount}x** {item['name']} - {cost:,} coins")
        
        embed.add_field(
            name="Items to Purchase:",
            value="\n".join(items_text),
            inline=False
        )
        
        embed.add_field(
            name="Total Cost:",
            value=f"**{total_cost:,}** coins",
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
            shop_type = item.get('_shop_type', 'items')
            
            if shop_type == "fishing":
                if item.get("type") == "rod":
                    return await db.add_fishing_item(user_id, item, "rod")
                elif item.get("type") == "bait":
                    return await db.add_fishing_item(user_id, item, "bait")
                    
            elif shop_type == "potions":
                return await db.add_potion(user_id, item)
                
            elif shop_type == "upgrades":
                if item.get("type") == "bank":
                    return await db.increase_bank_limit(user_id, item.get("amount", 0), guild_id)
                    
            elif shop_type == "items":
                result = await db.db.users.update_one(
                    {"_id": str(user_id)},
                    {"$push": {"inventory": item}},
                    upsert=True
                )
                return result.modified_count > 0 or result.upserted_id is not None
                
            return False
            
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
            from collections import Counter
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
        
        embed.add_field(
            name="💸 Total Spent:",
            value=f"**{total_spent:,}** coins",
            inline=True
        )
        
        new_balance = await db.get_wallet_balance(ctx.author.id, ctx.guild.id)
        embed.add_field(
            name="💰 Remaining Balance:",
            value=f"**{new_balance:,}** coins",
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

async def setup(bot):
    await bot.add_cog(Shop(bot))