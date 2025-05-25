import os
import json
import random
import math
import asyncio
from pathlib import Path
import discord
from discord.ext import commands
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('data/logs/MathRace.log')
    ]
)
logger = logging.getLogger('MathRace')

class MathRace(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.EQUATION_FILE = Path("data/equations.json")
        self.EQUATION_FILE.parent.mkdir(exist_ok=True)  # Create data directory if it doesn't exist

    @commands.command(aliases=['mathduel', 'md', 'math'])
    async def mathrace(self, ctx, opponent: discord.Member = None, difficulty: int = 5):
        """Race to solve advanced math problems
        Difficulty levels: 1-10 (higher is harder)
        Example: .mathrace @User 6"""

        # Help command
        if (isinstance(difficulty, str) and difficulty.lower() == "help") or not opponent:
            examples = {
                "1 - Very Easy": "`3 + 5`",
                "3 - Easy Algebra": "`3x + 5 = 20` (solve for x)",
                "5 - Calculus Intro": "`∫(2x dx) from 0 to 3`",
                "7 - Advanced Calculus": "`lim(x→∞) (1 + 1/x)^x`",
                "9 - Quantum Mechanics": "`∇²ψ + (8π²m/h²)(E - V)ψ = 0` (Schrödinger equation)",
                "10 - Theoretical Math": "`ζ(s) = Σ(1/n^s) for n=1 to ∞` (Riemann Zeta function)"
            }

            embed = discord.Embed(
                title="Math Race Help",
                description="Challenge someone to solve advanced math problems!\n"
                            "Choose a difficulty from **1 (easiest)** to **10 (hardest)**.\n\n"
                            "**Difficulty Examples:**",
                color=discord.Color.blue()
            )

            for level, example in examples.items():
                embed.add_field(name=f"Level {level}", value=example, inline=False)

            embed.set_footer(text="Usage: .mathrace @user [1-10]\nYou can also use `.mathrace help`")
            return await ctx.send(embed=embed)

        # Validate opponent
        if opponent == ctx.author:
            return await ctx.reply(embed=discord.Embed(
                description="You can't race against yourself!",
                color=discord.Color.red()
            ))
        if opponent.bot:
            return await ctx.reply(embed=discord.Embed(
                description="Bots can't race",
                color=discord.Color.red()
            ))

        # Validate difficulty
        if not 1 <= difficulty <= 10:
            return await ctx.reply(embed=discord.Embed(
                description="Difficulty must be between 1 and 10",
                color=discord.Color.red()
            ))

        # Challenge message
        embed = discord.Embed(
            description=f"🧮 **{opponent.mention}**, {ctx.author.mention} challenged you to a difficulty {difficulty} Math Race!\nReact with ✅ to accept within 30 seconds!",
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

        # Generate problem
        game = MathGame()
        problem, answer = game.generate_problem(difficulty)

        # Send problem
        embed = discord.Embed(
            title=f"🧮 Math Race (Difficulty {difficulty})",
            description=f"**Problem:**\n```{problem}```",
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"You have {45*difficulty} seconds to answer!")
        await ctx.send(embed=embed)

        def check_answer(msg):
            if msg.author not in [ctx.author, opponent] or msg.channel != ctx.channel:
                return False
            
            try:
                user_answer = msg.content.strip().lower().replace(" ", "")
                
                # Handle numeric answers
                if isinstance(answer, (int, float)):
                    try:
                        return abs(float(user_answer) - float(answer)) < 0.01
                    except ValueError:
                        return False
                
                # Handle list of answers (quadratic equations)
                elif isinstance(answer, list):
                    try:
                        # Try numeric comparison first
                        user_num = float(user_answer)
                        return any(abs(user_num - float(str(ans))) < 0.01 for ans in answer if isinstance(ans, (int, float)))
                    except ValueError:
                        # Try string comparison for complex numbers
                        return any(user_answer == str(ans).lower().replace(" ", "") for ans in answer)
                
                # Handle string answers
                else:
                    correct_answer = str(answer).lower().replace(" ", "")
                    return user_answer == correct_answer
            
            except Exception:
                return False

        try:
            # Wait for a correct answer
            winner_msg = await self.bot.wait_for(
                "message",
                timeout=45*difficulty,
                check=check_answer
            )
            
            # Announce winner
            embed = discord.Embed(
                description=f"🏆 **{winner_msg.author.mention}** solved it first!\nThe answer was: `{answer}`",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
            
        except asyncio.TimeoutError:
            # Timeout if no one answered
            embed = discord.Embed(
                description=f"⌛ Time's up! No one solved the problem.\nThe answer was: `{answer}`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

class MathGame:
    def __init__(self):
        self.EQUATION_FILE = Path("data/equations.json")
        self.EQUATION_FILE.parent.mkdir(exist_ok=True)  # Create directory if needed
        self.equations = self.load_equations()

    def load_equations(self):
        if not self.EQUATION_FILE.exists():
            with open(self.EQUATION_FILE, 'w') as f:
                json.dump({str(i): [] for i in range(1, 11)}, f, indent=4)
        with open(self.EQUATION_FILE, 'r') as f:
            return json.load(f)

    def save_equation(self, diff, problem, answer):
        entry = {"problem": problem, "answer": answer}
        self.equations.setdefault(str(diff), []).append(entry)
        with open(self.EQUATION_FILE, 'w') as f:
            json.dump(self.equations, f, indent=4)

    def generate_problem(self, diff):
        # Check if a stored problem exists
        existing = self.equations.get(str(diff), [])
        if existing:
            chosen = random.choice(existing)
            return chosen["problem"], chosen["answer"]

        # Otherwise, generate a new one
        if diff <= 2:
            a, b = random.randint(1, 10), random.randint(1, 10)
            op = random.choice(['+', '-', '*'])
            problem = f"{a} {op} {b}"
            answer = eval(f"{a}{op}{b}")
        
        elif diff <= 4:
            a = random.randint(2, 5)
            b = random.randint(5, 20)
            c = random.randint(1, 10)
            problem = f"{a}x + {b} = {c}"
            answer = round((c - b) / a, 2)
        
        elif diff <= 6:
            a = random.randint(1, 3)
            b = random.randint(-5, 5)
            c = random.randint(-10, 10)
            problem = f"{a}x² + {b}x + {c} = 0"
            discriminant = b**2 - 4*a*c
            if discriminant >= 0:
                root1 = round((-b + math.sqrt(discriminant)) / (2 * a), 2)
                root2 = round((-b - math.sqrt(discriminant)) / (2 * a), 2)
                answer = [root1, root2]
            else:
                real_part = round(-b / (2 * a), 2)
                imag_part = round(math.sqrt(-discriminant) / (2 * a), 2)
                root1 = f"{real_part}+{imag_part}i"
                root2 = f"{real_part}-{imag_part}i"
                answer = [root1, root2]
        
        elif diff <= 8:
            choice = random.choice(['derivative', 'integral', 'limit'])
            if choice == 'derivative':
                coeff = random.randint(1, 5)
                power = random.randint(2, 4)
                problem = f"d/dx ({coeff}x^{power})"
                answer = f"{coeff * power}x^{power - 1}"
            elif choice == 'integral':
                coeff = random.randint(1, 5)
                problem = f"∫({coeff}x dx)"
                answer = f"{coeff/2}x² + C"
            else:
                problem = "lim(x→0) sin(x)/x"
                answer = 1
        
        elif diff <= 10:
            choice = random.choice(['matrix', 'complex', 'diffeq'])
            if choice == 'matrix':
                a, b = random.randint(1, 5), random.randint(1, 5)
                c, d = random.randint(1, 5), random.randint(1, 5)
                problem = f"Det of [[{a}, {b}], [{c}, {d}]]"
                answer = a * d - b * c
            elif choice == 'complex':
                a, b = random.randint(1, 5), random.randint(1, 5)
                c, d = random.randint(1, 5), random.randint(1, 5)
                problem = f"({a}+{b}i) * ({c}+{d}i)"
                real = a * c - b * d
                imag = a * d + b * c
                answer = f"{real}+{imag}i"
            else:
                coeff = random.randint(2, 5)
                problem = f"Solve: dy/dx = {coeff}y"
                answer = f"y = Ce^({coeff}x)"

        # Save and return the new problem
        self.save_equation(diff, problem, answer)
        return problem, answer

async def setup(bot):
    try:
        await bot.add_cog(MathRace(bot))
        logger.info("MathRace cog loaded successfully")

    except Exception as e:
        logger.error(f"Failed to load MathRace cog: {e}")
        raise e