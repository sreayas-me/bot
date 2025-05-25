import discord
import random
import asyncio
import datetime
from discord.ext import commands
from cogs.logging.logger import CogLogger
from utils.db import db
from cogs.Help import HelpPaginator  # Add this import

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = CogLogger(self.__class__.__name__)
        self.currency = "💰"
        self.active_games = set()
        
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

    async def cog_before_invoke(self, ctx):
        """Check if user has an active game"""
        if ctx.command.name in ['slots', 'slotbattle', 'jackpot', 'rollfight', 'rps', 'blackjack']:
            if ctx.author.id in self.active_games:
                raise commands.CommandError("You already have an active game!")
            self.active_games.add(ctx.author.id)

    async def cog_after_invoke(self, ctx):
        """Remove user from active games"""
        self.active_games.discard(ctx.author.id)

    @commands.command(name="balance", aliases=["bal"])
    async def balance(self, ctx, member: discord.Member = None):
        """Check your balance or someone else's"""
        member = member or ctx.author
        balance = await db.get_user_balance(member.id)
        await ctx.reply(f"{member.mention}'s balance: **{balance}** {self.currency}")

    @commands.command(name="pay", aliases=["transfer"])
    async def pay(self, ctx, member: discord.Member, amount: int):
        """Transfer money to another user"""
        if amount <= 0:
            return await ctx.reply("Amount must be positive!")
        
        if member == ctx.author:
            return await ctx.reply("You can't pay yourself!")
        
        if await db.transfer_money(ctx.author.id, member.id, amount):
            await ctx.reply(f"Transferred **{amount}** {self.currency} to {member.mention}")
        else:
            await ctx.reply("Insufficient funds!")

    @commands.command(aliases=['slot'])
    async def slots(self, ctx, bet: int = 10):
        """Play the slot machine"""
        if bet < 10:
            return await ctx.reply("Minimum bet is 10!")
            
        if not await db.update_balance(ctx.author.id, -bet):
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
        
        await db.update_balance(ctx.author.id, winnings)
        
        embed = discord.Embed(
            description=f"🎰 {display}\n\n{result}\n\nBet: **{bet}**\nWon: **{winnings}**",
            color=discord.Color.green() if winnings > 0 else discord.Color.red()
        )
        await msg.edit(content=None, embed=embed)

    @commands.command()
    @commands.cooldown(1, 86400, commands.BucketType.user)
    async def daily(self, ctx):
        """Claim your daily reward"""
        amount = random.randint(100, 500)
        await db.update_balance(ctx.author.id, amount)
        await ctx.reply(f"Daily reward claimed! +**{amount}** {self.currency}")

    @commands.command()
    @commands.cooldown(1, 3600, commands.BucketType.user)
    async def work(self, ctx):
        """Work for some money"""
        jobs = [
            "You wrote some code for a client",
            "You fixed a bug",
            "You designed a website",
            "You moderated a server",
            "You helped someone with their homework"
        ]
        amount = random.randint(50, 200)
        await db.update_balance(ctx.author.id, amount)
        await ctx.reply(f"{random.choice(jobs)}! +**{amount}** {self.currency}")

    @commands.command()
    @commands.cooldown(1, 300, commands.BucketType.user)
    async def rob(self, ctx, victim: discord.Member):
        """Attempt to rob someone"""
        if victim == ctx.author:
            return await ctx.reply("You can't rob yourself!")
        
        victim_bal = await db.get_user_balance(victim.id)
        if victim_bal < 100:
            return await ctx.reply("They're too poor to rob!")
        
        chance = random.random()
        if chance < 0.6:  # 60% chance to fail
            fine = random.randint(50, 200)
            await db.update_balance(ctx.author.id, -fine)
            return await ctx.reply(f"You got caught and paid **{fine}** {self.currency} in fines!")
        
        stolen = random.randint(50, min(victim_bal, 500))
        await db.update_balance(victim.id, -stolen)
        await db.update_balance(ctx.author.id, stolen)
        await ctx.reply(f"You stole **{stolen}** {self.currency} from {victim.mention}!")

    @commands.command(aliases=['lb'])
    async def leaderboard(self, ctx):
        """View the richest users"""
        users = await db.db.economy.find().sort('balance', -1).limit(10).to_list(10)
        
        embed = discord.Embed(title="🏆 Richest Users", color=discord.Color.gold())
        
        for i, user in enumerate(users, 1):
            member = ctx.guild.get_member(user['_id'])
            if member:
                embed.add_field(
                    name=f"#{i} {member.display_name}",
                    value=f"**{user['balance']}** {self.currency}",
                    inline=False
                )
        
        await ctx.reply(embed=embed)

    @commands.command()
    async def shop(self, ctx):
        """View available items in the shop"""
        pages = []
        
        # Overview page
        overview = discord.Embed(
            title="🛍️ Shop Overview",
            description=f"Welcome to the shop! Use the buttons below to browse categories.\n\n"
                       f"**Available Categories:**\n"
                       f"• Roles and Colors\n"
                       f"• Badges and Status\n"
                       f"• Special Items\n\n"
                       f"Your Balance: **{await db.get_user_balance(ctx.author.id)}** {self.currency}",
            color=discord.Color.blue()
        )
        pages.append(overview)
        
        # Split items into pages of 4 items each
        items = list(self.SHOP_ITEMS.items())
        for i in range(0, len(items), 4):
            page_items = items[i:i+4]
            embed = discord.Embed(
                title="🛍️ Shop Items",
                color=discord.Color.blue()
            )
            
            for item_id, item in page_items:
                embed.add_field(
                    name=f"{item['name']} - {item['price']} {self.currency}",
                    value=f"{item['description']}\nUse `buy {item_id}` to purchase",
                    inline=False
                )
                
            embed.set_footer(text=f"Your Balance: {await db.get_user_balance(ctx.author.id)} {self.currency}")
            pages.append(embed)
        
        # Create and send paginator
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
        if not await db.update_balance(ctx.author.id, -item['price']):
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
                await db.update_balance(ctx.author.id, item['price'])  # Refund
                return await ctx.reply("Color selection failed. You've been refunded.")
        
        await ctx.reply(f"Successfully purchased **{item['name']}**!")

    @commands.command(aliases=['cf'])
    async def coinflip(self, ctx, bet: int, choice: str):
        """Bet on a coinflip (heads/tails)"""
        if bet < 10:
            return await ctx.reply("Minimum bet is 10!")
        
        if choice.lower() not in ['heads', 'tails', 'h', 't']:
            return await ctx.reply("Choose either 'heads' or 'tails'!")
        
        if not await db.update_balance(ctx.author.id, -bet):
            return await ctx.reply("Insufficient funds!")
        
        result = random.choice(['heads', 'tails'])
        user_choice = choice[0].lower()
        
        if (user_choice == 'h' and result == 'heads') or (user_choice == 't' and result == 'tails'):
            winnings = bet * 2
            await db.update_balance(ctx.author.id, winnings)
            await ctx.reply(f"It's **{result}**! You won **{winnings}** {self.currency}!")
        else:
            await ctx.reply(f"It's **{result}**! You lost **{bet}** {self.currency}!")

async def setup(bot):
    await bot.add_cog(Economy(bot))