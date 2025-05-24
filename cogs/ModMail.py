import discord
from discord.ext import commands
from discord.utils import get
import logging

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

class ModMail(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_tickets = {}  # {user_id: thread_id}
        self.staff_channel_id = 1259717946947670099  # Set this in setup
    
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
            if message.author.id not in self.active_tickets:
                await self.create_new_modmail(message)
            else:
                await self.forward_to_thread(message)
        
        # Check if message is in a modmail thread and from staff
        elif (isinstance(message.channel, discord.Thread) and 
              message.channel.parent_id == self.staff_channel_id and
              not message.author.bot):
            await self.handle_staff_reply(message)
    
    async def create_new_modmail(self, user_message):
        """Create a new modmail thread for a user's DM"""
        staff_channel = self.bot.get_channel(self.staff_channel_id)
        
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
        staff_msg = await staff_channel.send(embed=embed)
        thread = await staff_msg.create_thread(
            name=f"Modmail {user_message.author}",
            auto_archive_duration=1440
        )
        
        # Store the thread ID
        self.active_tickets[user_message.author.id] = thread.id
        
        # Send confirmation to user
        user_embed = discord.Embed(
            title="Modmail Received",
            description="Your message has been received by our staff team. "
                        "Please wait for a response. You can send additional "
                        "messages in this DM and they will be forwarded.",
            color=0x00ff00
        )
        await user_message.author.send(embed=user_embed)
    
    async def forward_to_thread(self, user_message):
        """Forward subsequent DMs to the existing thread"""
        thread_id = self.active_tickets.get(user_message.author.id)
        if not thread_id:
            return
            
        thread = self.bot.get_channel(thread_id)
        if not thread:
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
        
        try:
            msg = await thread.send(embed=embed)
            await msg.add_reaction("✅")  # Success reaction
        except discord.HTTPException:
            await thread.send("Failed to forward user message")
            await thread.send(f"User message: {user_message.content[:1900]}")
    
    async def handle_staff_reply(self, staff_message):
        """Handle staff replies in modmail threads"""
        # Get the user ID from the thread name or our active_tickets
        if staff_message.startswith("!"):
            return
        user_id = None
        for uid, tid in self.active_tickets.items():
            if tid == staff_message.channel.id:
                user_id = uid
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
        except discord.HTTPException:
            await staff_message.add_reaction("❌")  # Failure reaction
            await staff_message.channel.send("Failed to send message to user")
    
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
            user = self.bot.get_user(user_id)
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
        
        # Archive thread
        await ctx.send("Closing this modmail ticket...")
        await ctx.channel.edit(archived=True, locked=True)

async def setup(bot):
    try:
        await bot.add_cog(ModMail(bot))
        logger.info("ModMail cog loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load ModMail cog: {e}")
        raise e