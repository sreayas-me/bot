import discord
from discord.ext import commands
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('data/logs/Help.log')
    ]
)
logger = logging.getLogger('Help')

import discord
from discord.ext import commands
from discord.ui import View, Button

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help", aliases=["h"])
    async def help(self, ctx, *, command=None):
        """shows this help message"""
        if command:
            # Help for specific command
            cmd = self.bot.get_command(command.lower())
            if not cmd:
                return await ctx.reply(f"```no command found for '{command}'```")

            embed = discord.Embed(color=ctx.author.accent_color)
            embed.set_author(name=f"command help: {cmd.name}", icon_url=self.bot.user.display_avatar.url)

            description = f"```{cmd.help or 'no description provided'}```\n"
            description += f"```usage: {ctx.prefix}{cmd.name} {cmd.signature}```\n"

            if cmd.aliases:
                description += f"```aliases: {', '.join(cmd.aliases)}```"

            embed.description = description
            return await ctx.reply(embed=embed)

        # Paginated help menu by cog
        pages = []
        for cog_name, cog in self.bot.cogs.items():
            if cog_name.lower() in ['economy', 'help']:
                continue

            embed = discord.Embed(
                title=f"{cog_name} Commands",
                description="Use `.help <command>` for more details.",
                color=ctx.author.accent_color
            )
            embed.set_author(name="command list", icon_url=self.bot.user.display_avatar.url)
            commands_list = cog.get_commands()

            for cmd in commands_list:
                if cmd.hidden:
                    continue
                usage = f"{ctx.prefix}{cmd.name} {cmd.signature}"
                embed.add_field(
                    name=usage,
                    value=cmd.help or "no description provided",
                    inline=False
                )

            pages.append(embed)

        # Button-based pagination
        current_page = 0

        class Paginator(View):
            def __init__(self):
                super().__init__(timeout=60)
                self.message = None

            @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
            async def prev(self, interaction: discord.Interaction, button: Button):
                nonlocal current_page
                if interaction.user != ctx.author:
                    return await interaction.response.send_message("Not your paginator.", ephemeral=True)

                current_page = (current_page - 1) % len(pages)
                await interaction.response.edit_message(embed=pages[current_page], view=self)

            @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
            async def next(self, interaction: discord.Interaction, button: Button):
                nonlocal current_page
                if interaction.user != ctx.author:
                    return await interaction.response.send_message("Not your paginator.", ephemeral=True)

                current_page = (current_page + 1) % len(pages)
                await interaction.response.edit_message(embed=pages[current_page], view=self)

        view = Paginator()
        await ctx.reply(embed=pages[0], view=view)


async def setup(bot):
    try:
        await bot.add_cog(Help(bot))
        logger.info("help cog loaded successfully")
    except Exception as e:
        logger.error(f"failed to load help cog: {e}")
        raise e