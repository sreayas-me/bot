import discord
from discord.ext import commands
from discord.utils import get
import logging
import json
import os
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('data/logs/modmail.log')
    ]
)
logger = logging.getLogger('ModMail')

# Ensure data directory exists
Path("data").mkdir(exist_ok=True)

class ModMail(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.staff_channel_id = 1259717946947670099  # Set this in setup
        self.data_file = "data/modmail.json"
        self.active_tickets = self.load_data()
    
    def load_data(self):
        """Load active tickets from JSON file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    # Convert thread IDs to integers (JSON stores them as strings)
                    return {k: int(v) for k, v in data.items()}
            return {}
        except Exception as e:
            logger.error(f"Failed to load modmail data: {e}")
            return {}
    
    def save_data(self):
        """Save active tickets to JSON file"""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.active_tickets, f)
        except Exception as e:
            logger.error(f"Failed to save modmail data: {e}")
    
    @commands.Cog.listener()
    async def on_ready(self):
        print(f"ModMail cog ready. Logged in as {self.bot.user}")
        # Initialize staff channel ID (replace with your channel ID)
        self.staff_channel_id = 1259717946947670099
    
    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore messages from bots
        if message.author.bot:
            return
            
        # Check if message is in DMs
        if isinstance(message.channel, discord.DMChannel):
            # Check if it's the first message (new modmail)
            if str(message.author.id) not in self.active_tickets:
                await self.create_new_modmail(message)
            else:
                await self.forward_to_thread(message)
        
        # Check if message is in a modmail thread and from staff
        elif (isinstance(message.channel, discord.Thread) and 
              message.channel.parent_id == self.staff_channel_id and
              not message.author.bot):
            await self.handle_staff_reply(message)
        
        # Update stats because DPY sucks with multiple on_message events that coincide with each other lol
        guilds = [1259717095382319215, 1299747094449623111, 1142088882222022786]
        if message.guild.id in guilds:
            with open("data/stats.json", "r") as f:
                data = json.load(f)
                data["stats"][str(message.guild.id)]["messages"] += 1
            with open("data/stats.json", "w") as f:
                json.dump(data, f, indent=2)
    
    async def create_new_modmail(self, user_message):
        """Create a new modmail thread for a user's DM"""
        staff_channel = self.bot.get_channel(self.staff_channel_id)
        if staff_channel is None:
            logger.error(f"Staff channel {self.staff_channel_id} not found!")
            return
        
        # Create initial embed
        embed = discord.Embed(
            title=f"New Modmail from {user_message.author}",
            description=user_message.content,
            color=0x00ff00
        )
        embed.set_thumbnail(url=user_message.author.avatar.url)
        embed.add_field(name="User ID", value=user_message.author.id)
        embed.add_field(name="Account Created", value=user_message.author.created_at.strftime("%Y-%m-%d %H:%M:%S"))
        
        # Send initial message and create thread
        try:
            staff_msg = await staff_channel.send(embed=embed)
            thread = await staff_msg.create_thread(
                name=f"Modmail {user_message.author}",
                auto_archive_duration=1440
            )
            
            # Store the thread ID
            self.active_tickets[str(user_message.author.id)] = thread.id
            self.save_data()
            
            # Send confirmation to user
            user_embed = discord.Embed(
                title="Modmail Received",
                description="Your message has been received by our staff team. "
                            "Please wait for a response. You can send additional "
                            "messages in this DM and they will be forwarded.",
                color=0x00ff00
            )
            await user_message.author.send(embed=user_embed)
        except Exception as e:
            logger.error(f"Failed to create modmail: {e}")
            await user_message.author.send("Failed to create your modmail ticket. Please try again later.")
    
    async def forward_to_thread(self, user_message):
        """Forward subsequent DMs to the existing thread"""
        thread_id = self.active_tickets.get(str(user_message.author.id))
        if not thread_id:
            logger.error(f"No thread ID found for user {user_message.author.id}")
            return
            
        try:
            thread = await self.bot.fetch_channel(thread_id)
            if thread is None:
                logger.error(f"Thread {thread_id} not found!")
                del self.active_tickets[str(user_message.author.id)]
                self.save_data()
                return
                
            # Create embed for the message
            embed = discord.Embed(
                description=user_message.content,
                color=0x7289da,
                timestamp=user_message.created_at
            )
            embed.set_author(name=user_message.author, icon_url=user_message.author.avatar.url)
            
            # Handle attachments
            if user_message.attachments:
                attachment_urls = []
                for attachment in user_message.attachments:
                    attachment_urls.append(f"[{attachment.filename}]({attachment.url})")
                embed.add_field(name="Attachments", value="\n".join(attachment_urls), inline=False)
            
            msg = await thread.send(embed=embed)
            await msg.add_reaction("✅")  # Success reaction
        except discord.NotFound:
            logger.error(f"Thread {thread_id} not found (404)")
            del self.active_tickets[str(user_message.author.id)]
            self.save_data()
            await user_message.author.send("Your previous modmail thread was not found. A new one will be created if you send another message.")
        except Exception as e:
            logger.error(f"Failed to forward message: {e}")
            await user_message.author.send("Failed to forward your message to staff. Please try again later.")
    
    async def handle_staff_reply(self, staff_message):
        """Handle staff replies in modmail threads"""
        # Skip if it's a command
        if staff_message.content.startswith("!"):
            return
            
        # Find the user ID for this thread
        user_id = None
        for uid, tid in self.active_tickets.items():
            if tid == staff_message.channel.id:
                user_id = int(uid)
                break
        
        if not user_id:
            return
            
        user = self.bot.get_user(user_id)
        if not user:
            return
            
        # Create embed for the user
        embed = discord.Embed(
            description=staff_message.content,
            color=0x7289da,
            timestamp=staff_message.created_at
        )
        embed.set_author(
            name=f"{staff_message.author} (Staff)",
            icon_url=staff_message.author.avatar.url
        )
        
        # Handle attachments
        if staff_message.attachments:
            attachment_urls = []
            for attachment in staff_message.attachments:
                attachment_urls.append(f"[{attachment.filename}]({attachment.url})")
            embed.add_field(name="Attachments", value="\n".join(attachment_urls), inline=False)
        
        try:
            await user.send(embed=embed)
            await staff_message.add_reaction("✅")  # Success reaction
        except discord.Forbidden:
            await staff_message.add_reaction("❌")  # Failure reaction
            await staff_message.channel.send("Failed to send message to user (user has DMs disabled)")
        except Exception as e:
            await staff_message.add_reaction("❌")  # Failure reaction
            await staff_message.channel.send(f"Failed to send message to user: {str(e)}")
    
    @commands.command(name="open", aliases=["openmail", "openmodmail", "omm", "mods"])
    async def open_modmail(self, ctx, message=None):
        """Open a new modmail thread"""
        if not message and len(message) < 15:
            return await ctx.reply("Please give a reason to open a new modmail thread. Dont spam it pls")
        await self.create_new_modmail(message)
        await ctx.message.add_reaction("✅")

    @commands.command(name="close", aliases=["closemail", "closemodmail", "cmm"])
    @commands.has_permissions(manage_messages=True)
    async def close_modmail(self, ctx):
        """Close the current modmail thread"""
        if not isinstance(ctx.channel, discord.Thread):
            await ctx.send("This command can only be used in modmail threads")
            return
            
        # Find the user ID for this thread
        user_id = None
        for uid, tid in self.active_tickets.items():
            if tid == ctx.channel.id:
                user_id = uid
                break
        
        if user_id:
            # Notify user
            user = self.bot.get_user(int(user_id))
            if user:
                try:
                    embed = discord.Embed(
                        title="Modmail Closed",
                        description="This modmail ticket has been closed by staff. "
                                  "If you have further questions, please open a new one.",
                        color=0xff0000
                    )
                    await user.send(embed=embed)
                except discord.HTTPException:
                    pass
            
            # Remove from active tickets
            del self.active_tickets[user_id]
            self.save_data()
        
        # Find the original message in the thread's parent channel
        try:
            # Get the parent channel
            parent_channel = self.bot.get_channel(ctx.channel.parent_id)
            if parent_channel:
                # Get the thread's starter message
                starter_message = await parent_channel.fetch_message(ctx.channel.id)
                if starter_message and starter_message.embeds:
                    # Edit the original embed to be red
                    original_embed = starter_message.embeds[0]
                    edited_embed = original_embed.copy()
                    edited_embed.color = 0xff0000  # Red color
                    await starter_message.edit(embed=edited_embed)
        except Exception as e:
            logger.error(f"Failed to edit original embed: {e}")
        
        # Archive thread
        await ctx.send("Closing this modmail ticket...")
        try:
            await ctx.channel.edit(archived=True, locked=True)
        except Exception as e:
            await ctx.send(f"Failed to archive thread: {e}")

async def setup(bot):
    try:
        await bot.add_cog(ModMail(bot))
        logger.info("ModMail cog loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load ModMail cog: {e}")
        raise e