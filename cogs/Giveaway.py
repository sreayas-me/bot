import discord
import random
import json
import logging
from discord.ext import commands, tasks
import datetime
import asyncio
from cogs.logging.logger import CogLogger
from utils.error_handler import ErrorHandler
from utils.db import async_db

class Giveaway(commands.Cog, ErrorHandler):
    def __init__(self, bot):
        ErrorHandler.__init__(self)
        self.bot = bot
        self.logger = CogLogger(self.__class__.__name__)
        self.bot.launch_time = discord.utils.utcnow()
        self.active_giveaways = {}  # Store active giveaways in memory
        self.check_giveaways.start()  # Start background task
        self.logger.info("Giveaway cog initialized")

    def cog_unload(self):
        """Clean up when cog is unloaded"""
        self.check_giveaways.cancel()

    @tasks.loop(seconds=30)
    async def check_giveaways(self):
        """Check for expired giveaways every 30 seconds"""
        try:
            current_time = datetime.datetime.now()
            expired_giveaways = []
            
            for giveaway_id, giveaway_data in self.active_giveaways.items():
                if current_time >= giveaway_data['end_time']:
                    expired_giveaways.append(giveaway_id)
            
            for giveaway_id in expired_giveaways:
                await self.end_giveaway(giveaway_id)
                
        except Exception as e:
            self.logger.error(f"Error checking giveaways: {e}")

    @check_giveaways.before_loop
    async def before_check_giveaways(self):
        """Wait for bot to be ready before starting the loop"""
        await self.bot.wait_until_ready()

    async def get_server_balance(self, guild_id: int) -> int:
        """Get the server's giveaway balance"""
        try:
            settings = await async_db.get_guild_settings(guild_id)
            return settings.get('server_balance', 0)
        except Exception as e:
            self.logger.error(f"Error getting server balance: {e}")
            return 0

    async def update_server_balance(self, guild_id: int, amount: int) -> bool:
        """Update the server's giveaway balance"""
        try:
            current_balance = await self.get_server_balance(guild_id)
            new_balance = current_balance + amount
            
            if new_balance < 0:
                return False
                
            return await async_db.update_guild_settings(guild_id, {'server_balance': new_balance})
        except Exception as e:
            self.logger.error(f"Error updating server balance: {e}")
            return False

    async def get_multiplier_info(self, user_id: int) -> dict:
        """Get active multipliers for a user"""
        try:
            # This would integrate with your potion/buff system
            # For now, return a base multiplier
            return {'multiplier': 1.0, 'description': 'No active multipliers'}
        except Exception as e:
            self.logger.error(f"Error getting multiplier info: {e}")
            return {'multiplier': 1.0, 'description': 'Error getting multipliers'}

    @commands.group(name='giveaway', aliases=['gw'], invoke_without_command=True)
    async def giveaway_group(self, ctx):
        """Giveaway command group"""
        embed = discord.Embed(
            title="🎉 Giveaway Commands",
            description="Available giveaway commands:",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="**User Commands**",
            value=(
                "`.giveaway donate <amount>` - Donate to server balance\n"
                "`.giveaway balance` - Check server balance\n"
                "`.giveaway list` - View active giveaways"
            ),
            inline=False
        )
        embed.add_field(
            name="**Admin Commands**",
            value=(
                "`.giveaway create <amount> <duration> [description]` - Create giveaway\n"
                "`.giveaway end <giveaway_id>` - End giveaway early"
            ),
            inline=False
        )
        embed.add_field(
            name="**Examples**",
            value=(
                "`.giveaway donate 1000` - Donate 1000 coins\n"
                "`.giveaway create 5000 1h Epic Giveaway!` - Create 1 hour giveaway"
            ),
            inline=False
        )
        await ctx.send(embed=embed)

    @giveaway_group.command(name='donate')
    async def donate_to_server(self, ctx, amount: int):
        """Donate money to the server giveaway balance"""
        if amount <= 0:
            await ctx.reply("❌ Amount must be positive!")
            return

        # Check if user has enough money
        wallet_balance = await async_db.get_wallet_balance(ctx.author.id, ctx.guild.id)
        if wallet_balance < amount:
            await ctx.reply(f"❌ Insufficient funds! You have {wallet_balance:,} coins but need {amount:,}.")
            return

        # Get multiplier info
        multiplier_info = await self.get_multiplier_info(ctx.author.id)
        multiplier = multiplier_info['multiplier']
        boosted_amount = int(amount * multiplier)

        # Deduct from user wallet
        if not await async_db.update_wallet(ctx.author.id, -amount, ctx.guild.id):
            await ctx.reply("❌ Failed to deduct donation from your wallet!")
            return

        # Add to server balance
        if not await self.update_server_balance(ctx.guild.id, boosted_amount):
            # Refund user if server balance update fails
            await async_db.update_wallet(ctx.author.id, amount, ctx.guild.id)
            await ctx.reply("❌ Failed to update server balance!")
            return

        # Store stats
        await async_db.store_stats(ctx.guild.id, "donated")

        embed = discord.Embed(
            title="💝 Donation Successful!",
            description=f"{ctx.author.mention} donated **{amount:,}** coins to the server giveaway balance!",
            color=discord.Color.green()
        )
        
        if multiplier > 1.0:
            embed.add_field(
                name="🚀 Multiplier Applied!",
                value=f"**{multiplier}x** multiplier active!\nActual donation: **{boosted_amount:,}** coins",
                inline=False
            )
            embed.add_field(
                name="Multiplier Source",
                value=multiplier_info['description'],
                inline=False
            )

        server_balance = await self.get_server_balance(ctx.guild.id)
        embed.add_field(
            name="💰 New Server Balance",
            value=f"**{server_balance:,}** coins",
            inline=True
        )
        
        embed.set_footer(text=f"Thank you for contributing to {ctx.guild.name}!")
        await ctx.send(embed=embed)

    @giveaway_group.command(name='balance', aliases=['bal'])
    async def server_balance(self, ctx):
        """Check the server's giveaway balance"""
        balance = await self.get_server_balance(ctx.guild.id)
        
        embed = discord.Embed(
            title="💰 Server Giveaway Balance",
            description=f"**{balance:,}** coins available for giveaways",
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Use '.giveaway donate <amount>' to contribute!")
        await ctx.send(embed=embed)

    @giveaway_group.command(name='create')
    @commands.has_permissions(manage_guild=True)
    async def create_giveaway(self, ctx, amount: int, duration: str, *, description: str = "Amazing Giveaway!"):
        """Create a new giveaway"""
        if amount <= 0:
            await ctx.reply("❌ Giveaway amount must be positive!")
            return

        # Check server balance
        server_balance = await self.get_server_balance(ctx.guild.id)
        if server_balance < amount:
            await ctx.reply(f"❌ Insufficient server balance! Available: {server_balance:,}, needed: {amount:,}")
            return

        # Parse duration
        try:
            duration_seconds = self.parse_duration(duration)
            if duration_seconds < 60:  # Minimum 1 minute
                await ctx.reply("❌ Minimum giveaway duration is 1 minute!")
                return
            if duration_seconds > 7 * 24 * 3600:  # Maximum 7 days
                await ctx.reply("❌ Maximum giveaway duration is 7 days!")
                return
        except ValueError:
            await ctx.reply("❌ Invalid duration format! Use formats like: 1h, 30m, 2d, 1h30m")
            return

        # Deduct from server balance
        if not await self.update_server_balance(ctx.guild.id, -amount):
            await ctx.reply("❌ Failed to deduct from server balance!")
            return

        # Create giveaway embed
        end_time = datetime.datetime.now() + datetime.timedelta(seconds=duration_seconds)
        giveaway_id = f"{ctx.guild.id}_{int(datetime.datetime.now().timestamp())}"

        embed = discord.Embed(
            title="🎉 GIVEAWAY 🎉",
            description=description,
            color=discord.Color.gold()
        )
        embed.add_field(
            name="💰 Prize",
            value=f"**{amount:,}** coins",
            inline=True
        )
        embed.add_field(
            name="⏰ Ends",
            value=f"<t:{int(end_time.timestamp())}:R>",
            inline=True
        )
        embed.add_field(
            name="🎯 How to Enter",
            value="React with 🎉 to enter!",
            inline=False
        )
        embed.set_footer(text=f"Giveaway ID: {giveaway_id}")

        # Send giveaway message
        giveaway_msg = await ctx.send(embed=embed)
        await giveaway_msg.add_reaction("🎉")

        # Store giveaway data
        self.active_giveaways[giveaway_id] = {
            'guild_id': ctx.guild.id,
            'channel_id': ctx.channel.id,
            'message_id': giveaway_msg.id,
            'amount': amount,
            'description': description,
            'end_time': end_time,
            'host_id': ctx.author.id,
            'participants': []  # Changed from set() to []
        }

        # Save to database (persistent storage)
        await async_db.update_guild_settings(
            ctx.guild.id, 
            {f'giveaway_{giveaway_id}': self.active_giveaways[giveaway_id]}
        )

        await ctx.send(f"✅ Giveaway created successfully! ID: `{giveaway_id}`")

    @giveaway_group.command(name='end')
    @commands.has_permissions(manage_guild=True)
    async def end_giveaway_command(self, ctx, giveaway_id: str):
        """End a giveaway early"""
        if giveaway_id not in self.active_giveaways:
            await ctx.reply("❌ Giveaway not found!")
            return

        await self.end_giveaway(giveaway_id)
        await ctx.send("✅ Giveaway ended successfully!")

    @giveaway_group.command(name='list')
    async def list_giveaways(self, ctx):
        """List active giveaways"""
        guild_giveaways = {
            gw_id: gw_data for gw_id, gw_data in self.active_giveaways.items()
            if gw_data['guild_id'] == ctx.guild.id
        }

        if not guild_giveaways:
            embed = discord.Embed(
                title="🎉 Active Giveaways",
                description="No active giveaways in this server.",
                color=discord.Color.blue()
            )
        else:
            embed = discord.Embed(
                title="🎉 Active Giveaways",
                color=discord.Color.gold()
            )
            for gw_id, gw_data in guild_giveaways.items():
                embed.add_field(
                    name=f"**{gw_data['description']}**",
                    value=(
                        f"💰 Prize: **{gw_data['amount']:,}** coins\n"
                        f"⏰ Ends: <t:{int(gw_data['end_time'].timestamp())}:R>\n"
                        f"🆔 ID: `{gw_id}`"
                    ),
                    inline=False
                )

        await ctx.send(embed=embed)

    async def end_giveaway(self, giveaway_id: str):
        """End a giveaway and pick winners"""
        if giveaway_id not in self.active_giveaways:
            return

        giveaway_data = self.active_giveaways[giveaway_id]
        
        try:
            # Get the giveaway message
            guild = self.bot.get_guild(giveaway_data['guild_id'])
            if not guild:
                return

            channel = guild.get_channel(giveaway_data['channel_id'])
            if not channel:
                return

            try:
                message = await channel.fetch_message(giveaway_data['message_id'])
            except discord.NotFound:
                # Message was deleted
                del self.active_giveaways[giveaway_id]
                return

            # Get participants from reactions
            participants = []
            participant_ids = set()  # Use a set locally to track unique participants
            for reaction in message.reactions:
                if str(reaction.emoji) == "🎉":
                    async for user in reaction.users():
                        if not user.bot and user.id != giveaway_data['host_id'] and user.id not in participant_ids:
                            participants.append(user)
                            participant_ids.add(user.id)

            # Pick winner
            embed = discord.Embed(
                title="🎉 GIVEAWAY ENDED 🎉",
                description=giveaway_data['description'],
                color=discord.Color.red()
            )

            if not participants:
                embed.add_field(
                    name="😢 No Winner",
                    value="No valid participants found!",
                    inline=False
                )
                # Refund server balance
                await self.update_server_balance(giveaway_data['guild_id'], giveaway_data['amount'])
                embed.add_field(
                    name="💰 Refund",
                    value=f"{giveaway_data['amount']:,} coins refunded to server balance",
                    inline=False
                )
            else:
                winner = random.choice(participants)
                
                # Award prize to winner
                await async_db.update_wallet(winner.id, giveaway_data['amount'], giveaway_data['guild_id'])
                
                embed.add_field(
                    name="🏆 Winner",
                    value=f"Congratulations {winner.mention}!",
                    inline=False
                )
                embed.add_field(
                    name="💰 Prize",
                    value=f"**{giveaway_data['amount']:,}** coins",
                    inline=True
                )
                embed.add_field(
                    name="👥 Participants",
                    value=f"**{len(participants)}** entries",
                    inline=True
                )

                # Store stats
                await async_db.store_stats(giveaway_data['guild_id'], "giveaway_won")

            # Update the original message
            await message.edit(embed=embed)
            await message.clear_reactions()

            # Send winner announcement
            if participants:
                await channel.send(f"🎉 Congratulations {winner.mention}! You won **{giveaway_data['amount']:,}** coins!")

        except Exception as e:
            self.logger.error(f"Error ending giveaway {giveaway_id}: {e}")
        finally:
            # Clean up
            if giveaway_id in self.active_giveaways:
                del self.active_giveaways[giveaway_id]

    def parse_duration(self, duration_str: str) -> int:
        """Parse duration string into seconds"""
        duration_str = duration_str.lower().replace(' ', '')
        total_seconds = 0
        current_number = ''
        
        for char in duration_str:
            if char.isdigit():
                current_number += char
            elif char in 'smhd':
                if not current_number:
                    raise ValueError("Invalid duration format")
                
                number = int(current_number)
                if char == 's':
                    total_seconds += number
                elif char == 'm':
                    total_seconds += number * 60
                elif char == 'h':
                    total_seconds += number * 3600
                elif char == 'd':
                    total_seconds += number * 86400
                
                current_number = ''
            else:
                raise ValueError("Invalid duration format")
        
        if current_number:
            # Assume minutes if no unit specified
            total_seconds += int(current_number) * 60
            
        return total_seconds

    @donate_to_server.error
    async def donate_error(self, ctx, error):
        """Handle donate command errors"""
        if isinstance(error, commands.BadArgument):
            await ctx.reply("❌ Please provide a valid amount to donate!")
        else:
            await self.handle_error(ctx, error, "donate")

    @create_giveaway.error
    async def create_giveaway_error(self, ctx, error):
        """Handle create giveaway command errors"""
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply("❌ You don't have permission to create giveaways!")
        elif isinstance(error, commands.BadArgument):
            await ctx.reply("❌ Invalid giveaway parameters! Usage: `.giveaway create <amount> <duration> [description]`")
        else:
            await self.handle_error(ctx, error, "create_giveaway")

    @end_giveaway_command.error
    async def end_giveaway_error(self, ctx, error):
        """Handle end giveaway command errors"""
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply("❌ You don't have permission to end giveaways!")
        else:
            await self.handle_error(ctx, error, "end_giveaway")

async def setup(bot):
    logger = CogLogger("Giveaway")
    try:
        await bot.add_cog(Giveaway(bot))
        logger.info("Giveaway cog loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load Giveaway cog: {e}")
        raise