import discord
import random
import json
from discord.ext import commands
import logging
import asyncio
import string
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('data/logs/fun.log')
    ]
)
logger = logging.getLogger('Fun')

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['mock'])
    async def spongebob(self, ctx, *, text):
        """mOcK sOme tExT"""
        result = ''.join([char.upper() if i % 2 == 0 else char.lower() for i, char in enumerate(text)])
        await ctx.reply(f"```{result}```")

    @commands.command(aliases=['choose'])
    async def pick(self, ctx, *options):
        """pick a random option

        Usage: pick [option1] [option2] ... [optionN]
        """
        if not options:
            return await ctx.reply("```provide some options to choose from```")
        await ctx.reply(f"```i choose: {random.choice(options)}```")

    @commands.command(aliases=['smallcaps'])
    async def tinytext(self, ctx, *, text: str):
        """convert to ᵗⁱⁿʸ ᶜᵃᵖˢ"""
        mapping = str.maketrans(
            'abcdefghijklmnopqrstuvwxyz',
            'ᵃᵇᶜᵈᵉᶠᵍʰⁱʲᵏˡᵐⁿᵒᵖᵠʳˢᵗᵘᵛʷˣʸᶻ'
        )
        await ctx.reply(f"```{text.lower().translate(mapping)}```")

    @commands.command(aliases=['textflip'])
    async def reverse(self, ctx, *, text: str):
        """ʇxǝʇ ǝsɹǝʌǝɹ"""
        await ctx.reply(f"```{text[::-1]}```")
    
    @commands.command(aliases=['8ball'])
    async def ball8(self, ctx, *, question: str):
        """ask the magic 8-ball"""
        responses = [
            "```it is certain```", "```no doubt```", "```nah```",
            "```maybe idk```", "```lol no```", "```ask again```"
        ]
        await ctx.reply(f"🎱 {random.choice(responses)}")

    @commands.command()
    async def rps(self, ctx, choice: str.lower):
        """rock paper scissors"""
        valid = ["rock", "paper", "scissors"]
        if choice not in valid:
            return await ctx.reply(f"```choose: {', '.join(valid)}```")
        
        bot_choice = random.choice(valid)
        results = {
            ("rock", "scissors"): "win",
            ("scissors", "paper"): "win",
            ("paper", "rock"): "win"
        }
        
        if choice == bot_choice:
            result = "```tie!```"
        else:
            result = "```you win!```" if (choice, bot_choice) in results else "```you lose!```"
        
        await ctx.reply(f"**{ctx.author.display_name}**: `{choice}`\n"
                        f"**bot**: `{bot_choice}`\n{result}")
    
    @commands.command(aliases=['owo'])
    async def owoify(self, ctx, *, text: str):
        """uwu-ify youw text owo"""
        replacements = {
            'r': 'w', 'l': 'w', 'R': 'W', 'L': 'W',
            'no': 'nyo', 'No': 'Nyo', 'NO': 'NYO',
            'ove': 'uv', '!': '! uwu'
        }
        for k, v in replacements.items():
            text = text.replace(k, v)
        await ctx.reply(f"```{text}```")

    @commands.command()
    async def emojify(self, ctx, *, text: str):
        """turn text into 🔥 emoji ✨ text"""
        emoji_map = {
            'a': '🇦', 'b': '🇧', 'c': '🇨', '...': '...',
            '1': '1️⃣', '!': '❗', '?': '❓'
        }
        result = ' '.join([emoji_map.get(c.lower(), c) for c in text])
        await ctx.reply(f"```{result}```")
    
    @commands.command()
    async def hack(self, ctx, user: discord.Member):
        """fake hack someone (joke)"""
        steps = [
            f"```breaching {user.name}'s firewall...```",
            "```installing backdoor... 32%```",
            "```stealing discord token...```",
            f"```success! {random.choice(['sent nudes to #general', 'changed status to \'I love bots\'', 'deleted all roles'])}```"
        ]
        msg = await ctx.reply(steps[0])
        for step in steps[1:]:
            await asyncio.sleep(1.5)
            await msg.edit(content=step)

    @commands.command(aliases=['ship'])
    async def lovecalc(self, ctx, user1: discord.Member, user2: discord.Member = None):
        """calculate love compatibility"""
        user2 = user2 or ctx.author
        score = (user1.id + user2.id) % 101  # Consistent based on user IDs
        emoji = "💔" if score < 30 else "❤️" if score < 70 else "💞"
        await ctx.reply(f"```{user1.display_name} {emoji} {user2.display_name}\ncompatibility: {score}%```")
    
    @commands.command()
    async def drake(self, ctx, *, text: str):
        """drake meme format (2 lines)"""
        if '\n' not in text:
            return await ctx.reply("```provide two lines separated by enter```")
        
        line1, line2 = text.split('\n', 1)
        async with self.bot.session.get(
            f"https://api.memegen.link/images/drake/"
            f"{line1.strip()}/{line2.strip()}.png?font=arial"
        ) as resp:
            if resp.status == 200:
                await ctx.reply(resp.url)
            else:
                await ctx.reply("```failed to generate meme```")
    
    @commands.command(aliases=['coin'])
    async def flip(self, ctx):
        """flip a coin"""
        result = random.choice(["```heads```", "```tails```"])
        await ctx.reply(f"🪙 {result}")

    @commands.command(aliases=['slots'])
    async def slotmachine(self, ctx):
        """Play slot machine with animations and payouts

        Possible payouts:
        🍒: 10
        🍋: 20
        🍊: 30
        🍇: 50
        7️⃣: 100
        💎: 200"""
        emojis = ["🍒", "🍋", "🍊", "🍇", "7️⃣", "💎"]
        values = {
            "🍒": 10,
            "🍋": 20,
            "🍊": 30,
            "🍇": 50,
            "7️⃣": 100,
            "💎": 200
        }
        
        # Initial spinning animation
        msg = await ctx.reply("🎰 | 🎰 | 🎰\n```Spinning...```")
        
        # First spin (partial animation)
        await asyncio.sleep(1)
        first_slot = random.choice(emojis)
        await msg.edit(content=f"🎰 | 🎰 | 🎰\n```Spinning... {first_slot}```")
        
        # Second spin (partial animation)
        await asyncio.sleep(1)
        second_slot = random.choice(emojis)
        await msg.edit(content=f"{first_slot} | 🎰 | 🎰\n```Spinning... {second_slot}```")
        
        # Final spin
        await asyncio.sleep(1)
        third_slot = random.choice(emojis)
        slots = [first_slot, second_slot, third_slot]
        result = " | ".join(slots)
        
        # Calculate winnings
        if slots[0] == slots[1] == slots[2]:
            outcome = "```JACKPOT!```"
            winnings = values[slots[0]] * 10  # 10x multiplier for jackpot
        elif slots[0] == slots[1] or slots[1] == slots[2] or slots[0] == slots[2]:
            outcome = "```Winner!```"
            # Find the matching pair
            if slots[0] == slots[1]:
                winnings = values[slots[0]] * 2
            elif slots[1] == slots[2]:
                winnings = values[slots[1]] * 2
            else:
                winnings = values[slots[0]] * 2
        else:
            outcome = "```You lost```"
            winnings = 0
        
        # Add payout information if won
        if winnings > 0:
            outcome += f"\nYou won ${winnings}!"
        
        await msg.edit(content=f"🎰 {result}\n{outcome}")
    
    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def trollvc(self, ctx, channel: discord.VoiceChannel):
        """rename VC repeatedly (requires perms)"""
        original = channel.name
        for _ in range(5):
            new = ''.join(random.choices(string.ascii_letters, k=10))
            await channel.edit(name=new)
            await asyncio.sleep(1)
        await channel.edit(name=original)
        await ctx.reply("```trolling complete```")

    @commands.command()
    async def guess(self, ctx, max_num: int = 100):
        """guess the number game"""
        num = random.randint(1, max_num)
        await ctx.reply(f"```guess a number between 1-{max_num} (type 'quit' to end)```")
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        tries = 0
        while True:
            try:
                msg = await self.bot.wait_for('message', check=check, timeout=30.0)
                if msg.content.lower() == 'quit':
                    return await ctx.reply(f"```game over. it was {num}```")
                
                guess = int(msg.content)
                tries += 1
                
                if guess == num:
                    return await ctx.reply(f"```correct! guesses: {tries}```")
                await ctx.reply("```too high```" if guess > num else "```too low```")
            except ValueError:
                await ctx.reply("```enter a number```")
            except asyncio.TimeoutError:
                return await ctx.reply(f"```timeout. it was {num}```")

    @commands.command(aliases=['ttt'])
    async def tictactoe(self, ctx, opponent: discord.Member):
        """play tic-tac-toe

        Usage: .tictactoe [user]
        """
        if opponent == ctx.author:
            return await ctx.reply("```you can't play against yourself```")
        if opponent.bot:
            return await ctx.reply("```bots can't play (yet)```")
        
        board = ["⬜"] * 9
        players = {ctx.author: "❌", opponent: "⭕"}
        turn = ctx.author
        
        def format_board():
            return (
                f"```{board[0]}{board[1]}{board[2]}\n"
                f"{board[3]}{board[4]}{board[5]}\n"
                f"{board[6]}{board[7]}{board[8]}```"
            )
        
        msg = await ctx.reply(f"{turn.mention}'s turn\n{format_board()}")
        
        def check(m):
            return (
                m.author == turn and 
                m.channel == ctx.channel and
                m.content.isdigit() and
                1 <= int(m.content) <= 9
            )
        
        while True:
            try:
                move = await self.bot.wait_for('message', check=check, timeout=60)
                pos = int(move.content) - 1
                
                if board[pos] != "⬜":
                    await ctx.reply("```spot taken!```", delete_after=2)
                    continue
                    
                board[pos] = players[turn]
                await msg.edit(content=f"{turn.mention}'s turn\n{format_board()}")
                
                # Check win conditions
                wins = [
                    [0,1,2], [3,4,5], [6,7,8],  # rows
                    [0,3,6], [1,4,7], [2,5,8],    # columns
                    [0,4,8], [2,4,6]              # diagonals
                ]
                
                for combo in wins:
                    if all(board[i] == players[turn] for i in combo):
                        return await ctx.reply(f"```{turn.display_name} wins!🎉```")
                
                if "⬜" not in board:
                    return await ctx.reply("```it's a tie!```")
                
                turn = opponent if turn == ctx.author else ctx.author
                
            except asyncio.TimeoutError:
                return await ctx.reply("```game timed out```")

    @commands.command()
    async def tableflip(self, ctx):
        """(╯°□°）╯︵ ┻━┻"""
        await ctx.reply("```(╯°□°）╯︵ ┻━┻```")

    @commands.command(aliases=['textart'])
    async def ascii(self, ctx, *, name: str):
        """get ASCII art (cat, dog, etc)"""
        arts = {
            "cat": r""" /\_/\  
    ( o.o ) 
    > ^ < """,
            "dog": r"""  / \__
    (    @\___
    /         O
    /   (_____/
    /_____/   """
        }
        if name.lower() not in arts:
            return await ctx.reply(f"```available: {', '.join(arts.keys())}```")
        await ctx.reply(f"```{arts[name.lower()]}```")
    
    @commands.command(aliases=['typerace', 'tt'])
    async def typingtest(self, ctx):
        """start a typing speed test"""
        sentences = [
            "The quick brown fox jumps over the lazy dog",
            "Discord bots are awesome",
            "tsukami has alot of melanin on his bones",
            "south bronx is a pretty cool server despite the vanity",
            "there is no such thing as a free lunch",
            "a man is not complete until he is dead",
            "you are what you eat unless you eat yourself, then you are you what you are you are",
        ]
        sentence = random.choice(sentences)
        start = time.time()
        await ctx.reply(f"```type this:\n{sentence}```")
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30)
            elapsed = time.time() - start
            wpm = len(sentence.split()) / (elapsed / 60)
            accuracy = sum(a == b for a, b in zip(msg.content, sentence)) / len(sentence) * 100
            
            await ctx.reply(
                f"```time: {elapsed:.2f}s\n"
                f"speed: {wpm:.1f} WPM\n"
                f"accuracy: {accuracy:.1f}%```"
            )
        except asyncio.TimeoutError:
            await ctx.reply("```time's up!```")
    
    @commands.command()
    async def fireworks(self, ctx):
        """celebrate with fireworks"""
        fireworks = ["🎇", "🎆", "✨", "💥", "🔥"]
        msg = await ctx.reply("```3...```")
        await asyncio.sleep(1)
        await msg.edit(content="```2...```")
        await asyncio.sleep(1)
        await msg.edit(content="```1...```")
        await asyncio.sleep(1)
        await msg.edit(content="".join(random.choices(fireworks, k=10)))
    

async def setup(bot):
    try:
        await bot.add_cog(Fun(bot))
        logger.info("Fun cog loaded successfully")

    except Exception as e:
        logger.error(f"Failed to load Fun cog: {e}")
        raise e