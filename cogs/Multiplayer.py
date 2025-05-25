import discord
import random
import json
from discord.ext import commands
import logging
import asyncio

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

    @commands.command(aliases=['dicebattle'])
    async def rollfight(self, ctx, opponent: discord.Member):
        """Challenge someone to a dice duel (highest roll wins)

        Usage: .rollfight [user]
        """
        if opponent == ctx.author:
            return await ctx.reply("```you can't challenge yourself```")
        if opponent.bot:
            return await ctx.reply("```bots can't play dice games```")
        
        rolls = {
            ctx.author: random.randint(1, 100),
            opponent: random.randint(1, 100)
        }
        winner = max(rolls, key=rolls.get)
        
        result = (
            f"```{ctx.author.display_name}: {rolls[ctx.author]}\n"
            f"{opponent.display_name}: {rolls[opponent]}```\n"
            f"🏆 `{winner.display_name} wins!`"
        )
        await ctx.reply(result)
    
    @commands.command(aliases=['21game'])
    async def twentyone(self, ctx, opponent: discord.Member):
        """Take turns counting to 21 (who says 21 loses)

        Usage: .twentyone [user]
        """
        if opponent == ctx.author:
            return await ctx.reply("```you can't play against yourself```")
        if opponent.bot:
            return await ctx.reply("```bots can't count properly```")
        
        current = 0
        players = [ctx.author, opponent]
        turn = 0
        
        await ctx.reply("```type 1, 2, or 3 to add that number```")
        
        while current < 21:
            player = players[turn % 2]
            await ctx.send(f"`{current}`\n**{player.display_name}'s turn**")
            
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
                return await ctx.reply(f"```{player.display_name} took too long!```")
        
        loser = players[(turn - 1) % 2]
        await ctx.reply(f"💀 `{loser.display_name} said 21 and loses!`")
    
    @commands.command(aliases=['rps3'])
    async def rockpaperscissors3(self, ctx, opponent: discord.Member):
        """Best 2 out of 3 rock-paper-scissors

        Usage: .rockpaperscissors3 [user]
        """
        if opponent == ctx.author:
            return await ctx.reply("```you can't play against yourself```")
        
        wins = {ctx.author: 0, opponent: 0}
        choices = ['rock', 'paper', 'scissors']
        
        for round_num in range(1, 4):
            await ctx.reply(f"```round {round_num} - first to 2 wins```")
            
            # Get both players' choices simultaneously
            async def get_choice(player):
                await player.send(f"```choose for round {round_num}: rock/paper/scissors```")
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
                return await ctx.reply("```someone didn't choose in time```")
            
            # Determine winner
            if p1_choice == p2_choice:
                result = "`tie!`"
            elif (p1_choice == 'rock' and p2_choice == 'scissors') or \
                (p1_choice == 'paper' and p2_choice == 'rock') or \
                (p1_choice == 'scissors' and p2_choice == 'paper'):
                wins[ctx.author] += 1
                result = f"`{ctx.author.display_name} wins round {round_num}!`"
            else:
                wins[opponent] += 1
                result = f"`{opponent.display_name} wins round {round_num}!`"
            
            await ctx.reply(
                f"```{ctx.author.display_name}: {p1_choice}\n"
                f"{opponent.display_name}: {p2_choice}```\n"
                f"{result}\n"
                f"```score: {wins[ctx.author]}-{wins[opponent]}```"
            )
            
            if max(wins.values()) >= 2:
                break
        
        overall_winner = max(wins, key=wins.get)
        await ctx.reply(f"🏆 `{overall_winner.display_name} wins the match!`")

    @commands.command(aliases=['yacht'])
    async def yachtdice(self, ctx, opponent: discord.Member):
        """Play a simplified Yacht dice game

        Usage: .yachtdice [user]"""
        if opponent.bot:
            return await ctx.reply("```bots can't handle dice math```")
        
        async def play_round(player):
            rolls = [random.randint(1, 6) for _ in range(5)]
            await player.send(f"```your dice: {' '.join(map(str, rolls))}```")
            return sum(rolls)
        
        p1_score = await play_round(ctx.author)
        p2_score = await play_round(opponent)
        
        result = (
            f"```{ctx.author.display_name}: {p1_score}\n"
            f"{opponent.display_name}: {p2_score}```\n"
        )
        
        if p1_score == p2_score:
            result += "`it's a tie!`"
        else:
            winner = ctx.author if p1_score > p2_score else opponent
            result += f"🏆 `{winner.display_name} wins!`"
        
        await ctx.reply(result)

    @commands.command(aliases=['21'])
    async def blackjack(self, ctx, opponent: discord.Member):
        """Play simplified Blackjack against someone

        Usage: .blackjack [user]"""
        if opponent == ctx.author:
            return await ctx.reply("```you can't play against yourself```")
        if opponent.bot:
            return await ctx.reply("```bots don't gamble```")
        
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
            await player.send(f"```your hand: {hands[player]} ({total})```")
        
        # Players take turns
        for player in hands:
            await ctx.send(f"{player.mention}'s turn")
            while True:
                def check(m):
                    return m.author == player and m.channel == ctx.channel and m.content.lower() in ['hit', 'stand']
                
                try:
                    msg = await self.bot.wait_for('message', check=check, timeout=30)
                    if msg.content.lower() == 'stand':
                        break
                    
                    hands[player].append(draw_card())
                    total = await calculate_hand(hands[player])
                    await player.send(f"```new card: {hands[player][-1]}\ntotal: {total}```")
                    
                    if total > 21:
                        await ctx.send(f"```{player.display_name} busts!```")
                        break
                except asyncio.TimeoutError:
                    await ctx.send(f"```{player.display_name} took too long!```")
                    break
        
        # Determine winner
        results = {}
        for player in hands:
            results[player] = await calculate_hand(hands[player])
        
        valid_scores = {k: v for k, v in results.items() if v <= 21}
        if not valid_scores:
            await ctx.reply("```both players busted!```")
        else:
            winner = max(valid_scores.items(), key=lambda x: x[1])
            await ctx.reply(
                f"```{ctx.author.display_name}: {results[ctx.author]}\n"
                f"{opponent.display_name}: {results[opponent]}```\n"
                f"🏆 `{winner[0].display_name} wins!`"
            )

    @commands.command(aliases=['mathduel'])
    async def mathrace(self, ctx, opponent: discord.Member, difficulty: int = 10):
        """Race to solve math problems

        Usage: .mathrace <user> [difficulty]"""
        ops = ['+', '-', '*']
        a = random.randint(1, difficulty)
        b = random.randint(1, difficulty)
        op = random.choice(ops)
        problem = f"{a} {op} {b}"
        answer = eval(problem)
        
        await ctx.reply(f"```solve this first: {problem}```")
        
        def check(m):
            return (
                m.author in [ctx.author, opponent] and
                m.channel == ctx.channel and
                m.content.isdigit() and
                int(m.content) == answer
            )
        
        try:
            msg = await self.bot.wait_for('message', check=check, timeout=15)
            await ctx.reply(f"🏆 `{msg.author.display_name} solved it first!`")
        except asyncio.TimeoutError:
            await ctx.reply(f"```time's up! answer was: {answer}```")

async def setup(bot):
    try:
        await bot.add_cog(Multiplayer(bot))
        logger.info("Multiplayer cog loaded successfully")

    except Exception as e:
        logger.error(f"Failed to load Multiplayer cog: {e}")
        raise e