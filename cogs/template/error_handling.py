# Example template for command error handling in cogs

@command_name.error
async def command_error(self, ctx, error):
    """Error handler for specific command"""
    # Get error details
    command = ctx.command.qualified_name
    author = f"{ctx.author} ({ctx.author.id})"
    guild = f"{ctx.guild} ({ctx.guild.id})" if ctx.guild else "DM"
    
    # Full error trace for logging
    error_trace = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
    
    # Log the error
    self.logger.error(
        f"Error in {command}:\n"
        f"User: {author}\n"
        f"Guild: {guild}\n"
        f"Error: {str(error)}\n"
        f"Traceback:\n{error_trace}"
    )
    
    # Handle specific error types
    if isinstance(error, commands.MissingPermissions):
        await ctx.reply(
            f"❌ You need {', '.join(error.missing_permissions)} permission(s) to use this command!"
        )
    elif isinstance(error, commands.BadArgument):
        await ctx.reply(f"❌ Invalid argument: {str(error)}")
    else:
        error_id = hex(abs(hash(str(error))))[-6:]
        await ctx.reply(
            f"❌ An error occurred with this command! Error ID: `{error_id}`\n"
            "This has been logged and will be investigated."
        )
