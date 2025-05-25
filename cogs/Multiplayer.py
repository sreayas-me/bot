import discord
import random
import asyncio
import logging
from discord.ext import commands
from typing import Dict, List, Optional, Tuple, Union

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

class GameError(Exception):
    """Custom exception for game-related errors"""
    pass

class Multiplayer(commands.Cog):
    """Multiplayer gaming commands for Discord"""
    
    def __init__(self, bot):
        self.bot = bot
        self.ongoing_jackpots = set()
        self.active_games = set()  # Track all active games to prevent duplicates
        
        # Game constants
        self.SLOT_EMOJIS = ["🍒", "🍋", "🍊", "🍇", "7️⃣", "💎"]
        self.SLOT_VALUES = {"🍒": 10, "🍋": 20, "🍊": 30, "🍇": 50, "7️⃣": 100, "💎": 200}
    
    def _create_embed(self, description: str, color: discord.Color = discord.Color.blue()) -> discord.Embed:
        """Helper to create consistent embeds"""
        return discord.Embed(description=description, color=color)
    
    async def _validate_opponent(self, ctx, opponent: Optional[discord.Member], game_name: str) -> bool:
        """Validate opponent for multiplayer games"""
        if not opponent:
            await ctx.reply(embed=self._create_embed(
                f"You need to mention someone to challenge them to {game_name}!",
                discord.Color.red()
            ))
            return False
        
        if opponent == ctx.author:
            await ctx.reply(embed=self._create_embed(
                "You can't play against yourself!", discord.Color.red()
            ))
            return False
        
        if opponent.bot:
            await ctx.reply(embed=self._create_embed(
                f"Bots can't play {game_name}!", discord.Color.red()
            ))
            return False
        
        game_key = f"{min(ctx.author.id, opponent.id)}-{max(ctx.author.id, opponent.id)}"
        if game_key in self.active_games:
            await ctx.reply(embed=self._create_embed(
                "You already have an active game with this player!", discord.Color.red()
            ))
            return False
        
        return True
    
    async def _get_challenge_acceptance(self, ctx, opponent: discord.Member, game_name: str, timeout: int = 30) -> bool:
        """Handle challenge acceptance logic"""
        game_key = f"{min(ctx.author.id, opponent.id)}-{max(ctx.author.id, opponent.id)}"
        self.active_games.add(game_key)
        
        try:
            challenge_embed = self._create_embed(
                f"🎮 **{opponent.mention}**, {ctx.author.mention} challenged you to {game_name}!\n"
                f"React with ✅ to accept within {timeout} seconds!"
            )
            challenge_msg = await ctx.send(embed=challenge_embed)
            await challenge_msg.add_reaction("✅")

            def check(reaction, user):
                return (user == opponent and str(reaction.emoji) == "✅" and 
                       reaction.message.id == challenge_msg.id)

            await self.bot.wait_for("reaction_add", timeout=timeout, check=check)
            await challenge_msg.delete()
            return True
            
        except asyncio.TimeoutError:
            await ctx.send(embed=self._create_embed(
                f"⌛ {opponent.mention} didn't accept the challenge in time.",
                discord.Color.red()
            ))
            return False
        finally:
            self.active_games.discard(game_key)

    @commands.command(aliases=['jp'])
    async def jackpot(self, ctx):
        """Start a jackpot! $25 entry, winner takes all. React with 🎉 to join within 15 seconds."""
        if ctx.channel.id in self.ongoing_jackpots:
            return await ctx.reply(embed=self._create_embed(
                "🚨 A jackpot is already running in this channel!", discord.Color.red()
            ))
        
        self.ongoing_jackpots.add(ctx.channel.id)
        
        try:
            embed = self._create_embed(
                f"🎰 **JACKPOT STARTED!** 🎰\n"
                f"Hosted by: {ctx.author.mention}\n"
                f"Entry: **$25**\n"
                f"React with 🎉 within **15 seconds** to join!\n\n"
                f"Current pot: **$25** (1 player)",
                discord.Color.gold()
            )
            jackpot_msg = await ctx.send(embed=embed)
            await jackpot_msg.add_reaction("🎉")
            
            participants = [ctx.author]
            await asyncio.sleep(15)
            
            try:
                jackpot_msg = await ctx.channel.fetch_message(jackpot_msg.id)
                reaction = next((r for r in jackpot_msg.reactions if str(r.emoji) == "🎉"), None)
                
                if reaction:
                    async for user in reaction.users():
                        if not user.bot and user not in participants:
                            participants.append(user)
                
                if len(participants) == 1:
                    return await ctx.send(embed=self._create_embed(
                        f"❌ Only {ctx.author.mention} joined. Refunded $25.", discord.Color.red()
                    ))
                
                pot = len(participants) * 25
                winner = random.choice(participants)
                win_chance = 25 / pot * 100
                
                await ctx.send(embed=self._create_embed(
                    f"🎉 **JACKPOT RESULTS** 🎉\n"
                    f"Total entries: **{len(participants)}**\n"
                    f"Total pot: **${pot}**\n"
                    f"Winner: {winner.mention} (had a **{win_chance:.1f}%** chance)\n\n"
                    f"🏆 **{winner.display_name} takes ALL!** 🏆",
                    discord.Color.green()
                ))
                
            except discord.NotFound:
                await ctx.send(embed=self._create_embed(
                    "❌ Jackpot message was deleted. Game cancelled.", discord.Color.red()
                ))
        finally:
            self.ongoing_jackpots.discard(ctx.channel.id)

    @commands.command(aliases=['slotfight', 'slotsduel', 'sb'])
    async def slotbattle(self, ctx, opponent: discord.Member = None):
        """Challenge someone to a slot battle! Winner takes all, or the house wins if both lose."""
        if not await self._validate_opponent(ctx, opponent, "a slot battle"):
            return
        
        if not await self._get_challenge_acceptance(ctx, opponent, "SLOT BATTLE"):
            return

        async def get_slot_result(player: discord.Member) -> Dict:
            """Generate slot result for a player"""
            slots = [random.choice(self.SLOT_EMOJIS) for _ in range(3)]
            result = " | ".join(slots)
            
            if slots[0] == slots[1] == slots[2]:  # Triple match
                win_amount = self.SLOT_VALUES[slots[0]] * 10
                win_status = "**JACKPOT!**"
            elif slots[0] == slots[1] or slots[1] == slots[2]:  # Double match
                win_amount = self.SLOT_VALUES[slots[1]] * 2
                win_status = "**Winner!**"
            else:
                win_amount = 0
                win_status = "Lost"
            
            return {
                "name": player.display_name,
                "result": result,
                "win_amount": win_amount,
                "win_status": win_status
            }

        # Spinning animation
        spin_frames = ["🎰 Spinning...", "🎰 Spinning...", "🎰 Final results!"]
        msg = await ctx.send(embed=self._create_embed(spin_frames[0]))
        
        for i in range(1, len(spin_frames)):
            await asyncio.sleep(1.5)
            await msg.edit(embed=self._create_embed(spin_frames[i]))

        # Get final results
        p1_result, p2_result = await asyncio.gather(
            get_slot_result(ctx.author),
            get_slot_result(opponent)
        )
        
        total_pot = p1_result["win_amount"] + p2_result["win_amount"]
        
        # Determine outcome
        if p1_result["win_amount"] > p2_result["win_amount"]:
            outcome = f"🏆 **{p1_result['name']} WINS ${total_pot}!**"
            color = discord.Color.green()
        elif p2_result["win_amount"] > p1_result["win_amount"]:
            outcome = f"🏆 **{p2_result['name']} WINS ${total_pot}!**"
            color = discord.Color.green()
        elif p1_result["win_amount"] > 0:
            outcome = f"🤝 **Tie! Both win ${p1_result['win_amount']}.**"
            color = discord.Color.blue()
        else:
            outcome = "🏦 **The house wins! Both players lose.**"
            color = discord.Color.red()

        result_embed = self._create_embed(
            f"**{p1_result['name']}**\n🎰 {p1_result['result']} ({p1_result['win_status']})\n"
            f"**{p2_result['name']}**\n🎰 {p2_result['result']} ({p2_result['win_status']})\n\n"
            f"{outcome}",
            color
        )
        await msg.edit(embed=result_embed)

    @commands.command(aliases=['dicebattle', 'db'])
    async def rollfight(self, ctx, opponent: discord.Member = None):
        """Challenge someone to a dice duel (highest roll wins)"""
        if not await self._validate_opponent(ctx, opponent, "a dice battle"):
            return
        
        if not await self._get_challenge_acceptance(ctx, opponent, "DICE BATTLE"):
            return

        p1_roll, p2_roll = random.randint(1, 100), random.randint(1, 100)
        
        if p1_roll == p2_roll:
            result = "**It's a tie!**"
            color = discord.Color.gold()
        else:
            winner = ctx.author.display_name if p1_roll > p2_roll else opponent.display_name
            result = f"🏆 **{winner} wins!**"
            color = discord.Color.green()
        
        await ctx.send(embed=self._create_embed(
            f"**{ctx.author.display_name}**: {p1_roll}\n"
            f"**{opponent.display_name}**: {p2_roll}\n\n{result}",
            color
        ))

    @commands.command(aliases=['21game', '21'])
    async def twentyone(self, ctx, opponent: discord.Member = None):
        """Take turns counting to 21 (who says 21 loses)"""
        if not await self._validate_opponent(ctx, opponent, "a game of 21"):
            return
        
        if not await self._get_challenge_acceptance(ctx, opponent, "21"):
            return

        current = 0
        players = [ctx.author, opponent]
        turn = 0
        
        await ctx.send(embed=self._create_embed("Type `1`, `2`, or `3` to add that number to the count"))
        
        while current < 21:
            player = players[turn % 2]
            await ctx.send(embed=self._create_embed(
                f"Current count: **{current}**\n**{player.display_name}'s turn**"
            ))
            
            def check(m):
                return (m.author == player and m.channel == ctx.channel and 
                       m.content in ['1', '2', '3'])
            
            try:
                msg = await self.bot.wait_for('message', check=check, timeout=30)
                current += int(msg.content)
                turn += 1
            except asyncio.TimeoutError:
                return await ctx.send(embed=self._create_embed(
                    f"{player.display_name} took too long!", discord.Color.red()
                ))
        
        loser = players[(turn - 1) % 2]
        await ctx.send(embed=self._create_embed(
            f"💀 **{loser.display_name} said 21 and loses!**", discord.Color.red()
        ))

    @commands.command(aliases=['rps3', 'rps'])
    async def rockpaperscissors3(self, ctx, opponent: discord.Member = None, games: int = 3):
        """Best 2 out of 3 rock-paper-scissors"""
        if not await self._validate_opponent(ctx, opponent, f"best of {games} RPS"):
            return
        
        if not await self._get_challenge_acceptance(ctx, opponent, f"BEST OF {games} RPS"):
            return

        wins = {ctx.author: 0, opponent: 0}
        choices = ['rock', 'paper', 'scissors']
        win_conditions = {
            ('rock', 'scissors'): True, ('paper', 'rock'): True, ('scissors', 'paper'): True
        }
        
        for round_num in range(1, games + 1):
            await ctx.send(embed=self._create_embed(f"**Round {round_num}** - First to 2 wins"))
            
            async def get_choice(player):
                await player.send(embed=self._create_embed(
                    f"Choose for round {round_num}: `rock`, `paper`, or `scissors`"
                ))
                def check(m):
                    return (m.author == player and isinstance(m.channel, discord.DMChannel) and 
                           m.content.lower() in choices)
                resp = await self.bot.wait_for('message', check=check, timeout=30)
                return resp.content.lower()
            
            try:
                p1_choice, p2_choice = await asyncio.gather(
                    get_choice(ctx.author), get_choice(opponent)
                )
            except asyncio.TimeoutError:
                return await ctx.send(embed=self._create_embed(
                    "Someone didn't choose in time", discord.Color.red()
                ))
            
            # Determine round winner
            if p1_choice == p2_choice:
                result = "**Tie!**"
                color = discord.Color.gold()
            elif win_conditions.get((p1_choice, p2_choice)):
                wins[ctx.author] += 1
                result = f"**{ctx.author.display_name} wins round {round_num}!**"
                color = discord.Color.green()
            else:
                wins[opponent] += 1
                result = f"**{opponent.display_name} wins round {round_num}!**"
                color = discord.Color.green()
            
            await ctx.send(embed=self._create_embed(
                f"{ctx.author.display_name}: {p1_choice}\n"
                f"{opponent.display_name}: {p2_choice}\n\n{result}\n"
                f"Score: {wins[ctx.author]}-{wins[opponent]}",
                color
            ))
            
            if max(wins.values()) >= 2:
                break
        
        overall_winner = max(wins, key=wins.get)
        await ctx.send(embed=self._create_embed(
            f"🏆 **{overall_winner.display_name} wins the match!**", discord.Color.green()
        ))

    @commands.command(aliases=['yacht', 'yd'])
    async def yachtdice(self, ctx, opponent: discord.Member = None):
        """Play a simplified Yacht dice game"""
        if not await self._validate_opponent(ctx, opponent, "yacht dice"):
            return
        
        if not await self._get_challenge_acceptance(ctx, opponent, "YACHT DICE"):
            return

        async def play_round(player):
            rolls = [random.randint(1, 6) for _ in range(5)]
            total = sum(rolls)
            await player.send(embed=self._create_embed(
                f"Your dice: {' '.join(f'`{r}`' for r in rolls)}\nTotal: {total}"
            ))
            return total
        
        p1_score, p2_score = await asyncio.gather(
            play_round(ctx.author), play_round(opponent)
        )
        
        if p1_score == p2_score:
            result = "**It's a tie!**"
            color = discord.Color.gold()
        else:
            winner = ctx.author if p1_score > p2_score else opponent
            result = f"🏆 **{winner.display_name} wins!**"
            color = discord.Color.green()
        
        await ctx.send(embed=self._create_embed(
            f"{ctx.author.display_name}: {p1_score}\n"
            f"{opponent.display_name}: {p2_score}\n\n{result}",
            color
        ))

    @commands.command(aliases=['bj'])
    async def blackjack(self, ctx, opponent: discord.Member = None):
        """Play simplified Blackjack against someone"""
        if not await self._validate_opponent(ctx, opponent, "blackjack"):
            return
        
        if not await self._get_challenge_acceptance(ctx, opponent, "BLACKJACK"):
            return

        def calculate_hand(hand: List[int]) -> int:
            """Calculate blackjack hand value with ace handling"""
            total = sum(min(card, 10) for card in hand)
            aces = hand.count(1)
            while aces > 0 and total + 10 <= 21:
                total += 10
                aces -= 1
            return total
        
        def draw_card() -> int:
            return random.randint(1, 13)
        
        hands = {
            ctx.author: [draw_card(), draw_card()],
            opponent: [draw_card(), draw_card()]
        }
        
        # Send initial hands to players
        for player, hand in hands.items():
            total = calculate_hand(hand)
            await player.send(embed=self._create_embed(
                f"Your hand: {' '.join(f'`{c}`' for c in hand)}\nTotal: {total}"
            ))
        
        # Player turns
        for player in hands:
            await ctx.send(embed=self._create_embed(f"{player.mention}'s turn - type `hit` or `stand`"))
            
            while True:
                def check(m):
                    return (m.author == player and m.channel == ctx.channel and 
                           m.content.lower() in ['hit', 'stand', 'h', 's'])
                
                try:
                    msg = await self.bot.wait_for('message', check=check, timeout=30)
                    if msg.content.lower() in ['stand', 's']:
                        break
                    
                    new_card = draw_card()
                    hands[player].append(new_card)
                    total = calculate_hand(hands[player])
                    
                    await player.send(embed=self._create_embed(f"New card: `{new_card}`\nTotal: {total}"))
                    
                    if total > 21:
                        await ctx.send(embed=self._create_embed(
                            f"💥 **{player.display_name} busts!**", discord.Color.red()
                        ))
                        break
                        
                except asyncio.TimeoutError:
                    await ctx.send(embed=self._create_embed(
                        f"⌛ {player.display_name} took too long!", discord.Color.red()
                    ))
                    break
        
        # Calculate results
        results = {player: calculate_hand(hand) for player, hand in hands.items()}
        valid_scores = {k: v for k, v in results.items() if v <= 21}
        
        if not valid_scores:
            result = "💥 **Both players busted!**"
            color = discord.Color.red()
        else:
            winner = max(valid_scores.items(), key=lambda x: x[1])[0]
            result = f"🏆 **{winner.display_name} wins!**"
            color = discord.Color.green()
        
        await ctx.send(embed=self._create_embed(
            f"{ctx.author.display_name}: {results[ctx.author]}\n"
            f"{opponent.display_name}: {results[opponent]}\n\n{result}",
            color
        ))

async def setup(bot):
    try:
        await bot.add_cog(Multiplayer(bot))
        logger.info("Multiplayer cog loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load Multiplayer cog: {e}")
        raise e