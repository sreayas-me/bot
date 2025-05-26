import discord
import random
import json
from discord.ext import commands
import logging
import asyncio
import string
import time
import aiohttp
from cogs.logging.logger import CogLogger
from utils.error_handler import ErrorHandler

class Fun(commands.Cog, ErrorHandler):
    def __init__(self, bot):
        ErrorHandler.__init__(self)
        self.bot = bot
        # Cache for active games to prevent spam
        self.active_games = set()
        self.logger = CogLogger(self.__class__.__name__)

    def get_command_help(self) -> list[discord.Embed]:
        """Get paginated help embeds for this cog"""
        pages = []
        
        # Text Commands Page
        text_embed = discord.Embed(
            title="🎲 Fun Commands - Text Transformations",
            color=discord.Color.blue()
        )
        text_commands = ['spongebob', 'tinytext', 'reverse', 'owoify', 'emojify']
        for cmd_name in text_commands:
            cmd = self.bot.get_command(cmd_name)
            if cmd:
                text_embed.add_field(
                    name=f"{cmd.name} {cmd.signature}",
                    value=cmd.help or "No description",
                    inline=False
                )
        pages.append(text_embed)

        # Game Commands Page
        games_embed = discord.Embed(
            title="🎲 Fun Commands - Games",
            color=discord.Color.blue()
        )
        game_commands = ['guess', 'typingtest']
        for cmd_name in game_commands:
            cmd = self.bot.get_command(cmd_name)
            if cmd:
                games_embed.add_field(
                    name=f"{cmd.name} {cmd.signature}",
                    value=cmd.help or "No description",
                    inline=False
                )
        pages.append(games_embed)

        # Utility Fun Commands Page
        util_embed = discord.Embed(
            title="🎲 Fun Commands - Utilities",
            color=discord.Color.blue()
        )
        util_commands = ['pick', 'ball8', 'flip', 'roll']
        for cmd_name in util_commands:
            cmd = self.bot.get_command(cmd_name)
            if cmd:
                util_embed.add_field(
                    name=f"{cmd.name} {cmd.signature}",
                    value=cmd.help or "No description",
                    inline=False
                )
        pages.append(util_embed)

        # ASCII & Visual Commands Page
        visual_embed = discord.Embed(
            title="🎲 Fun Commands - Visual",
            color=discord.Color.blue()
        )
        visual_commands = ['ascii', 'fireworks', 'tableflip']
        for cmd_name in visual_commands:
            cmd = self.bot.get_command(cmd_name)
            if cmd:
                visual_embed.add_field(
                    name=f"{cmd.name} {cmd.signature}",
                    value=cmd.help or "No description",
                    inline=False
                )
        pages.append(visual_embed)

        return pages

    # Text transformation commands
    @commands.command(aliases=['mock'])
    async def spongebob(self, ctx, *, text):
        """mOcK sOmE tExT lIkE tHiS"""
        if len(text) > 500:
            return await ctx.reply("```text too long (max 500 chars)```")
        result = ''.join([char.upper() if i % 2 == 0 else char.lower() for i, char in enumerate(text)])
        await ctx.reply(f"```{result}```")

    @commands.command(aliases=['choose', 'random'])
    async def pick(self, ctx, *options):
        """pick a random option from your list
        
        Usage: pick [option1] [option2] ... [optionN]
        """
        if not options:
            return await ctx.reply("```provide some options to choose from```")
        if len(options) > 50:
            return await ctx.reply("```too many options (max 50)```")
        
        chosen = random.choice(options)
        await ctx.reply(f"🎲 ```i choose: {chosen}```")

    @commands.command(aliases=['smallcaps', 'tiny'])
    async def tinytext(self, ctx, *, text: str):
        """convert to ᵗⁱⁿʸ ˢᵘᵖᵉʳˢᶜʳⁱᵖᵗ"""
        if len(text) > 200:
            return await ctx.reply("```text too long (max 200 chars)```")
        
        mapping = str.maketrans(
            'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ',
            'ᵃᵇᶜᵈᵉᶠᵍʰⁱʲᵏˡᵐⁿᵒᵖᵠʳˢᵗᵘᵛʷˣʸᶻᴬᴮᶜᴰᴱᶠᴳᴴᴵᴶᴷᴸᴹᴺᴼᴾᵠᴿˢᵀᵁⱽᵂˣʸᶻ'
        )
        result = text.translate(mapping)
        await ctx.reply(f"```{result}```")

    @commands.command(aliases=['textflip', 'tf'])
    async def reverse(self, ctx, *, text: str):
        """ʇxǝʇ ruoy esreveɹ"""
        if len(text) > 500:
            return await ctx.reply("```text too long (max 500 chars)```")
        await ctx.reply(f"```{text[::-1]}```")
    
    @commands.command(aliases=['owo', 'uwu'])
    async def owoify(self, ctx, *, text: str):
        """uwu-ify youw text owo *nuzzles*"""
        if len(text) > 500:
            return await ctx.reply("```text too long (max 500 chars)```")
        
        replacements = {
            'r': 'w', 'l': 'w', 'R': 'W', 'L': 'W',
            'no': 'nyo', 'No': 'Nyo', 'NO': 'NYO',
            'ove': 'uv', 'th': 'f', 'TH': 'F',
            '!': '! uwu', '?': '? owo'
        }
        
        for k, v in replacements.items():
            text = text.replace(k, v)
        
        # Add random uwu expressions
        if random.random() < 0.3:
            text += random.choice([' uwu', ' owo', ' >w<', ' ^w^'])
            
        await ctx.reply(f"```{text}```")

    @commands.command(aliases=['letters'])
    async def emojify(self, ctx, *, text: str):
        """turn text into 🔤 regional 🔤 indicators"""
        if len(text) > 100:
            return await ctx.reply("```text too long (max 100 chars)```")
        
        emoji_map = {
            'a': '🇦', 'b': '🇧', 'c': '🇨', 'd': '🇩', 'e': '🇪', 'f': '🇫',
            'g': '🇬', 'h': '🇭', 'i': '🇮', 'j': '🇯', 'k': '🇰', 'l': '🇱',
            'm': '🇲', 'n': '🇳', 'o': '🇴', 'p': '🇵', 'q': '🇶', 'r': '🇷',
            's': '🇸', 't': '🇹', 'u': '🇺', 'v': '🇻', 'w': '🇼', 'x': '🇽',
            'y': '🇾', 'z': '🇿', '0': '0️⃣', '1': '1️⃣', '2': '2️⃣', '3': '3️⃣',
            '4': '4️⃣', '5': '5️⃣', '6': '6️⃣', '7': '7️⃣', '8': '8️⃣', '9': '9️⃣',
            '!': '❗', '?': '❓', ' ': '   '
        }
        
        result = ''.join([emoji_map.get(c.lower(), c) for c in text])
        await ctx.reply(result)

    # Magic 8-ball with more responses
    @commands.command(aliases=['8ball', 'magic8ball'])
    async def ball8(self, ctx, *, question: str):
        """ask the magic 8-ball a question"""
        if len(question) > 200:
            return await ctx.reply("```question too long```")
            
        responses = [
            "it is certain", "without a doubt", "yes definitely", "you may rely on it",
            "as i see it, yes", "most likely", "outlook good", "yes",
            "signs point to yes", "reply hazy, try again", "ask again later",
            "better not tell you now", "cannot predict now", "concentrate and ask again",
            "don't count on it", "my reply is no", "my sources say no",
            "outlook not so good", "very doubtful", "absolutely not"
        ]
        
        response = random.choice(responses)
        await ctx.reply(f"🎱 ```{response}```")

    @commands.command(aliases=['dice', 'd'])
    async def roll(self, ctx, dice: str = "1d6"):
        """roll dice (format: 2d20, 1d6, etc.)"""
        try:
            if 'd' not in dice.lower():
                return await ctx.reply("```format: XdY (like 2d6 or 1d20)```")
            
            num_dice, sides = map(int, dice.lower().split('d'))
            
            if num_dice > 20 or sides > 1000 or num_dice < 1 or sides < 2:
                return await ctx.reply("```reasonable limits: 1-20 dice, 2-1000 sides```")
            
            rolls = [random.randint(1, sides) for _ in range(num_dice)]
            total = sum(rolls)
            
            if num_dice == 1:
                await ctx.reply(f"🎲 ```rolled {sides}-sided die: {total}```")
            else:
                rolls_str = ", ".join(map(str, rolls))
                await ctx.reply(f"🎲 ```rolled {num_dice}d{sides}: [{rolls_str}] = {total}```")
                
        except ValueError:
            await ctx.reply("```format: XdY (like 2d6 or 1d20)```")

    # Interactive games
    @commands.command(aliases=['guessnumber'])
    async def guess(self, ctx, max_num: int = 100):
        """start a number guessing game"""
        if max_num > 10000 or max_num < 10:
            return await ctx.reply("```number range: 10-10000```")
        
        if ctx.author.id in self.active_games:
            return await ctx.reply("```finish your current game first!```")
        
        self.active_games.add(ctx.author.id)
        
        try:
            num = random.randint(1, max_num)
            await ctx.reply(f"🎯 ```guess a number between 1-{max_num}\ntype 'quit' to give up```")
            
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel
            
            tries = 0
            start_time = time.time()
            
            while tries < 10:  # Max 10 tries
                try:
                    msg = await self.bot.wait_for('message', check=check, timeout=45.0)
                    
                    if msg.content.lower() in ['quit', 'stop', 'exit']:
                        return await ctx.reply(f"```game over! the number was {num}```")
                    
                    try:
                        guess = int(msg.content)
                    except ValueError:
                        await ctx.reply("```please enter a valid number```")
                        continue
                    
                    if guess < 1 or guess > max_num:
                        await ctx.reply(f"```number must be between 1-{max_num}```")
                        continue
                    
                    tries += 1
                    
                    if guess == num:
                        elapsed = time.time() - start_time
                        await ctx.reply(f"🎉 ```correct! the number was {num}\ntries: {tries}\ntime: {elapsed:.1f}s```")
                        return
                    
                    hint = "too high" if guess > num else "too low"
                    remaining = 10 - tries
                    await ctx.reply(f"```{hint}! tries left: {remaining}```")
                    
                except asyncio.TimeoutError:
                    return await ctx.reply(f"```timeout! the number was {num}```")
            
            await ctx.reply(f"```out of tries! the number was {num}```")
            
        finally:
            self.active_games.discard(ctx.author.id)

    @commands.command(aliases=['tt', 'typerace'])
    async def typingtest(self, ctx, difficulty: str = "easy"):
        """test your typing speed
        
        Difficulties: easy, medium, hard
        """
        if ctx.author.id in self.active_games:
            return await ctx.reply("```finish your current game first!```")
        
        sentences = {
            "easy": [
                "the quick brown fox jumps over the lazy dog",
                "hello world this is a simple test",
                "discord bots are pretty cool",
                "python is a great programming language"
            ],
            "medium": [
                "tsukami has a lot of melanin on his bones",
                "south bronx is a pretty cool server despite the vanity",
                "there is no such thing as a free lunch in this world",
                "programming requires patience and logical thinking skills"
            ],
            "hard": [
                "you are what you eat unless you eat yourself, then you are what you are",
                "a man is not complete until he is married, then he is finished",
                "the complexity of modern software systems requires careful architectural planning",
                "asynchronous programming paradigms enable efficient resource utilization"
            ]
        }
        
        if difficulty not in sentences:
            return await ctx.reply("```difficulties: easy, medium, hard```")
        
        self.active_games.add(ctx.author.id)
        
        try:
            sentence = random.choice(sentences[difficulty])
            start = time.time()
            
            embed = discord.Embed(
                description=f"⌨️ Type this exactly:\n```{sentence}```\n`{difficulty.title()} | 60s limit`",
                color=discord.Color.blue()
            )
            await ctx.reply(embed=embed)
            
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel
            
            try:
                msg = await self.bot.wait_for('message', check=check, timeout=60)
                elapsed = time.time() - start
                
                # Calculate stats
                words = len(sentence.split())
                wpm = words / (elapsed / 60)
                
                # Calculate accuracy
                correct_chars = sum(a == b for a, b in zip(msg.content, sentence))
                accuracy = (correct_chars / len(sentence)) * 100
                
                # Grade performance
                if accuracy == 100:
                    grade = "Perfect! 🏆"
                elif accuracy >= 95:
                    grade = "Excellent! ⭐"
                elif accuracy >= 85:
                    grade = "Good! 👍"
                elif accuracy >= 70:
                    grade = "Not bad! 👌"
                else:
                    grade = "Keep practicing! 💪"
                
                # Results embed
                embed = discord.Embed(
                    description=f"📊 **Results**\n\n"
                                f"Time: `{elapsed:.2f}s`\n"
                                f"Speed: `{wpm:.1f}` WPM\n"
                                f"Accuracy: `{accuracy:.1f}%`\n"
                                f"Grade: {grade}",
                    color=discord.Color.green()
                )
                await ctx.reply(embed=embed)
                
            except asyncio.TimeoutError:
                await ctx.reply("```time's up! try again when you're ready```")
        
        finally:
            self.active_games.discard(ctx.author.id)

    # Fun interaction commands
    @commands.command(aliases=['ship'])
    async def lovecalc(self, ctx, user1: discord.Member, user2: discord.Member = None):
        """calculate love compatibility percentage"""
        user2 = user2 or ctx.author
        
        if user1 == user2:
            return await ctx.reply("```you can't ship someone with themselves! (or can you? 🤔)```")
        
        # Consistent score based on user IDs
        score = (user1.id + user2.id) % 101
        
        if score < 20:
            emoji = "💔"
            comment = "not compatible at all!"
        elif score < 40:
            emoji = "😐"
            comment = "just friends maybe?"
        elif score < 60:
            emoji = "😊"
            comment = "decent compatibility!"
        elif score < 80:
            emoji = "❤️"
            comment = "great match!"
        else:
            emoji = "💞"
            comment = "soulmates! 💕"
        
        await ctx.reply(f"💘 ```{user1.display_name} {emoji} {user2.display_name}\ncompatibility: {score}%\n{comment}```")

    @commands.command()
    async def hack(self, ctx, user: discord.Member):
        """totally real hacking simulator (joke command)"""
        if user == ctx.author:
            return await ctx.reply("```you can't hack yourself... or can you? 🤔```")
        
        if user.bot:
            return await ctx.reply("```bots have advanced firewalls! (they're unhackable)```")
        
        steps = [
            f"```initializing hack on {user.display_name}...```",
            "```bypassing discord security... 23%```",
            "```cracking password... 56%```",
            "```accessing mainframe... 78%```",
            "```downloading data... 94%```",
            f"```hack complete! discovered: {random.choice([
                'their browser history is 99% memes',
                'they have 847 unread discord notifications',
                'their password is literally \"password123\"',
                'they\'ve been typing for 5 minutes without sending',
                'they have 23 servers muted',
                'they use light mode (shocking!)',
                'they have nitro but no good emotes'
            ])}```"
        ]
        
        msg = await ctx.reply(steps[0])
        for step in steps[1:]:
            await asyncio.sleep(random.uniform(1.2, 2.0))
            await msg.edit(content=step)

    # ASCII Art and visuals
    @commands.command(aliases=['textart'])
    async def ascii(self, ctx, *, name: str):
        """get cool ASCII art
        
        Available: cat, dog, heart, star, shrug, tableflip
        """
        arts = {
            "cat": "```\n /\\_/\\  \n( o.o ) \n > ^ < \n```",
            "dog": "```\n  / \\__\n (    @\\___\n /         O\n /   (_____/\n /_____/   \n```",
            "heart": "```\n  ♥♥♥    ♥♥♥\n ♥♥♥♥♥  ♥♥♥♥♥\n ♥♥♥♥♥♥♥♥♥♥♥\n  ♥♥♥♥♥♥♥♥♥\n   ♥♥♥♥♥♥♥\n    ♥♥♥♥♥\n     ♥♥♥\n      ♥\n```",
            "star": "```\n    ★\n   ★★★\n  ★★★★★\n ★★★★★★★\n★★★★★★★★★\n ★★★★★★★\n  ★★★★★\n   ★★★\n    ★\n```",
            "shrug": "```¯\\_(ツ)_/¯```",
            "tableflip": "```(╯°□°）╯︵ ┻━┻```"
        }
        
        name = name.lower().strip()
        if name not in arts:
            available = ", ".join(arts.keys())
            return await ctx.reply(f"```available arts: {available}```")
        
        await ctx.reply(arts[name])

    @commands.command()
    async def fireworks(self, ctx):
        """celebrate with animated fireworks! 🎆"""
        fireworks = ["🎇", "🎆", "✨", "💥", "🌟"]
        
        msg = await ctx.reply("```preparing fireworks...```")
        await asyncio.sleep(1)
        
        for i in range(3, 0, -1):
            await msg.edit(content=f"```{i}...```")
            await asyncio.sleep(1)
        
        # Multiple firework bursts
        for _ in range(3):
            burst = "".join(random.choices(fireworks, k=random.randint(8, 15)))
            await msg.edit(content=burst)
            await asyncio.sleep(0.8)
        
        await msg.edit(content="🎉 ```celebration complete! 🎉```")

    # Utility commands
    @commands.command()
    async def tableflip(self, ctx):
        """(╯°□°）╯︵ ┻━┻"""
        reactions = [
            "(╯°□°）╯︵ ┻━┻",
            "┻━┻ ︵ヽ(`Д´)ﾉ︵ ┻━┻",
            "ಠ_ಠ ... ┬─┬ノ( º _ ºノ)",
            "(ﾉಥ益ಥ）ﾉ ┻━┻"
        ]
        await ctx.reply(f"```{random.choice(reactions)}```")

    @commands.command(aliases=['password', 'pwd'])
    async def genpass(self, ctx, length: int = 12):
        """generate a random secure password"""
        if length < 6 or length > 50:
            return await ctx.reply("```password length: 6-50 characters```")
        
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(random.choices(chars, k=length))
        
        try:
            await ctx.author.send(f"🔐 Your generated password: ```{password}```")
            await ctx.reply("```password sent to your DMs for security!```")
        except discord.Forbidden:
            await ctx.reply("```couldn't DM you! enable DMs from server members```")

    @commands.command()
    async def cooldown(self, ctx):
        """check command cooldowns"""
        embed = discord.Embed(
            title="⏰ Active Games",
            description="Games you're currently playing:",
            color=discord.Color.blue()
        )
        
        if ctx.author.id in self.active_games:
            embed.add_field(
                name="Status", 
                value="You have an active game running!\nFinish it before starting another.", 
                inline=False
            )
        else:
            embed.add_field(
                name="Status", 
                value="No active games - you're free to play!", 
                inline=False
            )
        
        await ctx.reply(embed=embed)

    # Error handling for missing arguments
    @spongebob.error
    @tinytext.error  
    @reverse.error
    @owoify.error
    @emojify.error
    @ball8.error
    async def text_command_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply("```please provide some text to transform```")

    @lovecalc.error
    @hack.error
    async def user_command_error(self, ctx, error):
        if isinstance(error, commands.MemberNotFound):
            await ctx.reply("```user not found in this server```")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply("```please mention a user```")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if ctx.command and ctx.command.cog_name == self.__class__.__name__:
            await self.handle_error(ctx, error)


async def setup(bot):
    try:
        logger = CogLogger("Fun")
        await bot.add_cog(Fun(bot))
    except Exception as e:
        logger.error(f"Failed to load Fun cog: {e}")
        raise e