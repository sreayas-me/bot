import discord
from discord.ext import commands
import json
from pathlib import Path
from datetime import datetime, timedelta

class VoteBans(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.vote_channel_id = 1367979611748696284
        self.staff_role_id = 1259728436377817100
        self.required_votes = 25
        self.ban_threshold = 15
        self.timeout_duration = timedelta(days=7)
        self.data_path = Path("data/votebans.json")
        self.vote_data = self.load_data()
        
    def load_data(self):
        try:
            with open(self.data_path) as f:
                data = json.load(f)
                if "votes" in data and isinstance(data["votes"], dict):
                    new_data = {}
                    for vote_id, vote_info in data["votes"].items():
                        user_id = str(vote_info["user_id"])
                        new_data[user_id] = {
                            "user_id": vote_info["user_id"],
                            "initiator": vote_info["initiator"],
                            "message_id": vote_info["message_id"],
                            "channel_id": vote_info["channel_id"],
                            "jump_url": vote_info.get("jump_url", ""),
                            "reason": vote_info["reason"],
                            "votes": vote_info["votes"],
                            "advocates": {},
                            "completed": vote_info["completed"]
                        }
                        if str(user_id) in data.get("advocates", {}):
                            for advocate_id in data["advocates"][str(user_id)]:
                                advocate = self.bot.get_user(advocate_id)
                                new_data[user_id]["advocates"][str(advocate_id)] = {
                                    "reason": "Previous vote",
                                    "timestamp": datetime.utcnow().isoformat(),
                                    "username": advocate.name if advocate else "Unknown"
                                }
                    return new_data
                return data
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def save_data(self):
        self.data_path.parent.mkdir(exist_ok=True)
        with open(self.data_path, "w") as f:
            json.dump(self.vote_data, f, indent=2, default=str)
    
    async def is_staff(self, member):
        staff_role = member.guild.get_role(self.staff_role_id)
        return staff_role in member.roles if staff_role else False
    
    @commands.command(name="vban", aliases=["voteban", "vote", "kill", "vb", "ban"])
    async def voteban(self, ctx, user: discord.Member=None, *, reason="No reason provided"):
        if not user:
            embed = discord.Embed(
                title="Vote Ban",
                description="""
                **Usage:**
                `!vban <user> <reason>`
                > *vb, voteban, vote, kill, ban, vban*
                
                **Example:**
                `!vban ks.net gay`
                `!vban @ks.net gay`
                `!vban 814226043924643880 still gay`
                """,
                color=discord.Colour.random(),
                timestamp=datetime.now()
            )
            return await ctx.send(embed=embed)
        if user.id == ctx.author.id:
            return await ctx.send("You can't vote ban yourself!", delete_after=10)
            
        if await self.is_staff(user) or await self.is_staff(ctx.author):
            return await ctx.send("You can't vote ban (or vote as) a staff member!", delete_after=10)
            
        if user.bot:
            return await ctx.send("You can't vote ban bots!", delete_after=10)

        user_id_str = str(user.id)

        # If vote already exists, update advocates and edit embed
        if user_id_str in self.vote_data and not self.vote_data[user_id_str].get("completed", True):
            existing_vote = self.vote_data[user_id_str]
            
            # Add this user as an advocate
            existing_vote["advocates"][str(ctx.author.id)] = {
                "reason": reason,
                "timestamp": datetime.now().isoformat(),
                "username": ctx.author.name
            }

            # Update embed with new advocate list
            channel = self.bot.get_channel(existing_vote["channel_id"])
            message = await channel.fetch_message(existing_vote["message_id"])

            embed = message.embeds[0]
            embed.clear_fields()
            
            # Rebuild the embed fields
            advocate_text = []
            for advocate_id, advocate_data in existing_vote["advocates"].items():
                advocate_text.append(
                    f"• **{advocate_data['username']}** - \"{advocate_data['reason']}\" "
                    f"(<t:{int(datetime.fromisoformat(advocate_data['timestamp']).timestamp())}:R>)"
                )
            if advocate_text:
                embed.add_field(
                    name="Advocates",
                    value="\n".join(advocate_text),
                    inline=False
                )

            await message.edit(embed=embed)
            self.save_data()

            return await ctx.send(
                f"You've been added as an advocate for {user.mention}'s vote ban.\n"
                f"Vote here: {existing_vote['jump_url']}"
            )

        # Create a new vote embed
        embed = discord.Embed(
            title=f"Vote Ban: {user.display_name}",
            description=f"**Reason:** {reason}\n\nVote ✅ to ban, ❌ to keep\n{self.required_votes} votes needed to decide",
            color=0xff0000,
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=user.avatar.url)
        embed.set_footer(text=f"Started by {ctx.author.display_name}")

        # Send embed to vote channel
        vote_channel = self.bot.get_channel(self.vote_channel_id)
        vote_msg = await vote_channel.send(embed=embed)
        await vote_msg.add_reaction("✅")
        await vote_msg.add_reaction("❌")

        # Store vote data
        self.vote_data[user_id_str] = {
            "user_id": user.id,
            "initiator": ctx.author.id,
            "message_id": vote_msg.id,
            "channel_id": vote_channel.id,
            "jump_url": vote_msg.jump_url,
            "reason": reason,
            "votes": {"✅": [], "❌": []},
            "advocates": {
                str(ctx.author.id): {
                    "reason": reason,
                    "timestamp": datetime.utcnow().isoformat(),
                    "username": ctx.author.name
                }
            },
            "completed": False
        }

        self.save_data()

        await ctx.send(
            f"Vote started for {user.mention}!\n"
            f"Vote here: {vote_msg.jump_url}"
        )

    
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return
            
        # Find vote by message_id
        user_id_str = None
        vote_info = None
        for uid, data in self.vote_data.items():
            if uid == "advocates":
                continue
            if "message_id" in data and data["message_id"] == reaction.message.id:
                user_id_str = uid
                vote_info = data
                break
        
        if not vote_info or vote_info.get("completed", True):
            return
            
        if str(reaction.emoji) not in ["✅", "❌"]:
            return
            
        try:
            channel = self.bot.get_channel(vote_info["channel_id"])
            message = await channel.fetch_message(vote_info["message_id"])
        except discord.NotFound:
            return
        
        # Check if voter is staff
        try:
            voter = await channel.guild.fetch_member(user.id)
            if await self.is_staff(voter):
                await message.remove_reaction(reaction.emoji, user)
                return
        except discord.NotFound:
            return
            
        # Update votes
        for emoji in ["✅", "❌"]:
            if user.id in vote_info["votes"][emoji]:
                vote_info["votes"][emoji].remove(user.id)
                try:
                    await message.remove_reaction(emoji, user)
                except discord.HTTPException:
                    pass
        
        vote_info["votes"][str(reaction.emoji)].append(user.id)
        self.save_data()
        
        # Edit message to update counts
        embed = message.embeds[0]
        yes_votes = len(vote_info["votes"]["✅"])
        no_votes = len(vote_info["votes"]["❌"])
        
        # Update embed description with current counts
        embed.description = (
            f"**Reason:** {vote_info['reason']}\n\n"
            f"Vote ✅ to ban ({yes_votes}), ❌ to keep ({no_votes})\n"
            f"{self.required_votes} votes needed to decide"
        )
        
        # Keep existing advocate field if present
        await message.edit(embed=embed)
        
        # Check if vote complete
        total_votes = yes_votes + no_votes
        if total_votes >= self.required_votes:
            await self.complete_vote(user_id_str, message)
    
    async def complete_vote(self, user_id_str, message):
        vote_info = self.vote_data[user_id_str]
        vote_info["completed"] = True
        self.save_data()
        
        yes_votes = len(vote_info["votes"]["✅"])
        no_votes = len(vote_info["votes"]["❌"])
        advocate_bonus = len(vote_info.get("advocates", {})) * 3
        total_score = yes_votes - no_votes + advocate_bonus
        
        guild = message.guild
        target_user = guild.get_member(int(user_id_str))
        
        embed = message.embeds[0]
        
        # Build final embed
        embed.description = (
            f"**Reason:** {vote_info['reason']}\n\n"
            f"**Voting Complete!**\n"
            f"✅ {yes_votes} votes | ❌ {no_votes} votes\n"
            f"Advocate bonus: +{advocate_bonus}\n"
            f"**Final Score:** {total_score}\n\n"
        )
        
        if total_score >= self.ban_threshold:
            if target_user:
                try:
                    await target_user.timeout(self.timeout_duration, reason="Vote ban result")
                    embed.description += f"\n**Result:** {target_user.mention} has been timed out for 1 week!"
                    embed.color = 0xff0000
                except discord.Forbidden:
                    embed.description += "\n**Result:** Failed to timeout user (missing permissions)"
                    embed.color = 0xffff00
                except discord.HTTPException:
                    embed.description += "\n**Result:** Error timing out user"
                    embed.color = 0xffff00
            else:
                embed.description += "\n**Result:** User not found in server"
                embed.color = 0xffff00
        else:
            embed.description += "\n**Result:** User will not be banned (score below threshold)"
            embed.color = 0x00ff00
        
        await message.edit(embed=embed)
        await message.clear_reactions()
    
    @commands.command(name="votestats", aliases=["vs"])
    async def vote_stats(self, ctx, user: discord.Member = None):
        if not user:
            return await ctx.send("Please specify a user to check stats for.", delete_after=10)
            
        user_id_str = str(user.id)
        embed = discord.Embed(
            title=f"Vote Stats for {user.display_name}",
            color=0x7289da
        )
        embed.set_thumbnail(url=user.avatar.url)
        
        if user_id_str in self.vote_data:
            vote_info = self.vote_data[user_id_str]
            
            # Show current vote status if active
            if not vote_info.get("completed", True):
                yes_votes = len(vote_info["votes"]["✅"])
                no_votes = len(vote_info["votes"]["❌"])
                embed.add_field(
                    name="Current Vote",
                    value=f"✅ {yes_votes} | ❌ {no_votes}\n"
                         f"Needs {self.required_votes} total votes\n"
                         f"[Jump to Vote]({vote_info['jump_url']})",
                    inline=False
                )
            
            # Show advocates
            if vote_info.get("advocates", {}):
                advocate_text = []
                for advocate_id, advocate_data in vote_info["advocates"].items():
                    advocate_text.append(
                        f"• **{advocate_data['username']}** - \"{advocate_data['reason']}\" "
                        f"(<t:{int(datetime.fromisoformat(advocate_data['timestamp']).timestamp())}:R>)"
                    )
                embed.add_field(
                    name="Advocates",
                    value="\n".join(advocate_text),
                    inline=False
                )
        else:
            embed.description = "No vote history found for this user."
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(VoteBans(bot))