import discord
import random
import json
from discord.ext import commands
import logging
import asyncio
import math
from pathlib import Path
import os
from fractions import Fraction

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('data/logs/Multiplayer.log')
    ]
)
logger = logging.getLogger('Multiplayer')

class Multiplayer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ongoing_jackpots = set()

    @commands.command(aliases=['jp'])
    async def jackpot(self, ctx):
        """Start a jackpot! $25 entry, winner takes all. React with 🎉 to join within 15 seconds."""
        if ctx.channel.id in self.ongoing_jackpots:
            return await ctx.reply(embed=discord.Embed(
                description="🚨 A jackpot is already running in this channel!",
                color=discord.Color.red()
            ))
        
        self.ongoing_jackpots.add(ctx.channel.id)
        
        embed = discord.Embed(
            description=(
                f"🎰 **JACKPOT STARTED!** 🎰\n"
                f"Hosted by: {ctx.author.mention}\n"
                f"Entry: **$25**\n"
                f"React with 🎉 within **15 seconds** to join!\n\n"
                f"Current pot: **$25** (1 player)"
            ),
            color=discord.Color.gold()
        )
        jackpot_msg = await ctx.send(embed=embed)
        await jackpot_msg.add_reaction("🎉")
        
        participants = [ctx.author]
        
        await asyncio.sleep(15)
        self.ongoing_jackpots.discard(ctx.channel.id)
        
        try:
            jackpot_msg = await ctx.channel.fetch_message(jackpot_msg.id)
        except discord.NotFound:
            return await ctx.send(embed=discord.Embed(
                description="❌ Jackpot message was deleted. Game cancelled.",
                color=discord.Color.red()
            ))
        
        reaction = next((r for r in jackpot_msg.reactions if str(r.emoji) == "🎉"), None)
        if not reaction:
            return await ctx.send(embed=discord.Embed(
                description="❌ No one joined the jackpot. Game cancelled.",
                color=discord.Color.red()
            ))
        
        async for user in reaction.users():
            if not user.bot and user not in participants:
                participants.append(user)
        
        if len(participants) == 1:
            return await ctx.send(embed=discord.Embed(
                description=f"❌ Only {ctx.author.mention} joined. Refunded $25.",
                color=discord.Color.red()
            ))
        
        pot = len(participants) * 25
        winner = random.choice(participants)
        win_chance = 25 / pot * 100
        
        result_embed = discord.Embed(
            description=(
                f"🎉 **JACKPOT RESULTS** 🎉\n"
                f"Total entries: **{len(participants)}**\n"
                f"Total pot: **${pot}**\n"
                f"Winner: {winner.mention} (had a **{win_chance:.1f}%** chance)\n\n"
                f"🏆 **{winner.display_name} takes ALL!** 🏆"
            ),
            color=discord.Color.green()
        )
        await ctx.send(embed=result_embed)

    @commands.command(aliases=['slotfight', 'slotsduel', 'sb'])
    async def slotbattle(self, ctx, opponent: discord.Member = None):
        """Challenge someone to a slot battle! Winner takes all, or the house wins if both lose."""
        if not opponent:
            return await ctx.reply(embed=discord.Embed(
                description="You need to mention someone to challenge them to a slot battle!",
                color=discord.Color.red()
            ))
        if opponent == ctx.author:
            return await ctx.reply(embed=discord.Embed(
                description="You can't battle yourself!",
                color=discord.Color.red()
            ))
        if opponent.bot:
            return await ctx.reply(embed=discord.Embed(
                description="Bots can't play slots!",
                color=discord.Color.red()
            ))

        challenge_embed = discord.Embed(
            description=f"🎰 **{opponent.mention}**, {ctx.author.mention} challenged you to a SLOT BATTLE!\nReact with ✅ to accept within 30 seconds!",
            color=discord.Color.blue()
        )
        challenge_msg = await ctx.send(embed=challenge_embed)
        await challenge_msg.add_reaction("✅")

        def check(reaction, user):
            return (
                user == opponent and
                str(reaction.emoji) == "✅" and
                reaction.message.id == challenge_msg.id
            )

        try:
            await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            return await ctx.send(embed=discord.Embed(
                description=f"⌛ {opponent.mention} didn't accept the challenge in time.",
                color=discord.Color.red()
            ))
        await challenge_msg.delete()

        emojis = ["🍒", "🍋", "🍊", "🍇", "7️⃣", "💎"]
        values = {
            "🍒": 10, "🍋": 20, "🍊": 30, 
            "🍇": 50, "7️⃣": 100, "💎": 200
        }

        async def spinning_slots(player_name):
            frames = []
            for _ in range(3):
                frame = " | ".join([random.choice(emojis) for _ in range(3)])
                frames.append(f"**{player_name}**\n🎰 {frame}")
            return frames

        p1_frames = await spinning_slots(ctx.author.display_name)
        p2_frames = await spinning_slots(opponent.display_name)

        spin_embed = discord.Embed(
            description=f"{p1_frames[0]}\n{p2_frames[0]}\n```Spinning...```",
            color=discord.Color.blue()
        )
        msg = await ctx.send(embed=spin_embed)

        for i in range(1, 3):
            await asyncio.sleep(1.5)
            spin_embed.description = f"{p1_frames[i]}\n{p2_frames[i]}\n```Spinning...```"
            await msg.edit(embed=spin_embed)

        async def get_final_result(player):
            slots = [random.choice(emojis) for _ in range(3)]
            result = " | ".join(slots)
            
            if slots[0] == slots[1] == slots[2]:
                win_amount = values[slots[0]] * 10
                win_status = "**JACKPOT!**"
            elif slots[0] == slots[1] or slots[1] == slots[2]:
                win_amount = values[slots[1]] * 2
                win_status = "**Winner!**"
            else:
                win_amount = 0
                win_status = "Lost"
            
            return {
                "name": player.display_name,
                "slots": slots,
                "result": result,
                "win_amount": win_amount,
                "win_status": win_status,
                "display": f"**{player.display_name}**\n🎰 {result}"
            }

        results = await asyncio.gather(
            get_final_result(ctx.author),
            get_final_result(opponent)
        )
        player1, player2 = results
        total_pot = player1["win_amount"] + player2["win_amount"]

        if player1["win_amount"] > player2["win_amount"]:
            outcome = f"🏆 **{player1['name']} WINS ${total_pot}!**"
        elif player2["win_amount"] > player1["win_amount"]:
            outcome = f"🏆 **{player2['name']} WINS ${total_pot}!**"
        elif player1["win_amount"] > 0:
            outcome = f"🤝 **Tie! Both win ${player1['win_amount']}.**"
        else:
            outcome = "🏦 **The house wins! Both players lose.**"

        result_embed = discord.Embed(
            description=(
                f"{player1['display']} ({player1['win_status']})\n"
                f"{player2['display']} ({player2['win_status']})\n\n"
                f"{outcome}"
            ),
            color=discord.Color.green() if "WINS" in outcome else 
                discord.Color.blue() if "Tie" in outcome else 
                discord.Color.red()
        )
        await msg.edit(embed=result_embed)
    @commands.command(aliases=['dicebattle', 'db'])
    async def rollfight(self, ctx, opponent: discord.Member = None):
        """Challenge someone to a dice duel (highest roll wins)"""
        if not opponent:
            return await ctx.reply(embed=discord.Embed(
                description="You need to mention someone to challenge them to a dice battle!",
                color=discord.Color.red()
            ))
        if opponent == ctx.author:
            return await ctx.reply(embed=discord.Embed(
                description="You can't challenge yourself!",
                color=discord.Color.red()
            ))
        if opponent.bot:
            return await ctx.reply(embed=discord.Embed(
                description="Bots can't play dice games",
                color=discord.Color.red()
            ))
        
        embed = discord.Embed(
            description=f"🎲 **{opponent.mention}**, {ctx.author.mention} challenged you to a DICE BATTLE!\nReact with ✅ to accept within 30 seconds!",
            color=discord.Color.blue()
        )
        challenge_msg = await ctx.send(embed=embed)
        await challenge_msg.add_reaction("✅")

        def check(reaction, user):
            return (
                user == opponent and
                str(reaction.emoji) == "✅" and
                reaction.message.id == challenge_msg.id
            )

        try:
            await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            return await ctx.send(embed=discord.Embed(
                description=f"⌛ {opponent.mention} didn't accept the challenge in time",
                color=discord.Color.red()
            ))
        await challenge_msg.delete()

        rolls = {
            ctx.author: random.randint(1, 100),
            opponent: random.randint(1, 100)
        }
        winner = max(rolls, key=rolls.get)
        
        result_embed = discord.Embed(
            description=(
                f"**{ctx.author.display_name}**: {rolls[ctx.author]}\n"
                f"**{opponent.display_name}**: {rolls[opponent]}\n\n"
                f"🏆 **{winner.display_name} wins!**"
            ),
            color=discord.Color.green()
        )
        await ctx.send(embed=result_embed)

    @commands.command(aliases=['21game', '21'])
    async def twentyone(self, ctx, opponent: discord.Member = None):
        """Take turns counting to 21 (who says 21 loses)"""
        if not opponent:
            return await ctx.reply(embed=discord.Embed(
                description="You need to mention someone to challenge them to a game of 21!",
                color=discord.Color.red()
            ))
        elif opponent == ctx.author:
            return await ctx.reply(embed=discord.Embed(
                description="You can't play against yourself!",
                color=discord.Color.red()
            ))
        elif opponent.bot:
            return await ctx.reply(embed=discord.Embed(
                description="Bots can't count properly",
                color=discord.Color.red()
            ))

        embed = discord.Embed(
            description=f"🔢 **{opponent.mention}**, {ctx.author.mention} challenged you to 21!\nReact with ✅ to accept within 30 seconds!",
            color=discord.Color.blue()
        )
        challenge_msg = await ctx.send(embed=embed)
        await challenge_msg.add_reaction("✅")

        def check(reaction, user):
            return (
                user == opponent and
                str(reaction.emoji) == "✅" and
                reaction.message.id == challenge_msg.id
            )

        try:
            await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            return await ctx.send(embed=discord.Embed(
                description=f"⌛ {opponent.mention} didn't accept the challenge in time",
                color=discord.Color.red()
            ))
        await challenge_msg.delete()

        current = 0
        players = [ctx.author, opponent]
        turn = 0
        
        await ctx.send(embed=discord.Embed(
            description="Type `1`, `2`, or `3` to add that number to the count",
            color=discord.Color.blue()
        ))
        
        while current < 21:
            player = players[turn % 2]
            await ctx.send(embed=discord.Embed(
                description=f"Current count: **{current}**\n**{player.display_name}'s turn**",
                color=discord.Color.blue()
            ))
            
            def check(m):
                return (
                    m.author == player and
                    m.channel == ctx.channel and
                    m.content in ['1', '2', '3']
                )
            
            try:
                msg = await self.bot.wait_for('message', check=check, timeout=30)
                current += int(msg.content)
                turn += 1
            except asyncio.TimeoutError:
                return await ctx.send(embed=discord.Embed(
                    description=f"{player.display_name} took too long!",
                    color=discord.Color.red()
                ))
        
        loser = players[(turn - 1) % 2]
        await ctx.send(embed=discord.Embed(
            description=f"💀 **{loser.display_name} said 21 and loses!**",
            color=discord.Color.red()
        ))

    @commands.command(aliases=['rps3', 'rps'])
    async def rockpaperscissors3(self, ctx, opponent: discord.Member=None, games:int=3):
        """Best 2 out of 3 rock-paper-scissors"""
        if not opponent:
            return await ctx.reply(embed=discord.Embed(
                description=f"You need to mention someone to challenge them to a best out of {games} RPS!",
                color=discord.Color.red()
            ))
        if opponent == ctx.author:
            return await ctx.reply(embed=discord.Embed(
                description="You can't play against yourself!",
                color=discord.Color.red()
            ))
        if opponent.bot:
            return await ctx.reply(embed=discord.Embed(
                description="Bots can't play rock-paper-scissors",
                color=discord.Color.red()
            ))
        
        embed = discord.Embed(
            description=f"🪨 **{opponent.mention}**, {ctx.author.mention} challenged you to best of {games} RPS!\nReact with ✅ to accept within 30 seconds!",
            color=discord.Color.blue()
        )
        challenge_msg = await ctx.send(embed=embed)
        await challenge_msg.add_reaction("✅")

        def check(reaction, user):
            return (
                user == opponent and
                str(reaction.emoji) == "✅" and
                reaction.message.id == challenge_msg.id
            )

        try:
            await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            return await ctx.send(embed=discord.Embed(
                description=f"⌛ {opponent.mention} didn't accept the challenge in time",
                color=discord.Color.red()
            ))
        await challenge_msg.delete()

        wins = {ctx.author: 0, opponent: 0}
        choices = ['rock', 'paper', 'scissors']
        
        for round_num in range(1, games+1):
            round_embed = discord.Embed(
                description=f"**Round {round_num}** - First to 2 wins",
                color=discord.Color.blue()
            )
            await ctx.send(embed=round_embed)
            
            async def get_choice(player):
                await player.send(embed=discord.Embed(
                    description=f"Choose for round {round_num}: `rock`, `paper`, or `scissors`",
                    color=discord.Color.blue()
                ))
                def check(m):
                    return (
                        m.author == player and
                        isinstance(m.channel, discord.DMChannel) and
                        m.content.lower() in choices
                    )
                resp = await self.bot.wait_for('message', check=check, timeout=30)
                return resp.content.lower()
            
            try:
                p1_choice = await get_choice(ctx.author)
                p2_choice = await get_choice(opponent)
            except asyncio.TimeoutError:
                return await ctx.send(embed=discord.Embed(
                    description="Someone didn't choose in time",
                    color=discord.Color.red()
                ))
            
            if p1_choice == p2_choice:
                result = "**Tie!**"
                color = discord.Color.gold()
            elif (p1_choice == 'rock' and p2_choice == 'scissors') or \
                (p1_choice == 'paper' and p2_choice == 'rock') or \
                (p1_choice == 'scissors' and p2_choice == 'paper'):
                wins[ctx.author] += 1
                result = f"**{ctx.author.display_name} wins round {round_num}!**"
                color = discord.Color.green()
            else:
                wins[opponent] += 1
                result = f"**{opponent.display_name} wins round {round_num}!**"
                color = discord.Color.green()
            
            result_embed = discord.Embed(
                description=(
                    f"{ctx.author.display_name}: {p1_choice}\n"
                    f"{opponent.display_name}: {p2_choice}\n\n"
                    f"{result}\n"
                    f"Score: {wins[ctx.author]}-{wins[opponent]}"
                ),
                color=color
            )
            await ctx.send(embed=result_embed)
            
            if max(wins.values()) >= 2:
                break
        
        overall_winner = max(wins, key=wins.get)
        await ctx.send(embed=discord.Embed(
            description=f"🏆 **{overall_winner.display_name} wins the match!**",
            color=discord.Color.green()
        ))

    @commands.command(aliases=['yacht', 'yd'])
    async def yachtdice(self, ctx, opponent: discord.Member=None):
        """Play a simplified Yacht dice game"""
        if not opponent:
            return await ctx.reply(embed=discord.Embed(
                description="You need to mention someone to challenge them to a yacht dice game!",
                color=discord.Color.red()
            ))
        if opponent.bot:
            return await ctx.reply(embed=discord.Embed(
                description="Bots can't handle dice math",
                color=discord.Color.red()
            ))
        if opponent == ctx.author:
            return await ctx.reply(embed=discord.Embed(
                description="You can't play against yourself!",
                color=discord.Color.red()
            ))
        
        embed = discord.Embed(
            description=f"🎲 **{opponent.mention}**, {ctx.author.mention} challenged you to Yacht Dice!\nReact with ✅ to accept within 30 seconds!",
            color=discord.Color.blue()
        )
        challenge_msg = await ctx.send(embed=embed)
        await challenge_msg.add_reaction("✅")

        def check(reaction, user):
            return (
                user == opponent and
                str(reaction.emoji) == "✅" and
                reaction.message.id == challenge_msg.id
            )

        try:
            await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            return await ctx.send(embed=discord.Embed(
                description=f"⌛ {opponent.mention} didn't accept the challenge in time",
                color=discord.Color.red()
            ))
        await challenge_msg.delete()

        async def play_round(player):
            rolls = [random.randint(1, 6) for _ in range(5)]
            await player.send(embed=discord.Embed(
                description=f"Your dice: {' '.join(f'`{r}`' for r in rolls)}\nTotal: {sum(rolls)}",
                color=discord.Color.blue()
            ))
            return sum(rolls)
        
        p1_score = await play_round(ctx.author)
        p2_score = await play_round(opponent)
        
        if p1_score == p2_score:
            result_embed = discord.Embed(
                description=(
                    f"{ctx.author.display_name}: {p1_score}\n"
                    f"{opponent.display_name}: {p2_score}\n\n"
                    "**It's a tie!**"
                ),
                color=discord.Color.gold()
            )
        else:
            winner = ctx.author if p1_score > p2_score else opponent
            result_embed = discord.Embed(
                description=(
                    f"{ctx.author.display_name}: {p1_score}\n"
                    f"{opponent.display_name}: {p2_score}\n\n"
                    f"🏆 **{winner.display_name} wins!**"
                ),
                color=discord.Color.green()
            )
        
        await ctx.send(embed=result_embed)

    @commands.command(aliases=['bj'])
    async def blackjack(self, ctx, opponent: discord.Member=None):
        """Play simplified Blackjack against someone"""
        if not opponent:
            return await ctx.reply(embed=discord.Embed(
                description="You need to mention someone to challenge them in blackjack!",
                color=discord.Color.red()
            ))
        if opponent == ctx.author:
            return await ctx.reply(embed=discord.Embed(
                description="You can't play against yourself!",
                color=discord.Color.red()
            ))
        if opponent.bot:
            return await ctx.reply(embed=discord.Embed(
                description="Bots don't gamble",
                color=discord.Color.red()
            ))
        
        embed = discord.Embed(
            description=f"🃏 **{opponent.mention}**, {ctx.author.mention} challenged you to Blackjack!\nReact with ✅ to accept within 30 seconds!",
            color=discord.Color.blue()
        )
        challenge_msg = await ctx.send(embed=embed)
        await challenge_msg.add_reaction("✅")

        def check(reaction, user):
            return (
                user == opponent and
                str(reaction.emoji) == "✅" and
                reaction.message.id == challenge_msg.id
            )

        try:
            await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            return await ctx.send(embed=discord.Embed(
                description=f"⌛ {opponent.mention} didn't accept the challenge in time",
                color=discord.Color.red()
            ))
        await challenge_msg.delete()

        async def calculate_hand(hand):
            total = sum(min(card, 10) for card in hand)
            if 1 in hand and total <= 11:
                total += 10
            return total
        
        def draw_card():
            return random.randint(1, 13)
        
        hands = {
            ctx.author: [draw_card(), draw_card()],
            opponent: [draw_card(), draw_card()]
        }
        
        for player in hands:
            total = await calculate_hand(hands[player])
            await player.send(embed=discord.Embed(
                description=f"Your hand: {' '.join(f'`{c}`' for c in hands[player])}\nTotal: {total}",
                color=discord.Color.blue()
            ))
        
        for player in hands:
            await ctx.send(embed=discord.Embed(
                description=f"{player.mention}'s turn - type `hit` or `stand`",
                color=discord.Color.blue()
            ))
            while True:
                def check(m):
                    return m.author == player and m.channel == ctx.channel and m.content.lower() in ['hit', 'stand', 'h', 's']
                
                try:
                    msg = await self.bot.wait_for('message', check=check, timeout=30)
                    if msg.content.lower() in ['stand', 's']:
                        break
                    
                    hands[player].append(draw_card())
                    total = await calculate_hand(hands[player])
                    await player.send(embed=discord.Embed(
                        description=f"New card: `{hands[player][-1]}`\nTotal: {total}",
                        color=discord.Color.blue()
                    ))
                    
                    if total > 21:
                        await ctx.send(embed=discord.Embed(
                            description=f"💥 **{player.display_name} busts!**",
                            color=discord.Color.red()
                        ))
                        break
                except asyncio.TimeoutError:
                    await ctx.send(embed=discord.Embed(
                        description=f"⌛ {player.display_name} took too long!",
                        color=discord.Color.red()
                    ))
                    break
        
        results = {}
        for player in hands:
            results[player] = await calculate_hand(hands[player])
        
        valid_scores = {k: v for k, v in results.items() if v <= 21}
        if not valid_scores:
            result_embed = discord.Embed(
                description="💥 **Both players busted!**",
                color=discord.Color.red()
            )
        else:
            winner = max(valid_scores.items(), key=lambda x: x[1])
            result_embed = discord.Embed(
                description=(
                    f"{ctx.author.display_name}: {results[ctx.author]}\n"
                    f"{opponent.display_name}: {results[opponent]}\n\n"
                    f"🏆 **{winner[0].display_name} wins!**"
                ),
                color=discord.Color.green()
            )
        
        await ctx.send(embed=result_embed)

async def setup(bot):
    try:
        await bot.add_cog(Multiplayer(bot))
        logger.info("Multiplayer cog loaded successfully")

    except Exception as e:
        logger.error(f"Failed to load Multiplayer cog: {e}")
        raise e