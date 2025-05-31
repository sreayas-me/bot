from discord.ext import commands
from cogs.logging.logger import CogLogger
from utils.db import async_db as db
from cogs.Help import HelpPaginator
from typing import Dict, List
from utils.betting import parse_bet
import discord
import random
import uuid
import datetime
import asyncio

def format_cooldown(seconds: float) -> str:
    """Format seconds into human readable time"""
    minutes, remaining_seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if remaining_seconds > 0:
        parts.append(f"{remaining_seconds}s")
    
    return " ".join(parts)

class EconomyShopView(discord.ui.View):
    def __init__(self, pages, author, timeout=180):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.author = author
        self.current_page = 0
        self.message = None
        
        # Only show navigation if we have multiple pages
        if len(self.pages) <= 1:
            self.clear_items()
            # Add only delete button for single page
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
        """Update button states based on current page"""
        # Clear existing items
        self.clear_items()
        
        # Previous button
        prev_btn = discord.ui.Button(
            label="◀ Previous",
            style=discord.ButtonStyle.secondary,
            disabled=self.current_page == 0
        )
        prev_btn.callback = self.previous_page
        self.add_item(prev_btn)
        
        # Page info button (disabled, just for display)
        page_info_btn = discord.ui.Button(
            label=f"Page {self.current_page + 1}/{len(self.pages)}",
            style=discord.ButtonStyle.primary,
            disabled=True
        )
        self.add_item(page_info_btn)
        
        # Next button
        next_btn = discord.ui.Button(
            label="Next ▶",
            style=discord.ButtonStyle.secondary,
            disabled=self.current_page == len(self.pages) - 1
        )
        next_btn.callback = self.next_page
        self.add_item(next_btn)
        
        # Delete button (always present)
        delete_btn = discord.ui.Button(
            label="🗑️",
            style=discord.ButtonStyle.danger,
            custom_id="delete"
        )
        delete_btn.callback = self.delete_shop
        self.add_item(delete_btn)
        
        # Add page selector if we have many pages (3+)
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
        """Go to previous page"""
        if interaction.user != self.author:
            return await interaction.response.send_message(
                "❌ This isn't your shop menu!", 
                ephemeral=True
            )
        
        self.current_page = max(0, self.current_page - 1)
        self.update_buttons()
        await interaction.response.edit_message(
            embed=self.pages[self.current_page], 
            view=self
        )
    
    async def next_page(self, interaction: discord.Interaction):
        """Go to next page"""
        if interaction.user != self.author:
            return await interaction.response.send_message(
                "❌ This isn't your shop menu!", 
                ephemeral=True
            )
        
        self.current_page = min(len(self.pages) - 1, self.current_page + 1)
        self.update_buttons()
        await interaction.response.edit_message(
            embed=self.pages[self.current_page], 
            view=self
        )
    
    async def select_page(self, interaction: discord.Interaction):
        """Jump to selected page"""
        if interaction.user != self.author:
            return await interaction.response.send_message(
                "❌ This isn't your shop menu!", 
                ephemeral=True
            )
        
        self.current_page = int(interaction.data['values'][0])
        self.update_buttons()
        await interaction.response.edit_message(
            embed=self.pages[self.current_page], 
            view=self
        )
    
    async def delete_shop(self, interaction: discord.Interaction):
        """Delete the shop message"""
        if interaction.user != self.author:
            return await interaction.response.send_message(
                "❌ Only the command author can close this shop!", 
                ephemeral=True
            )
        
        await interaction.response.defer()
        if self.message:
            try:
                await self.message.delete()
            except discord.NotFound:
                pass  # Message was already deleted
    
    async def on_timeout(self):
        """Disable all buttons when the view times out"""
        for item in self.children:
            item.disabled = True
        
        if self.message:
            try:
                # Add timeout message to embed
                if self.pages and len(self.pages) > 0:
                    embed = self.pages[self.current_page].copy()
                    embed.set_footer(text="⏰ This shop menu has expired")
                    await self.message.edit(embed=embed, view=self)
                else:
                    await self.message.edit(view=self)
            except (discord.NotFound, discord.HTTPException):
                pass  # Message was deleted or couldn't be edited

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = CogLogger(self.__class__.__name__)
        self.currency = "<:bronkbuk:1377389238290747582>"
        self.active_games = set()
        self.db = db  
        self.active_jackpots: Dict[int, Dict[int, int]] = {}  # {channel_id: {bet_amount: message_id}}
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
                }
            }
        }

        # Slot machine configuration
        self.SLOT_EMOJIS = ["🍒", "🍋", "🍊", "🍇", "7️⃣", "💎"]
        self.SLOT_VALUES = {"🍒": 1.5, "🍋": 2, "🍊": 3, "🍇": 4, "7️⃣": 7, "💎": 10}
        self.SLOT_WEIGHTS = [45, 30, 15, 7, 2, 1]  # Much harder to win now

        # Card values for blackjack
        self.CARD_VALUES = {
            "A": 11, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7,
            "8": 8, "9": 9, "10": 10, "J": 10, "Q": 10, "K": 10
        }
        self.CARD_SUITS = ["♠", "♥", "♦", "♣"]

        # Add shop items
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

        # Initialize fishing buffs
        self.fishing_cooldowns = {}
        
    async def get_shop_items(self, type:str, guild_id: int = None) -> dict:
        """Get shop items from database (Economy cog method)"""
        try:
            # Use the legacy method from database to avoid conflicts
            return await db.get_shop_items(type, guild_id)
        except Exception as e:
            self.logger.error(f"Failed to get shop items: {e}")
            return {}

    async def cog_before_invoke(self, ctx):
        """Check if user has an active game"""
        if ctx.command.name in ['slots', 'slotbattle', 'rollfight', 'rps', 'blackjack']:
            if ctx.author.id in self.active_games:
                raise commands.CommandError("You already have an active game!")
            self.active_games.add(ctx.author.id)

    async def cog_after_invoke(self, ctx):
        """Remove user from active games"""
        if hasattr(self, 'active_games'):
            self.active_games.discard(ctx.author.id)

    @commands.command(name="deposit", aliases=["dep", 'd'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def deposit(self, ctx, amount: str = None):
        """Deposit money into your bank"""
        try:
            if not amount:
                wallet = await db.get_wallet_balance(ctx.author.id, ctx.guild.id)
                bank = await db.get_bank_balance(ctx.author.id, ctx.guild.id)
                limit = await db.get_bank_limit(ctx.author.id, ctx.guild.id)
                space = limit - bank
                
                embed = discord.Embed(
                    description=(
                        "**BronkBuks Bank Deposit Guide**\n\n"
                        f"Your Wallet: **{wallet:,}** {self.currency}\n"
                        f"Bank Space: **{space:,}** {self.currency}\n\n"
                        "**Usage:**\n"
                        "`.deposit <amount>`\n"
                        "`.deposit 50%` - Deposit 50% of wallet\n"
                        "`.deposit all` - Deposit maximum amount\n"
                        "`.deposit 1k` - Deposit 1,000\n"
                        "`.deposit 1.5m` - Deposit 1,500,000"
                    ),
                    color=0x2b2d31
                )
                return await ctx.reply(embed=embed)

            wallet = await db.get_wallet_balance(ctx.author.id, ctx.guild.id)
            bank = await db.get_bank_balance(ctx.author.id, ctx.guild.id)
            limit = await db.get_bank_limit(ctx.author.id, ctx.guild.id)
            space = limit - bank

            # Parse amount with k/m suffix support
            if amount.lower() in ['all', 'max']:
                amount = min(wallet, space)
            elif amount.endswith('%'):
                try:
                    percentage = float(amount[:-1])
                    if not 0 < percentage <= 100:
                        return await ctx.reply("Percentage must be between 0 and 100!")
                    amount = min(int((percentage / 100) * wallet), space)
                except ValueError:
                    return await ctx.reply("Invalid percentage!")
            else:
                try:
                    if amount.lower().endswith('k'):
                        amount = int(float(amount[:-1]) * 1000)
                    elif amount.lower().endswith('m'):
                        amount = int(float(amount[:-1]) * 1000000)
                    else:
                        amount = int(amount)
                except ValueError:
                    return await ctx.reply("Invalid amount!")

            if amount <= 0:
                return await ctx.reply("Amount must be positive!")
            if amount > wallet:
                return await ctx.reply("You don't have that much in your wallet!")
            if amount > space:
                return await ctx.reply(f"Your bank can only hold {space:,} more coins!")

            # FIXED: Update wallet and bank separately instead of using transfer_money
            if await db.update_wallet(ctx.author.id, -amount, ctx.guild.id):
                if await db.update_bank(ctx.author.id, amount, ctx.guild.id):
                    await ctx.reply(f"💰 Deposited **{amount:,}** {self.currency} into your bank!")
                else:
                    # Revert wallet change if bank update fails
                    await db.update_wallet(ctx.author.id, amount, ctx.guild.id)
                    await ctx.reply("❌ Failed to deposit money! Transaction reverted.")
            else:
                await ctx.reply("❌ Failed to deposit money!")
                
        except Exception as e:
            self.logger.error(f"Deposit error: {e}")
            await ctx.reply("An error occurred while processing your deposit.")

    @commands.command(name="withdraw", aliases=["with", 'w'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def withdraw(self, ctx, amount: str = None):
        """Withdraw money from your bank"""
        try:
            if not amount:
                wallet = await db.get_wallet_balance(ctx.author.id, ctx.guild.id)
                bank = await db.get_bank_balance(ctx.author.id, ctx.guild.id)
                
                embed = discord.Embed(
                    description=(
                        "**BronkBuks Bank Withdrawal Guide**\n\n"
                        f"Your Bank: **{bank:,}** {self.currency}\n"
                        f"Your Wallet: **{wallet:,}** {self.currency}\n\n"
                        "**Usage:**\n"
                        "`.withdraw <amount>`\n"
                        "`.withdraw 50%` - Withdraw 50% of bank\n"
                        "`.withdraw all` - Withdraw everything\n"
                        "`.withdraw 1k` - Withdraw 1,000\n"
                        "`.withdraw 1.5m` - Withdraw 1,500,000"
                    ),
                    color=0x2b2d31
                )
                return await ctx.reply(embed=embed)

            bank = await db.get_bank_balance(ctx.author.id, ctx.guild.id)

            # Parse amount with k/m suffix support
            if amount.lower() in ['all', 'max']:
                amount = bank
            elif amount.endswith('%'):
                try:
                    percentage = float(amount[:-1])
                    if not 0 < percentage <= 100:
                        return await ctx.reply("Percentage must be between 0 and 100!")
                    amount = int((percentage / 100) * bank)
                except ValueError:
                    return await ctx.reply("Invalid percentage!")
            else:
                try:
                    if amount.lower().endswith('k'):
                        amount = int(float(amount[:-1]) * 1000)
                    elif amount.lower().endswith('m'):
                        amount = int(float(amount[:-1]) * 1000000)
                    else:
                        amount = int(amount)
                except ValueError:
                    return await ctx.reply("Invalid amount!")

            if amount <= 0:
                return await ctx.reply("Amount must be positive!")
            if amount > bank:
                return await ctx.reply("You don't have that much in your bank!")

            # FIXED: Better transaction handling with proper rollback
            if await db.update_bank(ctx.author.id, -amount, ctx.guild.id):
                if await db.update_wallet(ctx.author.id, amount, ctx.guild.id):
                    await ctx.reply(f"💸 Withdrew **{amount:,}** {self.currency} from your bank!")
                else:
                    # Revert bank change if wallet update fails
                    await db.update_bank(ctx.author.id, amount, ctx.guild.id)
                    await ctx.reply("❌ Failed to withdraw money! Transaction reverted.")
            else:
                await ctx.reply("❌ Failed to withdraw money!")
        except Exception as e:
            self.logger.error(f"Withdraw error: {e}")
            await ctx.reply("An error occurred while processing your withdrawal.")

    @commands.command(aliases=['bal', 'cash', 'bb'])
    async def balance(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        wallet = await db.get_wallet_balance(member.id, ctx.guild.id)
        bank = await db.get_bank_balance(member.id, ctx.guild.id)
        bank_limit = await db.get_bank_limit(member.id, ctx.guild.id)
        
        embed = discord.Embed(
            title=f"{member.display_name}'s Balance",
            description=(
                f"💵 Wallet: **{wallet:,}** {self.currency}\n"
                f"🏦 Bank: **{bank:,}**/**{bank_limit:,}** {self.currency}\n"
                f"💰 Net Worth: **{wallet + bank:,}** {self.currency}"
            ),
            color=member.color
        )
        await ctx.reply(embed=embed)

    @commands.command(name="pay", aliases=["transfer", 'p'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def pay(self, ctx, member: discord.Member, amount: int):
        """Transfer money to another user"""
        if amount <= 0:
            return await ctx.reply("Amount must be positive!")
        
        if member == ctx.author:
            return await ctx.reply("You can't pay yourself!")
        
        if await db.transfer_money(ctx.author.id, member.id, amount, ctx.guild.id):
            await ctx.reply(f"Transferred **{amount}** {self.currency} to {member.mention}")
        else:
            await ctx.reply("Insufficient funds!")

    @commands.command(aliases=['slot', 'sl'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def slots(self, ctx, bet_amount: str = "10"):
        """Play the slot machine"""
        wallet = await db.get_wallet_balance(ctx.author.id, ctx.guild.id)
        bet, error = parse_bet(bet_amount, wallet)
        
        if error:
            return await ctx.reply(error)
        
        if bet < 10:
            return await ctx.reply("Minimum bet is 10!")
            
        if bet > wallet:
            return await ctx.reply("Insufficient funds!")
        
        # Deduct the bet amount before spinning
        if not await db.update_wallet(ctx.author.id, -bet, ctx.guild.id):
            return await ctx.reply("Failed to deduct bet from your balance!")
        
        # Spinning animation
        msg = await ctx.reply("🎰 `spinning...`")
        for _ in range(3):
            await asyncio.sleep(0.7)
            await msg.edit(content="🎰 `spinning...`")
        
        # Generate results
        results = random.choices(self.SLOT_EMOJIS, weights=self.SLOT_WEIGHTS, k=3)
        display = " | ".join(results)
        
        # Calculate winnings
        if len(set(results)) == 1:  # All match
            multiplier = self.SLOT_VALUES[results[0]]
            winnings = bet * multiplier
            result = f"JACKPOT! {multiplier}x multiplier!"
        elif len(set(results)) == 2:  # Two match
            most_common = max(set(results), key=results.count)
            multiplier = self.SLOT_VALUES[most_common] // 2
            winnings = bet * multiplier
            result = f"WINNER! {multiplier}x multiplier!"
            if multiplier > 1: # the multiplier was bad unfortunately i.e 2 cherries
                result = "Better Luck Next Time!"
        else:  # No matches
            winnings = 0
            result = "Better luck next time!"
        
        # Only add winnings if > 0
        if winnings > 0:
            await db.update_balance(ctx.author.id, winnings, ctx.guild.id)
        
        embed = discord.Embed(
            description=f"🎰 `{display}`\n\n{result}\n\n**Bet:** {bet}\n**Won:** {winnings}",
            color=discord.Color.green() if winnings > 0 else discord.Color.red()
        )
        await msg.edit(content=None, embed=embed)

    @commands.command()
    @commands.cooldown(1, 86400, commands.BucketType.user)
    async def daily(self, ctx):
        """Claim your daily reward"""
        amount = random.randint(100, 500)
        await db.update_wallet(ctx.author.id, amount, ctx.guild.id)
        await ctx.reply(f"Daily reward claimed! +**{amount}** {self.currency}")

    @commands.command()
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def beg(self, ctx):
        """get ur money up"""
        amount = random.randint(0, 150)
        await db.update_wallet(ctx.author.id, amount, ctx.guild.id)
        await ctx.reply(f"you got +**{amount}** {self.currency}")

    async def calculate_daily_interest(self, user_id: int, guild_id: int = None) -> float:
        """Calculate and apply daily interest"""
        wallet = await db.get_wallet_balance(user_id, guild_id)
        interest_level = await db.get_interest_level(user_id)
        
        # Base interest rate is 0.003% (0.00003)
        base_rate = 0.00003
        # Each level increases rate by 0.0005% (0.000005)
        level_bonus = interest_level * 0.000005
        total_rate = base_rate + level_bonus
        
        interest = wallet * total_rate
        if interest < 1:  # Minimum 1 coin
            interest = 1
        
        # Cap at 1% of wallet per day (optional)
        max_interest = wallet * 0.01
        if interest > max_interest:
            interest = max_interest
        
        if await db.update_wallet(user_id, int(interest), guild_id):
            return interest
        return 0

    @commands.command(aliases=['interest', 'i'])
    @commands.cooldown(1, 86400, commands.BucketType.user)
    async def claim_interest(self, ctx):
        """Claim your daily interest"""
        interest = await self.calculate_daily_interest(ctx.author.id, ctx.guild.id)
        if interest > 0:
            await ctx.reply(f"💰 You earned **{interest:,}** {self.currency} in daily interest!")
        else:
            await ctx.reply("❌ Failed to claim interest. Try again later.")

    @commands.command(aliases=['upgrade_interest', 'iu'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def interest_upgrade(self, ctx):
        """Upgrade your daily interest rate"""
        
        async def create_upgrade_embed(user_id):
            """Create the upgrade embed with current user data"""
            current_level = await db.get_interest_level(user_id)
            if current_level >= 30:
                embed = discord.Embed(
                    title="Interest Rate Upgrade",
                    description="You've reached the maximum interest level!",
                    color=discord.Color.gold()
                )
                return embed, None, True  # embed, view, max_reached
            
            # Calculate upgrade cost
            base_cost = 1000
            cost = base_cost * (current_level + 1)
            
            # For levels 20+, require an item
            item_required = current_level >= 20
            
            embed = discord.Embed(
                title="Interest Rate Upgrade",
                description=(
                    f"Current interest level: **{current_level}**\n"
                    f"Next level cost: **{cost:,}** {self.currency}\n"
                    f"Item required: {'Yes' if item_required else 'No'}\n\n"
                    f"Your current daily interest rate: **{0.003 + (current_level * 0.05):.3f}%**\n"
                    f"Next level rate: **{0.003 + ((current_level + 1) * 0.05):.3f}%**"
                ),
                color=discord.Color.green()
            )
            
            if item_required:
                embed.add_field(
                    name="Special Item Required",
                    value="You need an **Interest Token** to upgrade beyond level 20!",
                    inline=False
                )
            
            # Create view with buttons
            view = discord.ui.View()
            
            confirm_button = discord.ui.Button(label="Upgrade", style=discord.ButtonStyle.green)
            
            async def confirm_callback(interaction):
                if interaction.user != ctx.author:
                    return await interaction.response.send_message("This isn't your upgrade!", ephemeral=True)
                
                # Get fresh data for the upgrade attempt
                fresh_level = await db.get_interest_level(ctx.author.id)
                fresh_cost = base_cost * (fresh_level + 1)
                fresh_item_required = fresh_level >= 20
                
                success, message = await db.upgrade_interest(ctx.author.id, fresh_cost, fresh_item_required)
                
                if success:
                    # Create new embed with updated data
                    new_embed, new_view, max_reached = await create_upgrade_embed(ctx.author.id)
                    if max_reached:
                        await interaction.response.edit_message(embed=new_embed, view=None)
                    else:
                        await interaction.response.edit_message(embed=new_embed, view=new_view)
                else:
                    # Show error message briefly, then restore original embed
                    error_embed = discord.Embed(
                        description=f"❌ {message}",
                        color=discord.Color.red()
                    )
                    await interaction.response.edit_message(embed=error_embed, view=None)
                    
                    # Wait 3 seconds then restore the upgrade embed
                    await asyncio.sleep(3)
                    original_embed, original_view, _ = await create_upgrade_embed(ctx.author.id)
                    await interaction.edit_original_response(embed=original_embed, view=original_view)
            
            confirm_button.callback = confirm_callback
            view.add_item(confirm_button)
            
            cancel_button = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.red)
            
            async def cancel_callback(interaction):
                if interaction.user != ctx.author:
                    return await interaction.response.send_message("This isn't your upgrade!", ephemeral=True)
                await interaction.response.edit_message(content="Upgrade cancelled.", embed=None, view=None)
            
            cancel_button.callback = cancel_callback
            view.add_item(cancel_button)
            
            return embed, view, False
        
        # Create initial embed and view
        embed, view, max_reached = await create_upgrade_embed(ctx.author.id)
        
        if max_reached:
            await ctx.reply(embed=embed)
        else:
            await ctx.reply(embed=embed, view=view)
    @commands.command(aliases=['interest_info', 'ii'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def interest_status(self, ctx):
        """Check your current interest rate and level"""
        wallet = await db.get_wallet_balance(ctx.author.id, ctx.guild.id)
        level = await db.get_interest_level(ctx.author.id)
        current_rate = 0.003 + (level * 0.05)
        next_rate = 0.003 + ((level + 1) * 0.05) if level < 30 else current_rate
        
        # Calculate what they would earn today
        daily_interest = wallet * (current_rate / 100)
        if daily_interest < 1:
            daily_interest = 1
        
        embed = discord.Embed(
            title="Interest Account Status",
            description=(
                f"**Current Level:** {level}/30\n"
                f"**Daily Interest Rate:** {current_rate:.3f}%\n"
                f"**Estimated Daily Earnings:** {int(daily_interest):,} {self.currency}\n"
                f"**Next Level Rate:** {next_rate:.3f}%"
            ),
            color=discord.Color.blue()
        )
        
        if level < 30:
            base_cost = 1000
            cost = base_cost * (level + 1)
            embed.add_field(
                name="Next Upgrade",
                value=f"Cost: **{cost:,}** {self.currency}\n" + 
                    ("*Requires Interest Token*" if level >= 20 else ""),
                inline=False
            )
        
        await ctx.reply(embed=embed)

    @commands.command()
    @commands.cooldown(1, 3600, commands.BucketType.user)
    async def work(self, ctx):
        """Work for some money"""
        amount = random.randint(50, 200)
        await db.update_wallet(ctx.author.id, amount, ctx.guild.id)
        await ctx.reply(f"You worked and earned **{amount}** {self.currency}")

    @commands.command()
    @commands.cooldown(1, 300, commands.BucketType.user)
    async def rob(self, ctx, victim: discord.Member):
        """Attempt to rob someone"""
        if victim == ctx.author:
            return await ctx.reply("You can't rob yourself!")
        
        victim_bal = await db.get_wallet_balance(victim.id, ctx.guild.id)
        if victim_bal < 100:
            return await ctx.reply("They're too poor to rob!")
        
        chance = random.random()
        if chance < 0.6:  # 60% chance to fail
            fine = random.randint(50, 200)
            await db.update_wallet(ctx.author.id, -fine, ctx.guild.id)
            return await ctx.reply(f"You got caught and paid **{fine}** {self.currency} in fines!")
        
        stolen = random.randint(50, min(victim_bal, 500))
        await db.update_wallet(victim.id, -stolen, ctx.guild.id)
        await db.update_wallet(ctx.author.id, stolen, ctx.guild.id)
        await ctx.reply(f"You stole **{stolen}** {self.currency} from {victim.mention}!")

    @commands.command(aliases=['lb'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def leaderboard(self, ctx, scope: str = "server"):
        """View the richest users in the current server or globally"""
        
        # Check if user wants global leaderboard
        if scope.lower() in ["global", "g", "world", "all"]:
            return await self._show_global_leaderboard(ctx)
        else:
            return await self._show_server_leaderboard(ctx)

    async def _show_server_leaderboard(self, ctx):
        """Show server-specific leaderboard (optimized version)"""
        try:
            if not await self.db.ensure_connected():
                return await ctx.reply(embed=discord.Embed(
                    description="❌ Database connection failed", 
                    color=0xff0000
                ))

            # Get all non-bot member IDs in the server
            member_ids = [str(member.id) for member in ctx.guild.members if not member.bot]
            
            if not member_ids:
                return await ctx.reply(embed=discord.Embed(
                    description="No users found in this server",
                    color=0x2b2d31
                ))

            # Single database query to get all relevant users
            cursor = self.db.db.users.find({
                "_id": {"$in": member_ids},
                "$or": [
                    {"wallet": {"$gt": 0}},
                    {"bank": {"$gt": 0}}
                ]
            })

            users = []
            async for user_doc in cursor:
                member = ctx.guild.get_member(int(user_doc["_id"]))
                if member:  # Only include members still in the server
                    total = user_doc.get("wallet", 0) + user_doc.get("bank", 0)
                    users.append({
                        "member": member,
                        "total": round(total)
                    })

            if not users:
                embed = discord.Embed(
                    description="No economy data for this server.\n💡 Users need to earn money first (work, daily, etc.)", 
                    color=0x2b2d31
                )
                return await ctx.reply(embed=embed)
            
            # Sort and get top 10
            users.sort(key=lambda x: x["total"], reverse=True)
            users = users[:10]
            
            content = []
            total_wealth = 0
            position_emojis = {1: "🥇", 2: "🥈", 3: "🥉"}
            
            for i, user in enumerate(users, 1):
                total = user["total"]
                formatted_amount = "{:,}".format(total)
                position = position_emojis.get(i, f"`{i}.`")
                content.append(f"{position} {user['member'].display_name} • **{formatted_amount}** {self.currency}")
                total_wealth += total
            
            embed = discord.Embed(
                title=f"💰 Richest Users in {ctx.guild.name}",
                description="\n".join(content),
                color=0x2b2d31
            )
            
            formatted_total = "{:,}".format(total_wealth)
            average_wealth = "{:,}".format(total_wealth // len(content)) if content else "0"
            embed.set_footer(text=f"Total Wealth: ${formatted_total} $BB • Average: ${average_wealth} $BB\n💡 Use `.leaderboard global` for global rankings")
            
            await ctx.reply(embed=embed)
            
        except Exception as e:
            print(f"Leaderboard error: {e}")
            return await ctx.reply(embed=discord.Embed(
                description="❌ An error occurred while fetching the leaderboard", 
                color=0xff0000
            ))

    async def _show_global_leaderboard(self, ctx):
        """Show global leaderboard across all servers"""
        try:
            if not await db.ensure_connected():
                return await ctx.reply(embed=discord.Embed(
                    description="❌ Database connection failed", 
                    color=0xff0000
                ))
            
            # MongoDB aggregation pipeline to get top users globally
            pipeline = [
                {
                    "$group": {
                        "_id": "$_id",  # User ID is stored as _id in your schema
                        "total": {"$sum": {"$add": ["$wallet", "$bank"]}}
                    }
                },
                {"$sort": {"total": -1}},
                {"$limit": 10}
            ]
            
            # Use the db instance properly
            users = await db.db.users.aggregate(pipeline).to_list(10)
            
            if not users:
                return await ctx.reply(embed=discord.Embed(
                    description="No global economy data found", 
                    color=0x2b2d31
                ))
            
            content = []
            total_wealth = 0
            position_emojis = {1: "🥇", 2: "🥈", 3: "🥉"}
            
            for i, user in enumerate(users, 1):
                user_id = int(user['_id'])  # _id is the user ID in your schema
                total = user['total']
                total_wealth += total
                
                # Try to get member from current guild first
                member = ctx.guild.get_member(user_id)
                if not member:
                    # Try to find user in any mutual guild
                    member = self.bot.get_user(user_id)
                
                if member:
                    position = position_emojis.get(i, f"`{i}.`")
                    formatted_amount = "{:,}".format(total)
                    display_name = getattr(member, 'display_name', member.name)
                    content.append(f"{position} {display_name} • **{formatted_amount}** {self.currency}")
            
            if not content:
                return await ctx.reply(embed=discord.Embed(
                    description="No active users found", 
                    color=0x2b2d31
                ))
            
            embed = discord.Embed(
                title="🌎 Global Economy Leaderboard",
                description="\n".join(content),
                color=0x2b2d31
            )
            
            formatted_total = "{:,}".format(total_wealth)
            average_wealth = "{:,}".format(total_wealth // len(content)) if content else "0"
            embed.set_footer(text=f"Total Wealth: ${formatted_total} • Average: ${average_wealth}")
            
            await ctx.reply(embed=embed)
            
        except Exception as e:
            print(f"DEBUG: Global leaderboard error: {e}")
            return await ctx.reply(embed=discord.Embed(
                description="❌ An error occurred while fetching the global leaderboard", 
                color=0xff0000
            ))

    # Keep the old globalboard command as an alias for backward compatibility
    @commands.command(aliases=['gboard', 'globalb', 'gtop', 'globaltop', 'glb'])
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def globalboard(self, ctx):
        """View global leaderboard across all servers (alias for .leaderboard global)"""
        await self._show_global_leaderboard(ctx)
        
    @commands.command(aliases=['gshop'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def globalshop(self, ctx):
        """View available items in the global shop"""
        pages = []
        
        # Get 3 random items for flash sale
        available_items = list(self.SHOP_ITEMS.items())
        flash_items = random.sample(available_items, min(3, len(available_items)))
        
        # Count duplicates and calculate discount
        item_counts = {}
        for item_id, _ in flash_items:
            item_counts[item_id] = item_counts.get(item_id, 0) + 1
        
        # Calculate discounts based on duplicates
        discounted_items = {}
        for item_id, count in item_counts.items():
            if count > 1:
                discount = 0.45 if count == 3 else 0.20
                discounted_items[item_id] = discount
        
        # Overview page with flash sales
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
        
        # Regular shop pages
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

        view = HelpPaginator(pages, ctx.author)
        view.update_buttons()
        message = await ctx.reply(embed=pages[0], view=view)
        view.message = message

    @commands.command()
    async def buy(self, ctx, *, args: str = None):
        """Buy items from the shop
        
        Usage:
        .buy - Show shop menu
        .buy <item_id> - Buy 1 of an item
        .buy <item_id> <amount> - Buy multiple of the same item
        .buy <item_id1> <amount1> <item_id2> <amount2> ... - Buy multiple different items
        """
        try:
            if not args:
                # Show shop menu
                await self._show_shop_menu(ctx)
                return
                
            # Parse arguments
            parsed_items = self._parse_buy_args(args)
            
            if not parsed_items:
                await ctx.reply(f"❌ Invalid format. Use `{ctx.prefix}buy <item_id> [amount]` or `{ctx.prefix}buy help` for more info.")
                return
                
            # Handle help command
            if len(parsed_items) == 1 and parsed_items[0][0].lower() == "help":
                await self._show_buy_help(ctx)
                return
                
            # Process purchases
            await self._process_bulk_purchase(ctx, parsed_items)
            
        except Exception as e:
            self.logger.error(f"Buy command error: {e}")
            await ctx.reply("❌ Failed to complete purchase. Please try again later.")

    def _parse_buy_args(self, args: str) -> list:
        """Parse buy command arguments into [(item_id, amount), ...]"""
        parts = args.split()
        items = []
        
        i = 0
        while i < len(parts):
            item_id = parts[i]
            amount = 1
            
            # Check if next part is a number
            if i + 1 < len(parts) and parts[i + 1].isdigit():
                amount = int(parts[i + 1])
                i += 2
            else:
                i += 1
                
            items.append((item_id, amount))
            
        return items

    async def _show_shop_menu(self, ctx):
        """Show available shop categories"""
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
        """Show detailed buy command help"""
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
            value=f"• Use `{ctx.prefix}shop <category>` to see available items\n• Amounts default to 1 if not specified\n• Transactions are atomic - if one item fails, nothing is purchased",
            inline=False
        )
        
        await ctx.reply(embed=embed)

    async def _process_bulk_purchase(self, ctx, items: list):
        """Process multiple item purchases"""
        user_id = ctx.author.id
        guild_id = ctx.guild.id
        
        # Loop through all items and calculate total cost
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
                
            # Skip cost calculation for free items
            if item['price'] > 0:
                item_cost = item['price'] * amount
                total_cost += item_cost
            purchase_plan.append((item, amount, item_cost))
                
            item_cost = item['price'] * amount
            total_cost += item_cost
            purchase_plan.append((item, amount, item_cost))
        
        # Check if user has enough money
        wallet_balance = await db.get_wallet_balance(user_id, guild_id)
        if wallet_balance < total_cost:
            await ctx.reply(f"❌ Insufficient funds. Need **{total_cost:,}** coins, you have **{wallet_balance:,}** coins.")
            return
        
        # Show purchase confirmation for expensive purchases
        if total_cost > 10000 or len(purchase_plan) > 3:
            if not await self._confirm_purchase(ctx, purchase_plan, total_cost):
                return
        
        # Execute purchases
        await self._execute_bulk_purchase(ctx, purchase_plan, total_cost)

    def _item_supports_multiple(self, item: dict) -> bool:
        """Check if item can be purchased multiple times"""
        # Items that typically can't be bought multiple times
        single_purchase_types = ["role"]
        single_purchase_items = ["vip", "color_role"]
        
        if item.get("type") in single_purchase_types:
            return False
        if item.get("id") in single_purchase_items:
            return False
        if "upgrade" in item.get("id", "").lower():
            return False
            
        return True

    async def _confirm_purchase(self, ctx, purchase_plan: list, total_cost: int) -> bool:
        """Ask user to confirm expensive/bulk purchases"""
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
        """Execute the bulk purchase with proper error handling"""
        user_id = ctx.author.id
        guild_id = ctx.guild.id
        
        # Only deduct if total_cost > 0
        if total_cost > 0:
            if not await db.update_wallet(user_id, -total_cost, guild_id):
                await ctx.reply("❌ Failed to deduct payment. Purchase cancelled.")
                return
            
        successful_purchases = []
        failed_purchases = []
        refund_amount = 0
        
        # Process each item
        for item, amount, item_cost in purchase_plan:
            for i in range(amount):
                success = await self._purchase_single_item(user_id, item, guild_id)
                if success:
                    successful_purchases.append(item['name'])
                else:
                    failed_purchases.append(item['name'])
                    refund_amount += item['price']
        
        # Refund failed purchases
        if refund_amount > 0:
            await db.update_wallet(user_id, refund_amount, guild_id)
        
        # Send results
        await self._send_purchase_results(ctx, successful_purchases, failed_purchases, total_cost - refund_amount, refund_amount)

    async def _purchase_single_item(self, user_id: int, item: dict, guild_id: int) -> bool:
        """Purchase a single item (no cost deduction)"""
        try:
            # Skip all checks if item is free
            if item.get('price', 0) <= 0:
                return True
            shop_type = item.get('_shop_type', 'items')
            
            if shop_type == "fishing":
                if item.get("type") == "rod":
                    return await db.add_fishing_item(user_id, item, "rod")
                elif item.get("type") == "bait":
                    return await db.add_fishing_item(user_id, item, "bait")
                    
            elif shop_type == "potions":
                return await db.add_potion(user_id, item)
                
            elif shop_type == "upgrades":
                if item.get("_id") == "interest_token":
                    # Special handling for interest token
                    result = await db.db.users.update_one(
                        {"_id": str(user_id)},
                        {
                            "$push": {"inventory": item},
                            "$set": {"interest_token_active": True, "interest_rate_bonus": 0.05}
                        },
                        upsert=True
                    )
                    return result.modified_count > 0 or result.upserted_id is not None
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

    @commands.command()
    async def buy(self, ctx, *, args: str = None):
        """Buy items from the shop
        
        Usage:
        .buy - Show shop menu
        .buy <item_id> - Buy 1 of an item
        .buy <item_id> <amount> - Buy multiple of the same item
        .buy <item_id1> <amount1> <item_id2> <amount2> ... - Buy multiple different items
        """
        try:
            if not args:
                # Show shop menu
                await self._show_shop_menu(ctx)
                return
                
            # Parse arguments
            parsed_items = self._parse_buy_args(args)
            
            if not parsed_items:
                await ctx.reply(f"❌ Invalid format. Use `{ctx.prefix}buy <item_id> [amount]` or `{ctx.prefix}buy help` for more info.")
                return
                
            # Handle help command
            if len(parsed_items) == 1 and parsed_items[0][0].lower() == "help":
                await self._show_buy_help(ctx)
                return
                
            # Process purchases
            await self._process_bulk_purchase(ctx, parsed_items)
            
        except Exception as e:
            self.logger.error(f"Buy command error: {e}")
            await ctx.reply("❌ Failed to complete purchase. Please try again later.")

    def _parse_buy_args(self, args: str) -> list:
        """Parse buy command arguments into [(item_id, amount), ...]"""
        parts = args.split()
        items = []
        
        i = 0
        while i < len(parts):
            item_id = parts[i]
            amount = 1
            
            # Check if next part is a number
            if i + 1 < len(parts) and parts[i + 1].isdigit():
                amount = int(parts[i + 1])
                i += 2
            else:
                i += 1
                
            items.append((item_id, amount))
            
        return items

    async def _show_shop_menu(self, ctx):
        """Show available shop categories"""
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
        """Show detailed buy command help"""
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
            value=f"• Use `{ctx.prefix}shop <category>` to see available items\n• Amounts default to 1 if not specified\n• Transactions are atomic - if one item fails, nothing is purchased",
            inline=False
        )
        
        await ctx.reply(embed=embed)

    async def _process_bulk_purchase(self, ctx, items: list):
        """Process multiple item purchases"""
        user_id = ctx.author.id
        guild_id = ctx.guild.id
        
        # Validate all items and calculate total cost
        purchase_plan = []
        total_cost = 0
        
        for item_id, amount in items:
            if amount <= 0:
                await ctx.reply(f"❌ Invalid amount for {item_id}. Amount must be positive.")
                return
                
            if amount > 100:  # Reasonable limit
                await ctx.reply(f"❌ Amount too large for {item_id}. Maximum 100 per item.")
                return
                
            # Find item in shops
            item = await self._find_item_in_shops(item_id)
            if not item:
                await ctx.reply(f"❌ Item `{item_id}` not found in any shop.")
                return
                
            # Check if item supports multiple purchases
            if not self._item_supports_multiple(item) and amount > 1:
                await ctx.reply(f"❌ `{item['name']}` can only be purchased once at a time.")
                return
                
            item_cost = item['price'] * amount
            total_cost += item_cost
            purchase_plan.append((item, amount, item_cost))
        
        # Check if user has enough money
        wallet_balance = await db.get_wallet_balance(user_id, guild_id)
        if wallet_balance < total_cost:
            await ctx.reply(f"❌ Insufficient funds. Need **{total_cost:,}** coins, you have **{wallet_balance:,}** coins.")
            return
        
        # Show purchase confirmation for expensive purchases
        if total_cost > 10000 or len(purchase_plan) > 3:
            if not await self._confirm_purchase(ctx, purchase_plan, total_cost):
                return
        
        # Execute purchases
        await self._execute_bulk_purchase(ctx, purchase_plan, total_cost)

    async def _find_item_in_shops(self, item_id: str, user_id: int = None) -> dict:
        """Find item across all shop types with inventory check"""
        # First check if it's a beginner item
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
        
        # If it's a beginner item and user is provided, check inventory
        if item_id in beginner_items and user_id:
            fishing_items = await db.get_fishing_items(user_id)
            
            # For rod, check if they have any rod
            if item_id == "beginner_rod" and fishing_items["rods"]:
                beginner_items["beginner_rod"]["price"] = 50  # Make it cost if they already have a rod
                
            # For bait, check if they have any bait
            if item_id == "beginner_bait" and fishing_items["bait"]:
                beginner_items["beginner_bait"]["price"] = 10  # Make it cost if they already have bait
        
        # Return the modified beginner item or search other shops
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
        """Ask user to confirm expensive/bulk purchases"""
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
        """Execute the bulk purchase with proper error handling"""
        user_id = ctx.author.id
        guild_id = ctx.guild.id
        
        # Start transaction by deducting total cost first
        if not await db.update_wallet(user_id, -total_cost, guild_id):
            await ctx.reply("❌ Failed to deduct payment. Purchase cancelled.")
            return
        
        successful_purchases = []
        failed_purchases = []
        refund_amount = 0
        
        # Process each item
        for item, amount, item_cost in purchase_plan:
            for i in range(amount):
                success = await self._purchase_single_item(user_id, item, guild_id)
                if success:
                    successful_purchases.append(item['name'])
                else:
                    failed_purchases.append(item['name'])
                    refund_amount += item['price']
        
        # Refund failed purchases
        if refund_amount > 0:
            await db.update_wallet(user_id, refund_amount, guild_id)
        
        # Send results
        await self._send_purchase_results(ctx, successful_purchases, failed_purchases, total_cost - refund_amount)

    async def _purchase_single_item(self, user_id: int, item: dict, guild_id: int) -> bool:
        """Purchase a single item (no cost deduction)"""
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
                elif item.get("type") == "upgrade":
                    # Handle upgrade items - add to inventory
                    result = await db.db.users.update_one(
                        {"_id": str(user_id)},
                        {"$push": {"inventory": item}},
                        upsert=True
                    )
                    return result.modified_count > 0 or result.upserted_id is not None
                    
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
        """Send purchase results to user"""
        if not successful and not failed:
            await ctx.reply("❌ No items were processed.")
            return
        
        embed = discord.Embed(
            title="🛍️ Purchase Complete",
            color=0x00ff00 if not failed else 0xffa500
        )
        
        if successful:
            # Count occurrences of each item
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
                name="💰 Refunded:",
                value=f"{len(failed) * 'item price'} coins automatically refunded",
                inline=False
            )
        
        embed.add_field(
            name="💸 Total Spent:",
            value=f"**{total_spent:,}** coins",
            inline=True
        )
        
        # Show new balance
        new_balance = await db.get_wallet_balance(ctx.author.id, ctx.guild.id)
        embed.add_field(
            name="💰 Remaining Balance:",
            value=f"**{new_balance:,}** coins",
            inline=True
        )
        
        await ctx.reply(embed=embed)

    @commands.command(aliases=['jp'])
    async def jackpot(self, ctx, bet_amount: str = "25"):
        """Start a jackpot with custom entry fee. Default: 25
        Usage: !jackpot [bet] (supports all/max/half/percentages)"""
        
        # Get user's balance
        user_id = ctx.author.id
        wallet = await self.db.get_wallet_balance(user_id)
        bank = await self.db.get_bank_balance(user_id)
        total_balance = wallet + bank
        
        # Parse the bet amount
        parsed_amount, error = parse_bet(bet_amount, total_balance)
        if error:
            return await ctx.reply(f"❌ {error}")
                
        # Check if user can afford the bet
        if wallet < parsed_amount:
            needed = parsed_amount - wallet
            return await ctx.reply(
                f"❌ You need {needed}{self.currency} more in your wallet to join this jackpot!\n"
                f"💡 Use `.withdraw {needed}` to move money from your bank."
            )
        
        # Handle "all" or "max" with empty bank
        if bet_amount.lower() in ["all", "max"] and bank == 0:
            amt = parsed_amount
            parsed_amount *= 2  # Double the bet for free
            await ctx.send(f"🎁 Bonus! Since your bank is empty, your bet has been doubled to **{parsed_amount}{self.currency}** for no extra cost!")
        
        # Minimum bet check
        if parsed_amount < 10:
            return await ctx.reply(f"Minimum jackpot entry is 10{self.currency}!")
        
        # Check for existing jackpot with this bet amount
        channel_jackpots = self.active_jackpots.get(ctx.channel.id, {})
        if parsed_amount in channel_jackpots:
            try:
                message = await ctx.channel.fetch_message(channel_jackpots[parsed_amount])
                return await ctx.reply(
                    f"A jackpot with {parsed_amount}{self.currency} entry fee already exists!\n"
                    f"{message.jump_url}"
                )
            except discord.NotFound:
                # Clean up expired jackpot
                del channel_jackpots[parsed_amount]
        
        try:
            # Deduct the bet immediately
            if not await self.db.update_wallet(user_id, -amt or -parsed_amount):
                return await ctx.reply("❌ Failed to deduct your bet amount. Please try again.")
            
            embed = discord.Embed(
                description=(
                    f"🎰 **JACKPOT STARTED!** 🎰\n"
                    f"Hosted by: {ctx.author.mention}\n"
                    f"Entry: **{parsed_amount}{self.currency}**\n"
                    f"React with 🎉 within **15 seconds** to join!\n\n"
                    f"Current pot: **{parsed_amount}{self.currency}** (1 player)"
                ),
                color=discord.Color.gold()
            )
            jackpot_msg = await ctx.send(embed=embed)
            await jackpot_msg.add_reaction("🎉")
            
            # Store jackpot info
            if ctx.channel.id not in self.active_jackpots:
                self.active_jackpots[ctx.channel.id] = {}
            self.active_jackpots[ctx.channel.id][parsed_amount] = jackpot_msg.id
            
            participants = {ctx.author.id: ctx.author}  # Store as dict to avoid duplicates
            await asyncio.sleep(15)
            
            # Clean up jackpot tracking
            if ctx.channel.id in self.active_jackpots and parsed_amount in self.active_jackpots[ctx.channel.id]:
                del self.active_jackpots[ctx.channel.id][parsed_amount]
                if not self.active_jackpots[ctx.channel.id]:
                    del self.active_jackpots[ctx.channel.id]
            
            try:
                jackpot_msg = await ctx.channel.fetch_message(jackpot_msg.id)
                reaction = next((r for r in jackpot_msg.reactions if str(r.emoji) == "🎉"), None)
                
                if reaction:
                    async for user in reaction.users():
                        if not user.bot and user.id != ctx.author.id:
                            # Check each participant's balance
                            user_wallet = await self.db.get_wallet_balance(user.id)
                            if user_wallet >= parsed_amount:
                                if await self.db.update_wallet(user.id, -parsed_amount):
                                    participants[user.id] = user
                                else:
                                    await ctx.send(f"{user.mention} couldn't join - transaction failed!")
                            else:
                                await ctx.send(f"{user.mention} couldn't join - insufficient funds!")
                
                if len(participants) == 1:
                    # Refund the host if no one joined
                    await self.db.update_wallet(ctx.author.id, parsed_amount)
                    return await ctx.send(embed=discord.Embed(
                        description=f"❌ Only {ctx.author.mention} joined. Refunded {parsed_amount}{self.currency}",
                        color=discord.Color.red()
                    ))
                
                pot = len(participants) * parsed_amount
                winner_id, winner = random.choice(list(participants.items()))
                
                # Calculate each participant's chance of winning
                win_chance = 100 / len(participants)
                
                # Award the pot to the winner
                if not await self.db.update_wallet(winner_id, pot):
                    await ctx.send("❌ Failed to award the jackpot prize! Please contact an admin.")
                    # Refund all participants
                    for uid in participants:
                        await self.db.update_wallet(uid, parsed_amount)
                    return
                
                await ctx.send(embed=discord.Embed(
                    description=(
                        f"🎉 **JACKPOT RESULTS** 🎉\n"
                        f"Entry Fee: **{parsed_amount}{self.currency}**\n"
                        f"Total entries: **{len(participants)}**\n"
                        f"Total pot: **{pot}{self.currency}**\n"
                        f"Winner: {winner.mention} (had a **{win_chance:.1f}%** chance)\n\n"
                        f"🏆 **{winner.display_name} takes {pot}{self.currency}!** 🏆"
                    ),
                    color=discord.Color.green()
                ))
                
            except discord.NotFound:
                await ctx.send(embed=discord.Embed(
                    description="❌ Jackpot message was deleted. Refunding all participants...",
                    color=discord.Color.red()
                ))
                # Refund all participants
                for uid in participants:
                    await self.db.update_wallet(uid, parsed_amount)
                    
        except Exception as e:
            self.bot.logger.error(f"Jackpot error: {e}")
            # Clean up and attempt to refund if something went wrong
            if ctx.channel.id in self.active_jackpots and parsed_amount in self.active_jackpots[ctx.channel.id]:
                del self.active_jackpots[ctx.channel.id][parsed_amount]
                if not self.active_jackpots[ctx.channel.id]:
                    del self.active_jackpots[ctx.channel.id]
            
            await ctx.send("❌ An error occurred during the jackpot. Refunding participants...")
            await self.db.update_wallet(ctx.author.id, parsed_amount)

    @commands.command(aliases=['cf'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def coinflip(self, ctx, bet_amount: str, choice: str = None):
        """Bet on a coinflip (heads/tails)"""
        balance = await db.get_wallet_balance(ctx.author.id, ctx.guild.id)
        bet, error = parse_bet(bet_amount, balance)
        
        if error:
            return await ctx.reply(embed=discord.Embed(description=error, color=discord.Color.red()))
        
        if bet < 10:
            return await ctx.reply(embed=discord.Embed(description="Minimum bet is 10!", color=discord.Color.red()))
        
        if not choice or choice.lower() not in ['heads', 'tails', 'h', 't']:
            return await ctx.reply(embed=discord.Embed(description="Choose either 'heads' or 'tails'!", color=discord.Color.red()))
        
        if not await db.update_wallet(ctx.author.id, -bet, ctx.guild.id):
            return await ctx.reply(embed=discord.Embed(description="Insufficient funds!", color=discord.Color.red()))
        
        result = random.choice(['heads', 'tails'])
        user_choice = choice[0].lower()
        
        suspense = min(5, bet // 1000)  # 5 seconds max
        msg = await ctx.reply(embed=discord.Embed(description=f"Flipping the coin... **{bet}** {self.currency} on the line...", color=discord.Color.blurple()))
        await asyncio.sleep(suspense)
        
        if (user_choice == 'h' and result == 'heads') or (user_choice == 't' and result == 'tails'):
            winnings = bet * 2
            await db.update_wallet(ctx.author.id, winnings, ctx.guild.id)
            await msg.edit(embed=discord.Embed(description=f"**IT'S {result.upper()}!** You won **{winnings}** {self.currency}!", color=discord.Color.green()))
        else:
            await msg.edit(embed=discord.Embed(description=f"**IT'S {result.upper()}!** You lost **{bet}** {self.currency}!", color=discord.Color.red()))

    @commands.command(aliases=['bj'])
    @commands.cooldown(1, 5, commands.BucketType.user)  # 5 second cooldown
    async def blackjack(self, ctx, bet_amount: str = None):
        """Play blackjack against the dealer
        Usage: !blackjack <amount/all/max/50%/1k/1m>"""
        if not bet_amount:
            return await ctx.reply("Please specify a bet amount! (all/max/50%/1k/1m)")

        balance = await db.get_user_balance(ctx.author.id, ctx.guild.id)
        bet, error = parse_bet(bet_amount, balance)
        
        if error:
            return await ctx.reply(error)

        if bet < 10:
            return await ctx.reply("Minimum bet is 10!")
        if bet > balance:
            return await ctx.reply("You don't have enough money!")

        if not await db.update_wallet(ctx.author.id, -bet, ctx.guild.id):
            return await ctx.reply("Failed to deduct bet from your balance!")

        def calculate_hand(hand):
            total = 0
            aces = 0
            for card in hand:
                if card == 1:  # Ace
                    aces += 1
                else:
                    total += min(card, 10)
            for _ in range(aces):
                if total + 11 <= 21:
                    total += 11
                else:
                    total += 1
            return total

        def format_card(card):
            if card == 1:
                return 'A'
            elif card == 11:
                return 'J'
            elif card == 12:
                return 'Q'
            elif card == 13:
                return 'K'
            return str(card)

        # Deal initial cards
        player_hands = [[random.randint(1, 13), random.randint(1, 13)]]
        hand_bets = [bet]
        dealer_hand = [random.randint(1, 13), random.randint(1, 13)]
        current_hand = 0
        doubled = [False]  # Track doubled hands
        
        while current_hand < len(player_hands):
            hand = player_hands[current_hand]
            player_total = calculate_hand(hand)
            dealer_total = calculate_hand(dealer_hand)

            # Format cards
            player_cards = ' '.join(format_card(c) for c in hand)
            dealer_cards = f"{format_card(dealer_hand[0])} ??"

            # Check for split option
            can_split = (
                len(hand) == 2 and 
                min(hand[0], 10) == min(hand[1], 10) and 
                len(player_hands) < 4 and 
                await db.get_user_balance(ctx.author.id, ctx.guild.id) >= hand_bets[current_hand]
            )

            # Check for double down option
            can_double = (
                len(hand) == 2 and 
                not doubled[current_hand] and 
                await db.get_user_balance(ctx.author.id, ctx.guild.id) >= hand_bets[current_hand]
            )

            # Show game state
            embed = discord.Embed(
                title="Blackjack Game",
                description=(
                    f"**Dealer's Hand:** {dealer_cards}\n"
                    f"**Your Hand {current_hand + 1}:** {player_cards} (Total: {player_total})\n"
                    f"**Current Bet:** {hand_bets[current_hand]}\n\n"
                    "Options:\n"
                    "• Type `hit` to take another card\n"
                    "• Type `stand` to keep your hand\n" +
                    ("• Type `double` to double your bet and take one card\n" if can_double else "") +
                    ("• Type `split` to split your hand\n" if can_split else "")
                ),
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)

            # Get player action
            valid_actions = ['hit', 'stand', 'h', 's']
            if can_double:
                valid_actions.extend(['double', 'd'])
            if can_split:
                valid_actions.extend(['split', 'sp'])

            def check(m):
                return (
                    m.author == ctx.author and 
                    m.channel == ctx.channel and 
                    m.content.lower() in valid_actions
                )

            try:
                action = await self.bot.wait_for('message', timeout=30, check=check)
                action = action.content.lower()

                if action in ['hit', 'h']:
                    hand.append(random.randint(1, 13))
                    if calculate_hand(hand) > 21:
                        current_hand += 1  # Bust, move to next hand

                elif action in ['stand', 's']:
                    current_hand += 1  # Stand, move to next hand

                elif action in ['double', 'd'] and can_double:
                    # Double the bet for this hand
                    if not await db.update_wallet(ctx.author.id, -hand_bets[current_hand], ctx.guild.id):
                        await ctx.send("Not enough money to double down!")
                        continue
                    hand_bets[current_hand] *= 2
                    hand.append(random.randint(1, 13))
                    doubled[current_hand] = True
                    current_hand += 1

                elif action in ['split', 'sp'] and can_split:
                    # Split the hand
                    if not await db.update_wallet(ctx.author.id, -hand_bets[current_hand], ctx.guild.id):
                        await ctx.send("Not enough money to split!")
                        continue
                    new_hand = [hand.pop()]
                    hand.append(random.randint(1, 13))
                    new_hand.append(random.randint(1, 13))
                    player_hands.append(new_hand)
                    hand_bets.append(hand_bets[current_hand])  # Same bet for new hand
                    doubled.append(False)

            except asyncio.TimeoutError:
                await ctx.send("Time's up! Standing with current hand.")
                current_hand += 1

        # Dealer's turn
        dealer_cards = ' '.join(format_card(c) for c in dealer_hand)
        while calculate_hand(dealer_hand) < 17:
            dealer_hand.append(random.randint(1, 13))
        
        dealer_total = calculate_hand(dealer_hand)
        dealer_cards = ' '.join(format_card(c) for c in dealer_hand)

        # Calculate results
        results = []
        total_winnings = 0
        
        for i, hand in enumerate(player_hands):
            player_total = calculate_hand(hand)
            hand_bet = hand_bets[i]
            if player_total > 21:
                result = "Bust"
                winnings = 0  # Already lost bet
            elif dealer_total > 21 or player_total > dealer_total:
                result = "Win"
                winnings = hand_bet * 2  # Win: get back bet + winnings
            elif player_total < dealer_total:
                result = "Lose"
                winnings = 0  # Already lost bet
            else:
                result = "Push"
                winnings = hand_bet  # Get back bet only

            total_winnings += winnings
            results.append(f"Hand {i + 1}: {' '.join(format_card(c) for c in hand)} ({player_total}) - {result}")

        # Calculate net winnings (subtract initial total bet)
        net_winnings = total_winnings - sum(hand_bets)
        if net_winnings != 0:
            await db.update_balance(ctx.author.id, total_winnings, ctx.guild.id)

        # Show final results
        embed = discord.Embed(
            title="Blackjack Results",
            description=(
                f"**Dealer's Hand:** {dealer_cards} (Total: {dealer_total})\n\n" +
                "\n".join(results) + "\n\n" +
                f"**Net {'Winnings' if net_winnings >= 0 else 'Loss'}:** {abs(net_winnings)}"
            ),
            color=discord.Color.green() if net_winnings > 0 else discord.Color.red()
        )
        await ctx.send(embed=embed)

    async def get_server_shop(self, guild_id: int) -> dict:
        """Get shop items for a specific server"""
        shop = await db.db.shops.find_one({"_id": f"server_{guild_id}"})
        if shop:
            return shop.get("items", {})
            
        # Initialize default server shop
        default_items = {
            "role_token": {
                "name": "Custom Role Token",
                "price": 5000,
                "description": "Create a custom role with a color of your choice"
            },
            "exp_boost": {
                "name": "XP Boost",
                "price": 2500,
                "description": "Get 2x XP for 1 hour"
            }
        }
        
        # Save the default shop for this server
        await db.db.shops.insert_one({
            "_id": f"server_{guild_id}",
            "items": default_items
        })
        
        return default_items

    @commands.group(invoke_without_command=True)
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def shop(self, ctx):
        """View available shop categories"""
        categories = {
            "items": {"name": "Item Shop", "icon": "🛍️", "cmd": "items"},
            "potions": {"name": "Potion Shop", "icon": "🧪", "cmd": "potions"},
            "rod": {"name": "Fishing Rods", "icon": "🎣", "cmd": "rods"},
            "bait": {"name": "Fishing Bait", "icon": "🪱", "cmd": "bait"},
            "upgrades": {"name": "Upgrades Shop", "icon": "⚡", "cmd": "upgrades"}
        }
        
        embed = discord.Embed(
            title="🏪 The Shop",
            description="Welcome! Choose a category to browse:",
            color=discord.Color.blue()
        )
        
        for cat_id, cat in categories.items():
            embed.add_field(
                name=f"{cat['icon']} {cat['name']}",
                value=f"Use `.shop {cat['cmd']}` to browse",
                inline=True
            )
            
        embed.set_footer(text=f"Your Balance: {await db.get_wallet_balance(ctx.author.id)}")
        await ctx.reply(embed=embed)
        
    @shop.command(name="items")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def shop_items(self, ctx):
        """View general items shop"""
        items = await db.get_shop_items("items", ctx.guild.id if ctx.guild else None)
        if not items:
            return await ctx.reply("❌ No items available in the shop!")

        # Ensure items is a list of dictionaries with required fields
        if not isinstance(items, list):
            items = list(items.values()) if isinstance(items, dict) else []
        
        if not items:
            return await ctx.reply("❌ No items available in the shop!")
        
        # Validate items
        valid_items = []
        for item in items:
            if not isinstance(item, dict):
                continue
            if not all(key in item for key in ['name', 'price', 'description', 'id']):
                continue
            
            # Ensure values aren't None or empty
            if not all(str(item[key]).strip() for key in ['name', 'description']):
                continue
                
            valid_items.append(item)
        
        if not valid_items:
            return await ctx.reply("❌ No valid items available in the shop!")
        
        try:
            balance = await db.get_wallet_balance(ctx.author.id, ctx.guild.id)
            balance_str = str(balance) if balance is not None else "0"
        except Exception:
            balance_str = "0"
        
        # Create pages with simplified format for button generation
        pages = []
        chunks = [valid_items[i:i+5] for i in range(0, len(valid_items), 5)]
        
        for page_num, chunk in enumerate(chunks, 1):
            embed = discord.Embed(
                title="🛍️ Item Shop",
                description=f"💰 Your Balance: **{balance_str}** {self.currency}",
                color=discord.Color.blue()
            )
            
            for item in chunk:
                # Truncate description if too long
                desc = str(item['description'])[:100]
                if len(str(item['description'])) > 100:
                    desc += "..."
                
                # Create field name with price
                field_name = f"{str(item['name'])[:30]} - {item['price']} {self.currency}"
                
                # Create field value with buy command
                field_value = f"{desc}\n`buy {item['id']}`"
                
                embed.add_field(
                    name=field_name,
                    value=field_value,
                    inline=False
                )
            
            # Add page footer
            if len(chunks) > 1:
                embed.set_footer(text=f"Page {page_num}/{len(chunks)} • {len(valid_items)} total items")
            else:
                embed.set_footer(text=f"{len(valid_items)} items available")
            
            pages.append(embed)
        
        # Create and send with custom view
        view = EconomyShopView(pages, ctx.author)
        message = await ctx.reply(embed=pages[0], view=view)
        view.message = message

    @shop.command(name="rods", aliases=["rod"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def shop_rods(self, ctx):
        """View available fishing rods"""
        try:
            # Get rod items from database
            rods = await db.get_shop_items("fishing", ctx.guild.id if ctx.guild else None)
            
            if not rods:
                return await ctx.reply("❌ No rods available in the shop!")
                
            # Ensure rods is a list of dictionaries
            if not isinstance(rods, list):
                rods = list(rods.values()) if isinstance(rods, dict) else []
                
            # Filter for rods only and validate
            valid_rods = []
            for item in rods:
                if not isinstance(item, dict):
                    continue
                if item.get('type') != 'rod':
                    continue
                if not all(key in item for key in ['name', 'price', 'description', 'id']):
                    continue
                # Ensure values aren't None or empty
                if not all(str(item[key]).strip() for key in ['name', 'description']):
                    continue
                valid_rods.append(item)
                
            if not valid_rods:
                return await ctx.reply("❌ No valid rods available in the shop!")
                
            try:
                balance = await db.get_wallet_balance(ctx.author.id, ctx.guild.id)
                balance_str = str(balance) if balance is not None else "0"
            except Exception:
                balance_str = "0"
                
            # Create pages with simplified format for button generation
            pages = []
            chunks = [valid_rods[i:i+5] for i in range(0, len(valid_rods), 5)]
            
            for page_num, chunk in enumerate(chunks, 1):
                embed = discord.Embed(
                    title="🎣 Fishing Rod Shop",
                    description=f"💰 Your Balance: **{balance_str}** {self.currency}",
                    color=discord.Color.blue()
                )
                
                for rod in chunk:
                    # Create field name with price
                    field_name = f"{str(rod['name'])[:30]} - {rod['price']} {self.currency}"
                    
                    # Create field value with buy command
                    field_value = f"Multiplier: {rod.get('multiplier', 1)}x\n`buy {rod['id']}`"
                    
                    embed.add_field(
                        name=field_name,
                        value=field_value,
                        inline=False
                    )
                
                # Add page footer
                if len(chunks) > 1:
                    embed.set_footer(text=f"Page {page_num}/{len(chunks)} • {len(valid_rods)} total rods")
                else:
                    embed.set_footer(text=f"{len(valid_rods)} rods available")
                    
                pages.append(embed)
            
            # Create and send with custom view
            view = EconomyShopView(pages, ctx.author)
            message = await ctx.reply(embed=pages[0], view=view)
            view.message = message
            
        except Exception as e:
            self.logger.error(f"Error in rod shop: {e}")
            await ctx.reply("An error occurred while loading the rod shop.")

    @shop.command(name="bait", aliases=["baits"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def shop_bait(self, ctx):
        """View available fishing bait"""
        try:
            # Get bait items from database
            shop_data = await db.get_shop_items("bait_shop", ctx.guild.id if ctx.guild else None)
            
            if not shop_data or "bait_shop" not in shop_data:
                # Fallback to default bait items if none found
                bait_items = self.DEFAULT_FISHING_ITEMS.get("bait_shop", {})
            else:
                bait_items = shop_data["bait_shop"]
                
            if not bait_items:
                return await ctx.reply("❌ No bait available in the shop!")
                
            # Convert to list of items with their IDs
            valid_baits = []
            for item_id, item in bait_items.items():
                if not isinstance(item, dict):
                    continue
                if not all(key in item for key in ['name', 'price', 'description']):
                    continue
                    
                # Add the item ID to the item data
                item['id'] = item_id
                valid_baits.append(item)
                
            if not valid_baits:
                return await ctx.reply("❌ No valid bait available in the shop!")
                
            try:
                balance = await db.get_wallet_balance(ctx.author.id, ctx.guild.id)
                balance_str = str(balance) if balance is not None else "0"
            except Exception:
                balance_str = "0"
                
            # Create pages with simplified format for button generation
            pages = []
            chunks = [valid_baits[i:i+5] for i in range(0, len(valid_baits), 5)]
            
            for page_num, chunk in enumerate(chunks, 1):
                embed = discord.Embed(
                    title="🪱 Fishing Bait Shop",
                    description=f"💰 Your Balance: **{balance_str}** {self.currency}",
                    color=discord.Color.blue()
                )
                
                for bait in chunk:
                    # Create field name with price
                    field_name = f"{str(bait['name'])[:30]} - {bait['price']} {self.currency}"
                    
                    # Create field value with buy command
                    field_value = f"Amount: {bait.get('amount', 1)}\n`buy {bait['id']}`"
                    
                    embed.add_field(
                        name=field_name,
                        value=field_value,
                        inline=False
                    )
                
                # Add page footer
                if len(chunks) > 1:
                    embed.set_footer(text=f"Page {page_num}/{len(chunks)} • {len(valid_baits)} total baits")
                else:
                    embed.set_footer(text=f"{len(valid_baits)} baits available")
                    
                pages.append(embed)
            
            # Create and send with custom view
            view = EconomyShopView(pages, ctx.author)
            message = await ctx.reply(embed=pages[0], view=view)
            view.message = message
            
        except Exception as e:
            self.logger.error(f"Error in bait shop: {e}")
            await ctx.reply("An error occurred while loading the bait shop.")

    @shop.command(name="potions")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def shop_potions(self, ctx):
        """View available potions"""
        try:
            # Get potion items from database
            potions = await db.get_shop_items("potions", ctx.guild.id if ctx.guild else None)
            
            if not potions:
                return await ctx.reply("❌ No potions available in the shop!")
                
            # Ensure potions is a list of dictionaries with required fields
            if not isinstance(potions, list):
                potions = list(potions.values()) if isinstance(potions, dict) else []
                
            if not potions:
                return await ctx.reply("❌ No potions available in the shop!")
                
            # Validate potion items
            valid_potions = []
            for potion in potions:
                if not isinstance(potion, dict):
                    continue
                if not all(key in potion for key in ['name', 'price', 'description', 'id']):
                    continue
                # Ensure values aren't None or empty
                if not all(str(potion[key]).strip() for key in ['name', 'description']):
                    continue
                valid_potions.append(potion)
                
            if not valid_potions:
                return await ctx.reply("❌ No valid potions available in the shop!")
                
            try:
                balance = await db.get_wallet_balance(ctx.author.id, ctx.guild.id)
                balance_str = str(balance) if balance is not None else "0"
            except Exception:
                balance_str = "0"
                
            # Create pages with simplified format for button generation
            pages = []
            chunks = [valid_potions[i:i+5] for i in range(0, len(valid_potions), 5)]
            
            for page_num, chunk in enumerate(chunks, 1):
                embed = discord.Embed(
                    title="🧪 Potion Shop",
                    description=f"💰 Your Balance: **{balance_str}** {self.currency}",
                    color=discord.Color.purple()
                )
                
                for potion in chunk:
                    # Format duration
                    duration = potion.get('duration', 60)
                    duration_text = f"{duration} minutes"
                    if duration >= 60:
                        hours = duration // 60
                        minutes = duration % 60
                        if minutes == 0:
                            duration_text = f"{hours} hour{'s' if hours > 1 else ''}"
                        else:
                            duration_text = f"{hours}h {minutes}m"
                    
                    # Create field name with price
                    field_name = f"{str(potion['name'])[:30]} - {potion['price']} {self.currency}"
                    
                    # Create field value with buy command
                    field_value = f"Duration: {duration_text}\n`buy {potion['id']}`"
                    
                    embed.add_field(
                        name=field_name,
                        value=field_value,
                        inline=False
                    )
                
                # Add page footer
                if len(chunks) > 1:
                    embed.set_footer(text=f"Page {page_num}/{len(chunks)} • {len(valid_potions)} total potions")
                else:
                    embed.set_footer(text=f"{len(valid_potions)} potions available")
                    
                pages.append(embed)
            
            # Create and send with custom view
            view = EconomyShopView(pages, ctx.author)
            message = await ctx.reply(embed=pages[0], view=view)
            view.message = message
            
        except Exception as e:
            self.logger.error(f"Error in potion shop: {e}")
            await ctx.reply("An error occurred while loading the potion shop.")

    @shop.command(name="upgrades")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def shop_upgrades(self, ctx):
        """View available upgrades like bank expansions"""
        try:
            # Get upgrade items from database
            upgrades = await db.get_shop_items("upgrades", ctx.guild.id if ctx.guild else None)
            print(f"Upgrades data: {upgrades}")  # Debugging line
            
            if not upgrades:
                return await ctx.reply("❌ No upgrades available in the shop!")
                
            # Ensure upgrades is a list of dictionaries with required fields
            if not isinstance(upgrades, list):
                upgrades = list(upgrades.values()) if isinstance(upgrades, dict) else []
                
            # Validate upgrade items
            valid_upgrades = []
            for upgrade in upgrades:
                if not isinstance(upgrade, dict):
                    continue
                allowed_types = ['bank', 'fishing', 'upgrade']
                if upgrade.get('type') not in allowed_types:
                    continue
                required_keys = ['name', 'price', 'description', 'id', 'type']
                if not all(key in upgrade for key in required_keys):
                    continue
                # Ensure values aren't None or empty
                if not all(str(upgrade[key]).strip() for key in ['name', 'description']):
                    continue
                valid_upgrades.append(upgrade)
                
            if not valid_upgrades:
                return await ctx.reply("❌ No valid bank upgrades available in the shop!")
                
            try:
                balance = await db.get_wallet_balance(ctx.author.id, ctx.guild.id)
                balance_str = str(balance) if balance is not None else "0"
            except Exception:
                balance_str = "0"
                
            # Create pages with simplified format
            pages = []
            chunks = [valid_upgrades[i:i+5] for i in range(0, len(valid_upgrades), 5)]
            
            for page_num, chunk in enumerate(chunks, 1):
                embed = discord.Embed(
                    title="⚡ Upgrade Shop",
                    description=f"💰 Your Balance: **{balance_str}** {self.currency}",
                    color=discord.Color.gold()
                )
                
                for upgrade in chunk:
                    # Create field name with price
                    field_name = f"{str(upgrade['name'])[:30]} - {upgrade['price']} {self.currency}"
                    
                    # Create field value with buy command
                    field_value = (
                        f"{upgrade['description']}\n"
                        f"`buy {upgrade['id']}`"
                    )
                    
                    embed.add_field(
                        name=field_name,
                        value=field_value,
                        inline=False
                    )
                
                # Add page footer
                if len(chunks) > 1:
                    embed.set_footer(text=f"Page {page_num}/{len(chunks)} • {len(valid_upgrades)} total upgrades")
                else:
                    embed.set_footer(text=f"{len(valid_upgrades)} upgrades available")
                    
                pages.append(embed)
            
            # Create and send with EconomyShopView (which doesn't have the select menu issue)
            view = EconomyShopView(pages, ctx.author)
            message = await ctx.reply(embed=pages[0], view=view)
            view.message = message
            
        except Exception as e:
            self.logger.error(f"Error in upgrades shop: {e}")
            await ctx.reply("An error occurred while loading the upgrades shop.")

    async def buy_item(self, user_id: int, item_id: str, guild_id: int = None) -> tuple[bool, str]:
        """Buy an item from any shop"""
        if not await self.ensure_connected():
            return False, "Database connection failed"
            
        try:
            # Check all possible shop collections for the item
            item = None
            item_type = None
            
            # First check the bait shop (special structure)
           

            bait_shop = await self.db.shops.find_one({"_id": f"bait_shop_{guild_id}" if guild_id else "bait_shop_global"})
            if bait_shop and item_id in bait_shop.get("items", {}):
                item = bait_shop["items"][item_id]
                item_type = "bait"
            
            # If not bait, check other shop types
            if not item:
                shop_types = [
                    ("items", "item"),
                    ("potions", "potion"),
                    ("fishing_rods", "fishing_rod"),
                    ("upgrades", "upgrade")
                ]
                
                for collection, i_type in shop_types:
                    doc = await self.db.shops.find_one({
                        "_id": f"{collection}_{guild_id}" if guild_id else f"{collection}_global",
                        f"items.{item_id}": {"$exists": True}
                    })
                    if doc:
                        item = doc["items"][item_id]
                        item_type = i_type
                        break
            
            if not item:
                return False, "Item not found in any shop"
                
            # Add the item ID to the item data
            item['id'] = item_id
            
            # Check if user has enough money
            wallet_balance = await self.get_wallet_balance(user_id, guild_id)
            if wallet_balance < item["price"]:
                return False, f"Insufficient funds. Need {item['price']}, have {wallet_balance}"
                
            # Process the purchase
            async with await self.client.start_session() as session:
                async with session.start_transaction():
                    # Deduct money first
                    if not await self.update_wallet(user_id, -item["price"], guild_id):
                        return False, "Failed to deduct payment"
                    
                    # Handle different item types
                    if item_type == "bait":
                        # Add bait to fishing items
                        result = await self.db.users.update_one(
                            {"_id": str(user_id)},
                            {"$push": {"fishing_items.bait": item}},
                            session=session
                        )
                        if not result.modified_count:
                            await session.abort_transaction()
                            return False, "Failed to add bait to inventory"
                    
                    elif item_type == "fishing_rod":
                        # Add or replace fishing rod
                        result = await self.db.users.update_one(
                            {"_id": str(user_id)},
                            {"$set": {"fishing_items.rod": item}},
                            session=session
                        )
                        if not result.modified_count:
                            await session.abort_transaction()
                            return False, "Failed to equip fishing rod"
                    
                    elif item_type == "potion":
                        # Activate potion effect
                        result = await self.db.users.update_one(
                            {"_id": str(user_id)},
                            {"$push": {"active_effects": item}},
                            session=session
                        )
                        if not result.modified_count:
                            await session.abort_transaction()
                            return False, "Failed to activate potion"
                    
                    elif item_type == "upgrade":
                        # Handle bank upgrades
                        if item.get("upgrade_type") == "bank":
                            result = await self.db.users.update_one(
                                {"_id": str(user_id)},
                                {"$inc": {"bank_limit": item["amount"]}},
                                session=session
                            )
                            if not result.modified_count:
                                await session.abort_transaction()
                                return False, "Failed to upgrade bank"
                    
                    elif item_type == "item":
                        # Add to general inventory
                        result = await self.db.users.update_one(
                            {"_id": str(user_id)},
                            {"$push": {"inventory": item}},
                            session=session
                        )
                        if not result.modified_count and not result.upserted_id:
                            await session.abort_transaction()
                            return False, "Failed to add item to inventory"
                    
                    return True, f"✅ Successfully purchased {item['name']} for {item['price']} {self.currency}!"
                    
        except Exception as e:
            self.logger.error(f"Failed to buy item {item_id}: {e}")
            return False, f"Purchase failed: {str(e)}"

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def globalshop(self, ctx):
        """View the global shop"""
        # Reuse the same shop display logic
        await self.shop(ctx)

    @commands.command(name="potions", aliases=["potion", "pot", "pots"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def potions(self, ctx):
        """View available potions from global and server shops"""
        global_shop = await db.get_shop_items()
        server_shop = await db.get_shop_items(ctx.guild.id)
        
        # Combine potions from both shops
        potions = {}
        if "potions" in global_shop:
            potions.update(global_shop["potions"])
        if "potions" in server_shop:
            potions.update(server_shop["potions"])
            
        if not potions:
            return await ctx.reply("No potions available in the shop!")

        # Validate potions data
        valid_potions = {}
        for potion_id, potion in potions.items():
            if not isinstance(potion, dict):
                continue
            if not all(key in potion for key in ['name', 'price', 'multiplier', 'type', 'duration']):
                continue
            # Ensure values aren't None or empty
            if not all(str(potion[key]).strip() for key in ['name', 'type'] if potion.get(key)):
                continue
            valid_potions[potion_id] = potion

        if not valid_potions:
            return await ctx.reply("No valid potions available in the shop!")

        try:
            balance = await db.get_wallet_balance(ctx.author.id, ctx.guild.id)
            balance_str = str(balance) if balance is not None else "0"
        except Exception:
            balance_str = "0"

        # Create embed pages for potions
        pages = []
        
        # Overview page
        overview = discord.Embed(
            title="🧪 Available Potions",
            description=f"Your Balance: **{balance_str}** {self.currency}\n\n",
            color=discord.Color.blue()
        )
        
        # Add first 3 potions to overview
        sample_potions = list(valid_potions.items())[:3]
        for potion_id, potion in sample_potions:
            overview.description += (
                f"**{potion['name']}** - {potion['price']} {self.currency}\n"
                f"• {potion['multiplier']}x {potion['type']} buff for {potion['duration']}min\n"
                f"• {potion.get('description', '')}\n"
                f"`buy {potion_id}` to purchase\n\n"
            )
            
        if len(valid_potions) > 3:
            overview.description += "*Use the arrows to see more potions*"
        
        pages.append(overview)
        
        # Create detail pages - 4 potions per page
        items = list(valid_potions.items())
        chunks = [items[i:i+4] for i in range(0, len(items), 4)]
        
        for page_num, chunk in enumerate(chunks, 1):
            embed = discord.Embed(
                title="🧪 Potions Shop",
                color=discord.Color.blue()
            )
            
            for potion_id, potion in chunk:
                # Truncate description if too long
                desc = str(potion.get('description', ''))[:100]
                if len(str(potion.get('description', ''))) > 100:
                    desc += "..."
                    
                embed.add_field(
                    name=f"{potion['name']} - {potion['price']} {self.currency}",
                    value=(
                        f"Type: {potion['type']}\n"
                        f"Effect: {potion['multiplier']}x for {potion['duration']}min\n"
                        f"{desc}\n"
                        f"`buy {potion_id}` to purchase"
                    ),
                    inline=False
                )
            
            # Add page footer
            if len(chunks) > 1:
                embed.set_footer(text=f"Page {page_num + 1}/{len(chunks) + 1} • {len(valid_potions)} total potions")
            else:
                embed.set_footer(text=f"{len(valid_potions)} potions available")
            
            pages.append(embed)

        # Use EconomyShopView instead of HelpPaginator
        view = EconomyShopView(pages, ctx.author)
        message = await ctx.reply(embed=pages[0], view=view)
        view.message = message

    @commands.command(name="inventory", aliases=["inv"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def inventory(self, ctx):
        """View your inventory with filtering and pagination"""
        items = await db.get_inventory(ctx.author.id, ctx.guild.id)
        if not items:
            return await ctx.reply("Your inventory is empty!")
        
        # Items now come pre-grouped with quantities
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
                
                # Show quantity if more than 1
                if quantity > 1:
                    name = f"**{quantity}x** {name}"
                
                # Add emojis based on type
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
        
        # Use your existing view
        view = EconomyShopView(pages, ctx.author)
        await ctx.reply(embed=pages[0], view=view)

    @commands.command(name="use")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def use_item(self, ctx, item_id: str):
        """Use an item from your inventory"""
        items = await db.get_inventory(ctx.author.id, ctx.guild.id)
        
        # Find the item
        item = next((item for item in items if item.get("id") == item_id), None)
        if not item:
            return await ctx.reply("❌ Item not found in your inventory!")

        # Handle different item types
        if item["type"] == "potion":
            # Apply potion effect
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
            # Handle consumable effects
            await db.remove_from_inventory(ctx.author.id, ctx.guild.id, item_id)
            embed = discord.Embed(
                description=f"✨ Used **{item['name']}**!",
                color=discord.Color.green()
            )
            await ctx.reply(embed=embed)
            
        else:
            await ctx.reply("❌ This item cannot be used!")

    @commands.command(name="fish", aliases=["fishing"])
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def fish(self, ctx):
        """Go fishing! Requires a rod and bait."""
        # Get user's fishing items
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
            embed.add_field(
                name="How to Buy",
                value="Use these commands:\n`.shop rod` - View fishing rods\n`.shop bait` - View fishing bait",
                inline=False
            )
            return await ctx.reply(embed=embed)
        
        if not fishing_items["bait"]:
            return await ctx.reply("❌ You need bait to go fishing! Buy some from `.shop bait`")
        
        # Select rod and bait
        rod = fishing_items["rods"][0]  # Use first rod
        bait = fishing_items["bait"][0]  # Use first bait
        
        # Remove one bait
        if not await db.remove_bait(ctx.author.id, bait["id"]):
            return await ctx.reply("❌ Failed to use bait!")
            
        # Calculate catch chances
        base_chances = {
            "normal": 0.7 * bait.get("catch_rates", {}).get("normal", 1.0),
            "rare": 0.2 * bait.get("catch_rates", {}).get("rare", 0.1),
            "event": 0.08 * bait.get("catch_rates", {}).get("event", 0.0),
            "mutated": 0.02 * bait.get("catch_rates", {}).get("mutated", 0.0)
        }
        
        # Apply rod multiplier
        rod_mult = rod.get("multiplier", 1.0)
        chances = {k: v * rod_mult for k, v in base_chances.items()}
        
        # Determine catch
        roll = random.random()
        cumulative = 0
        caught_type = "normal"  # Default to normal if no catch
        
        for fish_type, chance in chances.items():
            cumulative += chance
            if roll <= cumulative:
                caught_type = fish_type
                break
                
        # Generate fish data
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
        
        # Add to inventory
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

    @commands.group(name="fish_shop", aliases=["fshop"], invoke_without_command=True)
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def fish_shop(self, ctx):
        """View the fishing shops"""
        shops = {
            "rod": {"name": "Rod Shop", "icon": "🎣", "cmd": "rod"},
            "bait": {"name": "Bait Shop", "icon": "🪱", "cmd": "bait"},
            "fish": {"name": "Fish Market", "icon": "🐟", "cmd": "market"}
        }
        
        embed = discord.Embed(
            title="Fishing Shops",
            description="Choose a shop to browse:",
            color=discord.Color.blue()
        )
        
        for shop_id, shop in shops.items():
            embed.add_field(
                name=f"{shop['icon']} {shop['name']}",
                value=f"Use `.fish_shop {shop['cmd']}` to view",
                inline=True
            )
            
        await ctx.reply(embed=embed)

    @fish_shop.command(name="rod", aliases=["rods"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def rod_shop(self, ctx):
        """View available fishing rods"""
        shop_data = await self.get_shop_items("rod_shop", ctx.guild.id if ctx.guild else None)
        if "rod_shop" not in shop_data:
            return await ctx.reply("❌ Rod shop is currently unavailable!")
            
        pages = []
        rods = shop_data["rod_shop"]
        
        # Create pages
        for rod_id, rod in rods.items():
            pages.append(discord.Embed(
                title="🎣 Fishing Rod Shop",
                description=f"Your Balance: **{await db.get_wallet_balance(ctx.author.id)}** {self.currency}",
                color=discord.Color.blue()
            ).add_field(
                name=f"{rod['name']} - {rod['price']} {self.currency}",
                value=f"{rod['description']}\nMultiplier: {rod['multiplier']}x\n`buy {rod_id}` to purchase",
                inline=False
            ))
            
        if not pages:
            return await ctx.reply("No rods available!")
            
        view = HelpPaginator(pages, ctx.author)
        view.update_buttons()
        message = await ctx.reply(embed=pages[0], view=view)
        view.message = message

    @fish_shop.command(name="bait", aliases=["baits"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def bait_shop(self, ctx):
        """View available fishing bait"""
        shop_data = await self.get_shop_items("bait_shop", ctx.guild.id if ctx.guild else None)
        if "bait_shop" not in shop_data:
            return await ctx.reply("❌ Bait shop is currently unavailable!")
            
        pages = []
        baits = shop_data["bait_shop"]
        
        # Create pages
        for bait_id, bait in baits.items():
            embed = discord.Embed(
                title="🪱 Fishing Bait Shop",
                description=f"Your Balance: **{await db.get_wallet_balance(ctx.author.id)}** {self.currency}",
                color=discord.Color.blue()
            )
            
            # Calculate catch rates text
            rates = []
            for fish_type, rate in bait.get("catch_rates", {}).items():
                if rate > 0:
                    rates.append(f"{fish_type.title()}: {int(rate * 100)}%")
                    
            embed.add_field(
                name=f"{bait['name']} - {bait['price']} {self.currency}",
                value=f"{bait['description']}\n" \
                      f"Amount: {bait['amount']} per purchase\n" \
                      f"Catch Rates: {', '.join(rates)}\n" \
                      f"`buy {bait_id}` to purchase",
                inline=False
            )
            pages.append(embed)
            
        if not pages:
            return await ctx.reply("No bait available!")
            
        view = HelpPaginator(pages, ctx.author)
        view.update_buttons()
        message = await ctx.reply(embed=pages[0], view=view)
        view.message = message

    @commands.command(name="fish_inv", aliases=["finv"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def fish_inventory(self, ctx):
        """View your fishing inventory and fish collection"""
        fishing_items = await db.get_fishing_items(ctx.author.id)
        fish = await db.get_fish(ctx.author.id)
        
        pages = []
        
        # Equipment page
        equip_embed = discord.Embed(
            title="🎣 Fishing Equipment",
            color=discord.Color.blue()
        )
        
        # Show rods
        rods_text = ""
        for rod in fishing_items["rods"]:
            rods_text += f"**{rod['name']}**\n" \
                        f"• Multiplier: {rod['multiplier']}x\n" \
                        f"• {rod['description']}\n\n"
        equip_embed.add_field(
            name="🎣 Fishing Rods",
            value=rods_text or "No rods",
            inline=False
        )
        
        # Show bait
        bait_text = ""
        for bait in fishing_items["bait"]:
            bait_text += f"**{bait['name']}** (x{bait.get('amount', 1)})\n" \
                        f"• {bait['description']}\n\n"
        equip_embed.add_field(
            name="🪱 Bait",
            value=bait_text or "No bait",
            inline=False
        )
        
        pages.append(equip_embed)
        
        # Fish collection pages
        if fish:
            # Group fish by type
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
                
                # Show some sample fish
                for fish in sorted(fish_list, key=lambda x: x["value"], reverse=True)[:5]:
                    embed.add_field(
                        name=f"{fish['name']} ({fish['value']} {self.currency})",
                        value=f"Caught: {fish['caught_at'].split('T')[0]}",
                        inline=False
                    )
                    
                pages.append(embed)
        else:
            # No fish page
            pages.append(discord.Embed(
                title="🐟 Fish Collection",
                description="You haven't caught any fish yet!\nUse `.fish` to start fishing.",
                color=discord.Color.blue()
            ))
            
        view = HelpPaginator(pages, ctx.author)
        view.update_buttons()
        message = await ctx.reply(embed=pages[0], view=view)
        view.message = message

    @commands.command(name="sell_fish", aliases=["sellf"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def sell_fish(self, ctx, fish_id: str = "all"):
        """Sell fish from your inventory"""
        fish = await db.get_fish(ctx.author.id)
        if not fish:
            return await ctx.reply("You don't have any fish to sell!")
            
        if fish_id.lower() == "all":
            # Sell all fish
            total_value = sum(f["value"] for f in fish)
            if await db.update_balance(ctx.author.id, total_value):
                # Remove all fish
                result = await self.db.users.update_one(
                    {"_id": str(ctx.author.id)},
                    {"$set": {"fish": []}}
                )
                if result.modified_count > 0:
                    embed = discord.Embed(
                        title="🐟 Fish Sold!",
                        description=f"Sold {len(fish)} fish for **{total_value}** {self.currency}",
                        color=discord.Color.green()
                    )
                    return await ctx.reply(embed=embed)
            await ctx.reply("❌ Failed to sell fish!")
        else:
            # Sell specific fish
            fish_to_sell = next((f for f in fish if f["id"] == fish_id), None)
            if not fish_to_sell:
                return await ctx.reply("❌ Fish not found in your inventory!")
                
            if await db.update_balance(ctx.author.id, fish_to_sell["value"]):
                # Remove the fish
                result = await self.db.users.update_one(
                    {"_id": str(ctx.author.id)},
                    {"$pull": {"fish": {"id": fish_id}}}
                )
                if result.modified_count > 0:
                    embed = discord.Embed(
                        title="🐟 Fish Sold!",
                        description=f"Sold {fish_to_sell['name']} for **{fish_to_sell['value']}** {self.currency}",
                        color=discord.Color.green()
                    )
                    return await ctx.reply(embed=embed)
            await ctx.reply("❌ Failed to sell fish!")
    
    async def debug_user_state(self, ctx, user_id: int):
        """Debug helper to check user's database state"""
        try:
            # Check user document
            user_doc = await db.db.users.find_one({"_id": str(user_id)})
            
            if not user_doc:
                await ctx.reply("❌ User document not found in database")
                return
                
            # Check inventory
            inventory = user_doc.get('inventory', [])
            inventory_items = [item.get('name', item.get('id', 'unknown')) for item in inventory]
            
            embed = discord.Embed(title="🔍 User Debug Info", color=0x3498db)
            embed.add_field(name="User ID", value=str(user_id), inline=True)
            embed.add_field(name="Document Exists", value="✅ Yes", inline=True)
            embed.add_field(name="Inventory Count", value=len(inventory), inline=True)
            embed.add_field(name="Inventory Items", value="\n".join(inventory_items) if inventory_items else "Empty", inline=False)
            
            # Check for interest token specifically
            has_interest_token = any(item.get('id') == 'interest_token' for item in inventory)
            embed.add_field(name="Has Interest Token", value="✅ Yes" if has_interest_token else "❌ No", inline=True)
            
            await ctx.reply(embed=embed)
            
        except Exception as e:
            await ctx.reply(f"❌ Debug error: {e}")

    async def debug_item_lookup(self, ctx, item_id: str):
        """Debug helper to check item in shop databases"""
        try:
            item = await self._find_item_in_shops(item_id)
            
            if not item:
                await ctx.reply(f"❌ Item `{item_id}` not found in any shop")
                return
                
            embed = discord.Embed(title=f"🔍 Item Debug: {item_id}", color=0x3498db)
            embed.add_field(name="Name", value=item.get('name', 'N/A'), inline=True)
            embed.add_field(name="Price", value=f"{item.get('price', 0):,}", inline=True)
            embed.add_field(name="Shop Type", value=item.get('_shop_type', 'unknown'), inline=True)
            embed.add_field(name="Item Type", value=item.get('type', 'N/A'), inline=True)
            embed.add_field(name="Multiple Purchase", value="✅ Yes" if self._item_supports_multiple(item) else "❌ No", inline=True)
            
            # Show item data without json formatting
            item_data = []
            for key, value in item.items():
                if not key.startswith('_'):
                    item_data.append(f"{key}: {value}")
            
            if item_data:
                embed.add_field(name="Item Data", value="```\n" + "\n".join(item_data[:10]) + "```", inline=False)
            
            await ctx.reply(embed=embed)
            
        except Exception as e:
            await ctx.reply(f"❌ Debug error: {e}")

    # Add these as commands for debugging
    @commands.command(hidden=True)
    @commands.is_owner()  
    async def debug_user(self, ctx, user_id: int = None):
        """Debug user database state"""
        if not user_id:
            user_id = ctx.author.id
        await self.debug_user_state(ctx, user_id)

    @commands.command(hidden=True) 
    @commands.is_owner() 
    async def debug_item(self, ctx, item_id: str):
        """Debug item configuration"""
        await self.debug_item_lookup(ctx, item_id)

class InventorySelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="All Items", value="all", description="Show all items", emoji="📦"),
            discord.SelectOption(label="Potions", value="potion", description="Show only potions", emoji="🧪"),
            discord.SelectOption(label="Consumables", value="consumable", description="Show only consumables", emoji="🍖"),
            discord.SelectOption(label="Collectibles", value="collectible", description="Show only collectibles", emoji="🎨")
        ]
        super().__init__(placeholder="Filter items...", options=options, custom_id="filter_select")

    async def callback(self, interaction: discord.Interaction):
        # Get parent view for access to inventory data
        view: InventoryView = self.view
        
        if interaction.user != view.author:
            return await interaction.response.send_message("This isn't your inventory!", ephemeral=True)

        try:
            await interaction.response.defer()
            
            filter_type = self.values[0]
            items = view.all_items
            
            if filter_type != "all":
                items = [item for item in items if item.get("type") == filter_type]
            
            # Create pages from filtered items
            pages = []
            chunks = [items[i:i+6] for i in range(0, len(items), 6)]
            
            for chunk in chunks:
                embed = discord.Embed(
                    title=f"🎒 {interaction.user.name}'s Inventory",
                    color=interaction.user.color or discord.Color.blue()
                )
                
                for item in chunk:
                    name = f"{item.get('name', 'Unknown Item')}"
                    if item.get("type") == "potion":
                        name = f"🧪 {name}"
                    elif item.get("type") == "consumable":
                        name = f"🍖 {name}"
                    elif item.get("type") == "collectible":
                        name = f"🎨 {name}"
                        
                    value = f"ID: `{item.get('id')}`\n"
                    if item.get("type") == "potion":
                        value += f"Effect: {item.get('multiplier')}x {item.get('buff_type')} for {item.get('duration')}min\n"
                    value += item.get("description", "No description")
                    
                    embed.add_field(name=name, value=value, inline=False)
                
                embed.set_footer(text=f"Filter: {filter_type.title()}")
                pages.append(embed)
            
            if not pages:
                embed = discord.Embed(
                    title=f"🎒 {interaction.user.name}'s Inventory",
                    description=f"No {filter_type} items found!",
                    color=interaction.user.color or discord.Color.blue()
                )
                pages = [embed]

            # Update paginator
            view.pages = pages
            view.current_page = 0
            view.update_buttons()
            await interaction.message.edit(embed=pages[0], view=view)
            
        except Exception as e:
            await interaction.followup.send("An error occurred while filtering inventory!", ephemeral=True)

class InventoryView(HelpPaginator):
    def __init__(self, pages: list, author: discord.Member, all_items: list):
        super().__init__(pages, author)
        self.all_items = all_items
        self.add_item(InventorySelect())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.author:
            await interaction.response.send_message("This isn't your inventory!", ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(view=self)
        except discord.NotFound:
            pass

async def setup(bot):
    await bot.add_cog(Economy(bot))