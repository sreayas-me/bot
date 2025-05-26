import discord
import random
import asyncio
import datetime
from discord.ext import commands
from cogs.logging.logger import CogLogger
from utils.db import db
from cogs.Help import HelpPaginator
from utils.betting import parse_bet

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

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = CogLogger(self.__class__.__name__)
        self.currency = "💰"
        self.active_games = set()  # Remove ongoing_jackpots set
        
        # Slot machine configuration
        self.SLOT_EMOJIS = ["🍒", "🍋", "🍊", "🍇", "7️⃣", "💎"]
        self.SLOT_VALUES = {"🍒": 2, "🍋": 3, "🍊": 4, "🍇": 5, "7️⃣": 10, "💎": 15}
        self.SLOT_WEIGHTS = [30, 25, 20, 15, 8, 2]

        # Shop items configuration
        self.SHOP_ITEMS = {
            "vip": {"name": "VIP Status", "price": 10000, "description": "Exclusive VIP role"},
            "color": {"name": "Custom Color", "price": 5000, "description": "Custom role color"},
            "title": {"name": "Custom Title", "price": 7500, "description": "Custom role name"},
            "badge": {"name": "Rich Badge", "price": 25000, "description": "Special rich person badge"}
        }
        self.CARD_VALUES = {
            "A": 11, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7,
            "8": 8, "9": 9, "10": 10, "J": 10, "Q": 10, "K": 10
        }
        self.CARD_SUITS = ["♠", "♥", "♦", "♣"]

    async def cog_before_invoke(self, ctx):
        """Check if user has an active game"""
        if ctx.command.name in ['slots', 'slotbattle', 'rollfight', 'rps', 'blackjack']:
            if ctx.author.id in self.active_games:
                raise commands.CommandError("You already have an active game!")
            self.active_games.add(ctx.author.id)

    async def cog_after_invoke(self, ctx):
        """Remove user from active games"""
        self.active_games.discard(ctx.author.id)

    @commands.command(name="deposit", aliases=["dep"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def deposit(self, ctx, amount: str = None):
        """Deposit money into your bank"""
        if not amount:
            wallet = await db.get_wallet_balance(ctx.author.id, ctx.guild.id)
            bank = await db.get_bank_balance(ctx.author.id, ctx.guild.id)
            limit = await db.get_bank_limit(ctx.author.id, ctx.guild.id)
            space = limit - bank
            
            embed = discord.Embed(
                description=(
                    "**Bank Deposit Guide**\n\n"
                    f"Your Wallet: **{wallet}** 💰\n"
                    f"Bank Space: **{space}** 💰\n\n"
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

        # Parse amount
        if amount.lower() in ['all', 'max']:
            amount = min(wallet, space)
        elif amount.endswith('%'):
            try:
                percentage = float(amount[:-1])
                if not 0 < percentage <= 100:
                    return await ctx.reply("Percentage must be between 0 and 100!")
                amount = min(round((percentage / 100) * wallet), space)
            except ValueError:
                return await ctx.reply("Invalid percentage!")
        else:
            try:
                amount = int(amount)
                if amount > space:
                    return await ctx.reply(f"Your bank can only hold {space} more coins!")
            except ValueError:
                return await ctx.reply("Invalid amount!")

        if amount <= 0:
            return await ctx.reply("Amount must be positive!")
        if amount > wallet:
            return await ctx.reply("You don't have that much in your wallet!")

        # Update balances
        if await db.update_wallet(ctx.author.id, -amount, ctx.guild.id):
            if await db.update_bank(ctx.author.id, amount, ctx.guild.id):
                await ctx.reply(f"Deposited **{amount}** 💰 into your bank!")
                return
            await db.update_wallet(ctx.author.id, amount, ctx.guild.id)  # Refund if bank update fails

        await ctx.reply("Failed to deposit money!")

    @commands.command(name="withdraw", aliases=["with"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def withdraw(self, ctx, amount: str = None):
        """Withdraw money from your bank"""
        if not amount:
            wallet = await db.get_wallet_balance(ctx.author.id, ctx.guild.id)
            bank = await db.get_bank_balance(ctx.author.id, ctx.guild.id)
            
            embed = discord.Embed(
                description=(
                    "**Bank Withdrawal Guide**\n\n"
                    f"Your Bank: **{bank}** 💰\n"
                    f"Your Wallet: **{wallet}** 💰\n\n"
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

        # Parse amount
        if amount.lower() in ['all', 'max']:
            amount = bank
        elif amount.endswith('%'):
            try:
                percentage = float(amount[:-1])
                if not 0 < percentage <= 100:
                    return await ctx.reply("Percentage must be between 0 and 100!")
                amount = round((percentage / 100) * bank)
            except ValueError:
                return await ctx.reply("Invalid percentage!")
        else:
            try:
                amount = int(amount)
            except ValueError:
                return await ctx.reply("Invalid amount!")

        if amount <= 0:
            return await ctx.reply("Amount must be positive!")
        if amount > bank:
            return await ctx.reply("You don't have that much in your bank!")

        # Update balances
        if await db.update_bank(ctx.author.id, -amount, ctx.guild.id):
            if await db.update_wallet(ctx.author.id, amount, ctx.guild.id):
                await ctx.reply(f"Withdrew **{amount}** 💰 from your bank!")
                return
            await db.update_bank(ctx.author.id, amount, ctx.guild.id)  # Refund if wallet update fails

        await ctx.reply("Failed to withdraw money!")

    @commands.command(aliases=['bal'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def balance(self, ctx, member: discord.Member = None):
        """Check your balance or someone else's"""
        member = member or ctx.author
        wallet = await db.get_wallet_balance(member.id, ctx.guild.id)
        bank = await db.get_bank_balance(member.id, ctx.guild.id)
        
        embed = discord.Embed(
            title=f"{member.display_name}'s Balance",
            description=f"Wallet: **{wallet:,}** 💰\n" \
                       f"Bank: **{bank:,}** 💰\n" \
                       f"Net Worth: **{wallet + bank:,}** 💰",
            color=member.color or discord.Color.green()
        )
        await ctx.reply(embed=embed)

    @commands.command(name="pay", aliases=["transfer"])
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

    @commands.command(aliases=['slot'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def slots(self, ctx, bet_amount: str = "10"):
        """Play the slot machine"""
        balance = await db.get_user_balance(ctx.author.id, ctx.guild.id)
        bet, error = parse_bet(bet_amount, balance)
        
        if error:
            return await ctx.reply(error)
        
        if bet < 10:
            return await ctx.reply("Minimum bet is 10!")
            
        if bet > balance:
            return await ctx.reply("Insufficient funds!")
        
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
        else:  # No matches
            winnings = 0
            result = "Better luck next time!"
        
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
        await db.update_balance(ctx.author.id, amount, ctx.guild.id)
        await ctx.reply(f"Daily reward claimed! +**{amount}** {self.currency}")

    @commands.command()
    @commands.cooldown(1, 3600, commands.BucketType.user)
    async def work(self, ctx):
        """Work for some money"""
        amount = random.randint(50, 200)
        await db.update_wallet(ctx.author.id, amount, ctx.guild.id)
        await ctx.reply(f"You worked and earned **{amount}** 💰")

    @commands.command()
    @commands.cooldown(1, 300, commands.BucketType.user)
    async def rob(self, ctx, victim: discord.Member):
        """Attempt to rob someone"""
        if victim == ctx.author:
            return await ctx.reply("You can't rob yourself!")
        
        victim_bal = await db.get_user_balance(victim.id, ctx.guild.id)
        if victim_bal < 100:
            return await ctx.reply("They're too poor to rob!")
        
        chance = random.random()
        if chance < 0.6:  # 60% chance to fail
            fine = random.randint(50, 200)
            await db.update_balance(ctx.author.id, -fine, ctx.guild.id)
            return await ctx.reply(f"You got caught and paid **{fine}** {self.currency} in fines!")
        
        stolen = random.randint(50, min(victim_bal, 500))
        await db.update_balance(victim.id, -stolen, ctx.guild.id)
        await db.update_balance(ctx.author.id, stolen, ctx.guild.id)
        await ctx.reply(f"You stole **{stolen}** {self.currency} from {victim.mention}!")

    @commands.command(aliases=['lb'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def leaderboard(self, ctx):
        """View the richest users"""
        users = await db.db.economy.find().sort('balance', -1).limit(10).to_list(10)
        
        content = ["🏆 **Richest Users**\n"]
        for i, user in enumerate(users, 1):
            member = ctx.guild.get_member(user['_id'])
            if member:
                content.append(f"`#{i}` {member.mention}: **{user['balance']}** {self.currency}")
        
        embed = discord.Embed(
            description="\n".join(content),
            color=discord.Color.gold()
        )
        await ctx.reply(embed=embed)

    @commands.command(aliases=['ghop', 'globalb', 'gtop', 'globaltop', 'glb'])
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def globalboard(self, ctx):
        """View global leaderboard across all servers (excludes small servers and admin servers)"""
        # Get valid servers (30+ members, user not admin)
        valid_servers = []
        excluded_guilds = []
        total_servers = 0
        
        for guild in self.bot.guilds:
            total_servers += 1
            if len(guild.members) < 30:
                excluded_guilds.append(guild.id)
                continue
                
            member = guild.get_member(ctx.author.id)
            if member and member.guild_permissions.administrator:
                excluded_guilds.append(guild.id)
                continue
                
            valid_servers.append(guild)
        
        if not valid_servers:
            return await ctx.reply("No eligible servers found for global leaderboard!")

        # Get global net worth for all users
        user_totals = {}
        for guild in valid_servers:
            for member in guild.members:
                if member.bot:
                    continue
                    
                if member.id not in user_totals:
                    net_worth = await db.get_global_net_worth(member.id, excluded_guilds)
                    if net_worth > 0:  # Only include users with money
                        user_totals[member.id] = {
                            "name": str(member),
                            "total": net_worth
                        }

        # Sort users by total
        sorted_users = sorted(user_totals.items(), key=lambda x: x[1]["total"], reverse=True)[:10]

        if not sorted_users:
            return await ctx.reply("No users found with money in eligible servers!")

        # Create leaderboard embed
        embed = discord.Embed(
            title="🌎 Global Economy Leaderboard",
            color=discord.Color.gold()
        )
        
        embed.description = f"**Eligible Servers:** {len(valid_servers)}/{total_servers}\n" \
                          f"*Excludes servers with <30 members and servers where you're admin*\n\n"
        
        for i, (user_id, data) in enumerate(sorted_users, 1):
            embed.description += f"`#{i}` {data['name']}: **{data['total']:,}** 💰\n"

        await ctx.reply(embed=embed)

    @commands.command(aliases=['ghop'])
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
            description=f"🛍️ **Global Shop**\n\nYour Balance: **{await db.get_wallet_balance(ctx.author.id)}** {self.currency}\n\n"
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
    async def buy(self, ctx, item_id: str):
        """Buy an item from the shop"""
        if item_id not in self.SHOP_ITEMS:
            return await ctx.reply("Invalid item! Use `shop` to see available items.")
        
        item = self.SHOP_ITEMS[item_id]
        if not await db.update_balance(ctx.author.id, -item['price'], ctx.guild.id):
            return await ctx.reply("Insufficient funds!")
        
        # Handle special items
        if item_id == "vip":
            role = await ctx.guild.create_role(
                name="VIP",
                color=discord.Color.gold(),
                reason=f"VIP role purchased by {ctx.author}"
            )
            await ctx.author.add_roles(role)
        elif item_id == "color":
            try:
                await ctx.author.send("Reply with a hex color code (e.g., #FF0000)")
                color_msg = await self.bot.wait_for(
                    'message',
                    check=lambda m: m.author == ctx.author and m.channel.type == discord.ChannelType.private,
                    timeout=30
                )
                color = await commands.ColorConverter().convert(ctx, color_msg.content)
                role = await ctx.guild.create_role(
                    name=f"{ctx.author.name}'s Color",
                    color=color,
                    reason=f"Custom color purchased by {ctx.author}"
                )
                await ctx.author.add_roles(role)
            except:
                await db.update_balance(ctx.author.id, item['price'], ctx.guild.id)  # Refund
                return await ctx.reply("Color selection failed. You've been refunded.")
        
        await ctx.reply(f"Successfully purchased **{item['name']}**!")

    @commands.command(aliases=['cf'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def coinflip(self, ctx, bet_amount: str, choice: str):
        """Bet on a coinflip (heads/tails)"""
        balance = await db.get_user_balance(ctx.author.id, ctx.guild.id)
        bet, error = parse_bet(bet_amount, balance)
        
        if error:
            return await ctx.reply(error)
        
        if bet < 10:
            return await ctx.reply("Minimum bet is 10!")
        
        if choice.lower() not in ['heads', 'tails', 'h', 't']:
            return await ctx.reply("Choose either 'heads' or 'tails'!")
        
        if not await db.update_balance(ctx.author.id, -bet, ctx.guild.id):
            return await ctx.reply("Insufficient funds!")
        
        result = random.choice(['heads', 'tails'])
        user_choice = choice[0].lower()
        
        if (user_choice == 'h' and result == 'heads') or (user_choice == 't' and result == 'tails'):
            winnings = bet * 2
            await db.update_balance(ctx.author.id, winnings, ctx.guild.id)
            await ctx.reply(f"It's **{result}**! You won **{winnings}** {self.currency}!")
        else:
            await ctx.reply(f"It's **{result}**! You lost **{bet}** {self.currency}!")

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

        # Deduct initial bet
        await db.update_balance(ctx.author.id, -bet, ctx.guild.id)

        def calculate_hand(hand):
            total = 0
            aces = 0
            for card in hand:
                if card == 1:  # Ace
                    aces += 1
                else:
                    total += min(card, 10)
            
            # Handle aces
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
            can_split = (len(hand) == 2 and 
                        min(hand[0], 10) == min(hand[1], 10) and 
                        len(player_hands) < 4 and 
                        await db.get_user_balance(ctx.author.id, ctx.guild.id) >= bet)

            # Check for double down option
            can_double = (len(hand) == 2 and 
                         not doubled[current_hand] and 
                         await db.get_user_balance(ctx.author.id, ctx.guild.id) >= bet)

            # Show game state
            embed = discord.Embed(
                title="Blackjack Game",
                description=(
                    f"**Dealer's Hand:** {dealer_cards}\n"
                    f"**Your Hand {current_hand + 1}:** {player_cards} (Total: {player_total})\n"
                    f"**Current Bet:** {bet}\n\n"
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
                return (m.author == ctx.author and 
                        m.channel == ctx.channel and 
                        m.content.lower() in valid_actions)

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
                    # Double the bet
                    if not await db.update_balance(ctx.author.id, -bet, ctx.guild.id):
                        await ctx.send("Not enough money to double down!")
                        continue
                    
                    bet *= 2
                    hand.append(random.randint(1, 13))
                    doubled[current_hand] = True
                    current_hand += 1

                elif action in ['split', 'sp'] and can_split:
                    # Split the hand
                    if not await db.update_balance(ctx.author.id, -bet, ctx.guild.id):
                        await ctx.send("Not enough money to split!")
                        continue
                    
                    new_hand = [hand.pop()]
                    hand.append(random.randint(1, 13))
                    new_hand.append(random.randint(1, 13))
                    player_hands.append(new_hand)
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
            hand_bet = bet * 2 if doubled[i] else bet
            
            if player_total > 21:
                result = "Bust"
                winnings = -hand_bet
            elif dealer_total > 21 or player_total > dealer_total:
                result = "Win"
                winnings = hand_bet
            elif player_total < dealer_total:
                result = "Lose"
                winnings = -hand_bet
            else:
                result = "Push"
                winnings = 0
            
            total_winnings += winnings
            results.append(f"Hand {i + 1}: {' '.join(format_card(c) for c in hand)} ({player_total}) - {result}")

        # Update balance
        if total_winnings > 0:
            await db.update_balance(ctx.author.id, total_winnings, ctx.guild.id)

        # Show final results
        embed = discord.Embed(
            title="Blackjack Results",
            description=(
                f"**Dealer's Hand:** {dealer_cards} (Total: {dealer_total})\n\n" +
                "\n".join(results) + "\n\n" +
                f"**Total {'Winnings' if total_winnings >= 0 else 'Loss'}:** {abs(total_winnings)}"
            ),
            color=discord.Color.green() if total_winnings > 0 else discord.Color.red()
        )
        await ctx.send(embed=embed)

    @commands.command(invoke_without_command=True)
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def shop(self, ctx):
        """View the server's shop"""
        # Get shop data
        guild_shop = self.get_server_shop(ctx.guild.id)
        
        # Display shop using Admin cog's display method
        admin_cog = self.bot.get_cog('Admin')
        if admin_cog:
            await admin_cog.display_shop(ctx, guild_shop, title="Server Shop")
        else:
            await ctx.send("Shop system is currently unavailable.")

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def globalshop(self, ctx):
        """View the global shop"""
        admin_cog = self.bot.get_cog('Admin')
        if admin_cog:
            await admin_cog.display_shop(ctx, admin_cog.shop_data, title="Global Shop")
        else:
            await ctx.send("Shop system is currently unavailable.")

def setup(bot):
    bot.add_cog(Economy(bot))