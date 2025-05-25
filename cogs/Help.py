import discord
from discord.ext import commands
from cogs.logging.logger import CogLogger

logger = CogLogger('Help')


class HelpPaginator(discord.ui.View):
    def __init__(self, pages, author, timeout=180):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.author = author
        self.current_page = 0
        self.message = None
        
        # Update button states
        self.update_buttons()
    
    def update_buttons(self):
        """Update button states based on current page"""
        self.prev_button.disabled = len(self.pages) <= 1
        self.next_button.disabled = len(self.pages) <= 1
        
        # Update labels to show page numbers
        if len(self.pages) > 1:
            self.page_info.label = f"{self.current_page + 1}/{len(self.pages)}"
    
    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary, custom_id="prev")
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            return await interaction.response.send_message("This isn't your help menu!", ephemeral=True)
        
        self.current_page = (self.current_page - 1) % len(self.pages)
        self.update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)
    
    @discord.ui.button(label="1/1", style=discord.ButtonStyle.primary, custom_id="page_info", disabled=True)
    async def page_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass  # This button is just for display
    
    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary, custom_id="next")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            return await interaction.response.send_message("This isn't your help menu!", ephemeral=True)
        
        self.current_page = (self.current_page + 1) % len(self.pages)
        self.update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)
    
    @discord.ui.button(label="🗑️", style=discord.ButtonStyle.danger, custom_id="delete")
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            return await interaction.response.send_message("Only the command author can delete this!", ephemeral=True)
        
        await interaction.response.defer()
        if self.message:
            await self.message.delete()
    
    async def on_timeout(self):
        """Disable all buttons when the view times out"""
        for item in self.children:
            item.disabled = True
        
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                pass  # Message was already deleted


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="help", aliases=["h", "commands"])
    async def help(self, ctx, *, command=None):
        """Shows help information for commands"""
        
        if command:
            # Check if it's a cog first
            cog = self.bot.get_cog(command.title())
            if cog and hasattr(cog, 'get_command_help'):
                pages = cog.get_command_help()
                if pages:
                    view = HelpPaginator(pages, ctx.author)
                    view.update_buttons()
                    message = await ctx.reply(embed=pages[0], view=view)
                    view.message = message
                    return

            # Help for specific command
            cmd = self.bot.get_command(command.lower())
            if not cmd:
                embed = discord.Embed(
                    title="❌ Command Not Found",
                    description=f"No command found for `{command}`",
                    color=discord.Color.red()
                )
                return await ctx.reply(embed=embed)
            
            embed = discord.Embed(
                title=f"📖 Command: {cmd.name}",
                color=ctx.author.accent_color or discord.Color.blue()
            )
            embed.set_author(name="Command Help", icon_url=self.bot.user.display_avatar.url)
            
            # Description
            description = cmd.help or "No description provided"
            embed.add_field(name="Description", value=f"```{description}```", inline=False)
            
            # Usage
            usage = f"{ctx.prefix}{cmd.name} {cmd.signature}".strip()
            embed.add_field(name="Usage", value=f"```{usage}```", inline=False)
            
            # Aliases
            if cmd.aliases:
                aliases = ", ".join([f"`{alias}`" for alias in cmd.aliases])
                embed.add_field(name="Aliases", value=aliases, inline=False)
            
            # Cooldown info if exists
            if cmd.cooldown:
                cooldown_info = f"{cmd.cooldown.rate} times per {cmd.cooldown.per} seconds"
                embed.add_field(name="Cooldown", value=cooldown_info, inline=False)
            
            return await ctx.reply(embed=embed)
        
        # Paginated help menu by cog
        pages = []
        total_commands = 0
        
        # Sort cogs alphabetically
        sorted_cogs = sorted(self.bot.cogs.items(), key=lambda x: x[0].lower())
        
        for cog_name, cog in sorted_cogs:
            # Skip certain cogs
            if cog_name.lower() in ['help', 'jishaku', 'dev', 'moderation', 'giveaway']:
                continue
            
            # Get visible commands
            commands_list = [cmd for cmd in cog.get_commands() if not cmd.hidden]
            if not commands_list:
                continue
            
            embed = discord.Embed(
                title=f"📚 {cog_name} Commands",
                description=f"Use `{ctx.prefix}help <command>` for detailed information about a command.",
                color=ctx.author.accent_color or discord.Color.blue()
            )
            embed.set_author(
                name=f"{self.bot.user.name} Help Menu", 
                icon_url=self.bot.user.display_avatar.url
            )
            
            # Add commands to embed
            for cmd in sorted(commands_list, key=lambda x: x.name):
                usage = f"{ctx.prefix}{cmd.name} {cmd.signature}".strip()
                description = cmd.help or "No description provided"
                
                # Truncate long descriptions
                if len(description) > 100:
                    description = description[:97] + "..."
                
                embed.add_field(
                    name=f"**{usage}**",
                    value=description,
                    inline=False
                )
                total_commands += 1
            
            # Add footer with command count for this cog
            embed.set_footer(text=f"{len(commands_list)} commands in this category")
            pages.append(embed)
        
        if not pages:
            embed = discord.Embed(
                title="❌ No Commands Available",
                description="No visible commands found.",
                color=discord.Color.red()
            )
            return await ctx.reply(embed=embed)
        
        # Add overview page at the beginning
        overview_embed = discord.Embed(
            title=f"📖 {self.bot.user.name} Help Menu",
            description=f"Welcome to the help menu! Use the buttons below to navigate through different command categories.\n\n"
                       f"**Total Commands:** {total_commands}\n"
                       f"**Categories:** {len(pages)}\n\n"
                       f"Use `{ctx.prefix}help <command>` for detailed information about a specific command.",
            color=ctx.author.accent_color or discord.Color.blue()
        )
        overview_embed.set_author(
            name=f"{self.bot.user.name} Bot", 
            icon_url=self.bot.user.display_avatar.url
        )
        overview_embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        
        # Insert overview at the beginning
        pages.insert(0, overview_embed)
        
        # Create and send paginator
        view = HelpPaginator(pages, ctx.author)
        view.update_buttons()
        message = await ctx.reply(embed=pages[0], view=view)
        view.message = message


async def setup(bot):
    try:
        await bot.add_cog(Help(bot))
        logger.info("Help cog loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load Help cog: {e}")
        raise e