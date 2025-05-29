import discord
import json
from discord.ext import commands
from cogs.logging.logger import CogLogger
from utils.error_handler import ErrorHandler

logger = CogLogger('Help')
with open('data/config.json', 'r') as f:
    data = json.load(f)
BOT_ADMINS = data['OWNER_IDS']

class HelpPaginator(discord.ui.View):
    def __init__(self, pages, author, timeout=180):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.author = author
        self.current_page = 0
        self.message = None
        self.cog_page_map = {}  # Maps cog names to page indices
        
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
    
    @discord.ui.select(
        placeholder="Jump to category...",
        custom_id="category_select",
        row=1
    )
    async def select_category(self, interaction: discord.Interaction, select: discord.ui.Select):
        if interaction.user != self.author:
            return await interaction.response.send_message("This isn't your help menu!", ephemeral=True)
        
        self.current_page = int(select.values[0])
        self.update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    async def on_timeout(self):
        """Disable all buttons when the view times out"""
        for item in self.children:
            item.disabled = True
        
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                pass  # Message was already deleted


class Help(commands.Cog, ErrorHandler):
    def __init__(self, bot):
        ErrorHandler.__init__(self)
        self.bot = bot
    
    @commands.command(name="invite", aliases=["add"])
    async def invite(self, ctx):
        await ctx.reply(embed=discord.Embed(
            description=f"[Invite me](https://bronxbot.onrender.com/invite) to your server\nIf that link doesnt work [click here](https://discord.com/oauth2/authorize?client_id=828380019406929962&permissions=8&response_type=code&redirect_uri=https%3A%2F%2Fbronxbot.onrender.com%2Fcallback&integration_type=0&scope=identify+guilds+bot)",
            color=discord.Color.green()
        ))

    @commands.command(name="help", aliases=["h", "commands"])
    async def help(self, ctx, *, command=None):
        if command:
            # Check if it's a cog first
            cog = self.bot.get_cog(command)
            if cog:
                # Help for a cog
                commands_list = cog.get_commands()
                if not commands_list:
                    return await ctx.reply(embed=discord.Embed(
                        description=f"no commands found in `{cog.qualified_name}`",
                        color=discord.Color.red()
                    ))
                
                embed = discord.Embed(
                    title=f"{cog.qualified_name} commands",
                    description="\n".join(
                        f"`{ctx.prefix}{cmd.name} {cmd.signature}` - {cmd.help or 'no description'}"
                        for cmd in sorted(commands_list, key=lambda x: x.name)
                    ),
                    color=ctx.author.accent_color or discord.Color.blue()
                )
                embed.set_footer(text=f"{len(commands_list)} commands")
                return await ctx.reply(embed=embed)

            # Help for specific command
            cmd = self.bot.get_command(command.lower())
            if not cmd:
                return await ctx.reply(embed=discord.Embed(
                    description=f"couldn't find command `{command}`",
                    color=discord.Color.red()
                ))
            
            embed = discord.Embed(
                description=(
                    f"`{ctx.prefix}{cmd.name} {cmd.signature}`\n"
                    f"{cmd.help or 'no description'}\n"
                    + (f"\n**aliases:** {', '.join([f'`{a}`' for a in cmd.aliases])}" if cmd.aliases else "")
                ),
                color=ctx.author.accent_color or discord.Color.blue()
            )
            return await ctx.reply(embed=embed)
        
        # Paginated help menu
        pages = []
        total_commands = 0
        cog_page_map = {}
        page_index = 1  # Start at 1 because overview is at 0
        
        for cog_name, cog in sorted(self.bot.cogs.items(), key=lambda x: x[0].lower()):
            if cog_name.lower() in ['help', 'jishaku', 'dev', 'moderation', 'votebans', 'stats', 'welcoming']:
                continue

            if ctx.author.id not in BOT_ADMINS and cog_name.lower() in ['admin', 'owner']:
                continue
            
            commands_list = [cmd for cmd in cog.get_commands() if not cmd.hidden]
            if not commands_list:
                continue

            cog_page_map[cog_name] = page_index
            page_index += 1

            embed = discord.Embed(
                description=f"**{cog_name.lower()}**\n\n",
                color=ctx.author.accent_color or discord.Color.blue()
            )
            
            for cmd in sorted(commands_list, key=lambda x: x.name):
                usage = f"{ctx.prefix}{cmd.name} {cmd.signature}".strip()
                description = cmd.help or "no description"
                if len(description) > 80:
                    description = description[:77] + "..."
                embed.description += f"`{usage}`\n{description}\n\n"
                total_commands += 1
            
            embed.set_footer(text=f"{len(commands_list)} commands")
            pages.append(embed)

        # Overview page
        overview_embed = discord.Embed(
            description=(
                f"`{ctx.prefix}help <command>` for details\n\n"
                f"**commands:** {total_commands}\n"
                f"**categories:** {len(pages)}"
            ),
            color=ctx.author.accent_color or discord.Color.blue()
        )
        pages.insert(0, overview_embed)
        
        # Create and send paginator
        view = HelpPaginator(pages, ctx.author)
        
        # Add select menu options
        select = view.select_category
        select.add_option(label="Overview", value="0", description="View all categories")
        for cog_name, page_num in cog_page_map.items():
            select.add_option(
                label=cog_name,
                value=str(page_num),
                description=f"View {cog_name.lower()} commands"
            )
        
        view.update_buttons()
        message = await ctx.reply(embed=pages[0], view=view)
        view.message = message
        view.cog_page_map = cog_page_map

    @help.error
    async def help_error(self, ctx, error):
        """Handle help command errors"""
        if isinstance(error, commands.CommandNotFound):
            await ctx.reply("❌ Command not found!")
        else:
            await self.handle_error(ctx, error, "help")


async def setup(bot):
    try:
        await bot.add_cog(Help(bot))
    except Exception as e:
        logger.error(f"Failed to load Help cog: {e}")
        raise e