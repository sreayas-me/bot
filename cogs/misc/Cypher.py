import random
import string
import asyncio
from discord.ext import commands

class Cypher(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    def generate_cipher_mapping(self, key):
        """Generate a cipher mapping based on the key"""
        # Use key as seed for reproducible randomization
        random.seed(key)
        
        # Characters to encrypt/decrypt
        chars = string.ascii_letters + string.digits + ' .,!?;:-_()[]{}@#$%^&*+=<>/\\|`~"\'`'
        
        # Create shuffled version for mapping
        shuffled_chars = list(chars)
        random.shuffle(shuffled_chars)
        
        # Create mapping dictionaries
        encrypt_map = str.maketrans(chars, ''.join(shuffled_chars))
        decrypt_map = str.maketrans(''.join(shuffled_chars), chars)
        
        return encrypt_map, decrypt_map
    
    @commands.command(aliases=['secret', 'encrypt'])
    async def cypher(self, ctx, key: str = None, *, text: str = None):
        """Send encrypted messages using a key-based cipher"""
        
        # Handle case where no arguments provided
        if not text and not key:
            await ctx.reply("```Please check your DMs!```")
            
            try:
                await ctx.author.send("""```What do you want to send?
Usage: cypher [key] [message]
Example: cypher mykey123 hello world

You can use a colon to separate the key and message:
mykey123:hello world (sending key and message at the same time)
mykey123 (sending just key, I will ask for message after)

Since you didn't provide any arguments, please send your KEY now:```""")
                
                def dm_check(m):
                    return m.author == ctx.author and isinstance(m.channel, ctx.author.dm_channel.__class__)
                
                # Wait for key in DMs
                key_msg = await self.bot.wait_for('message', check=dm_check, timeout=60)
                
                if ':' in key_msg.content:
                    key, text = key_msg.content.split(':', 1)
                else:
                    key = key_msg.content
                    await ctx.author.send("```Now please send your message to encrypt:```")
                    text_msg = await self.bot.wait_for('message', check=dm_check, timeout=60)
                    text = text_msg.content
                    
            except Exception as e:
                return await ctx.author.send("```Operation timed out or failed. Please try again.```")
        
        elif not key:
            return await ctx.reply("```Please provide a key```")
        
        elif not text:
            await ctx.reply("```Please provide the text to encrypt```")
            return
        
        # Validation
        if len(text) > 1900:  # Leave room for formatting
            return await ctx.reply("```Text too long (max 1900 chars to allow for encryption overhead)```")
        
        if len(key) > 50:
            return await ctx.reply("```Key too long (max 50 chars)```")
        
        if len(key) < 3:
            return await ctx.reply("```Key too short (min 3 chars)```")
        
        # Generate cipher mapping and encrypt
        try:
            encrypt_map, _ = self.generate_cipher_mapping(key)
            encrypted_text = text.translate(encrypt_map)
            
            # Send encrypted message to DMs
            embed_content = f"**🔐 Encrypted Message**\n```\nKey: {key}\nOriginal: {text[:100]}{'...' if len(text) > 100 else ''}\nEncrypted: {encrypted_text}\n```"
            
            await ctx.author.send(embed_content)
            
        except Exception as e:
            await ctx.reply(f"```Encryption failed: {str(e)}```")
    
    @commands.command(aliases=['decrypt'])
    async def decypher(self, ctx, key: str = None, *, text: str = None):
        """Decrypt encrypted messages using the same key"""
        
        # Handle missing arguments
        if not key or not text:
            await ctx.reply("```Please check your DMs!```")
            
            try:
                await ctx.author.send("""```What do you want to send?
Usage: decypher [key] [message]
Example: decypher mykey123 hello world

You can use a colon to separate the key and message:
mykey123:hello world (sending key and message at the same time)
mykey123 (sending just key, I will ask for message after)

Since you didn't provide any arguments, please send your KEY now:```""")
                
                def dm_check(m):
                    return m.author == ctx.author and isinstance(m.channel, ctx.author.dm_channel.__class__)
                
                # Wait for key in DMs
                key_msg = await self.bot.wait_for('message', check=dm_check, timeout=60)
                
                if ':' in key_msg.content:
                    key, text = key_msg.content.split(':', 1)
                else:
                    key = key_msg.content
                    await ctx.author.send("```Now please send your message to encrypt:```")
                    text_msg = await self.bot.wait_for('message', check=dm_check, timeout=60)
                    text = text_msg.content
                    
            except Exception as e:
                return await ctx.author.send("```Operation timed out or failed. Please try again.```")
        
        # Validation
        if len(text) > 2000:
            return await ctx.reply("```Text too long (max 2000 chars)```")
        
        if len(key) > 50:
            return await ctx.reply("```Key too long (max 50 chars)```")
        
        if len(key) < 3:
            return await ctx.reply("```Key too short (min 3 chars)```")
        
        # Generate cipher mapping and decrypt
        try:
            _, decrypt_map = self.generate_cipher_mapping(key)
            decrypted_text = text.translate(decrypt_map)
            
            # Send decrypted message to DMs
            embed_content = f"**🔓 Decrypted Message**\n```\nKey: {key}\nEncrypted: {text[:100]}{'...' if len(text) > 100 else ''}\nDecrypted: {decrypted_text}\n```"
            await ctx.author.send(embed_content)
            
        except Exception as e:
            await ctx.reply(f"```Decryption failed: {str(e)} (wrong key?)```")
    
    @commands.command(aliases=['testcipher'])
    async def cipher_test(self, ctx, key: str = None, *, text: str = None):
        """Test the cipher system interactively
        Usage: 
        - cipher_test <key> [message]  (in channel)
        - cipher_test                  (starts DM wizard)"""
        
        # If no arguments provided, start DM wizard
        if not key:
            await ctx.reply("```Please check your DMs to continue!```")
            try:
                # Start interactive DM session
                await self.process_cipher_test(ctx, key, text)
            except Exception as e:
                await ctx.author.send(f"```❌ Error: {str(e)}```")
                await ctx.reply("```Failed to complete DM interaction. Please try again.```")
            return
        
        # Process with provided arguments
        await self.process_cipher_test(ctx, key, text or "Hello World! This is a test message 123.")

    async def cipher_test_dm_wizard(self, user):
        """Interactive DM wizard for cipher testing"""
        def dm_check(m):
            return m.author == user and isinstance(m.channel, user.dm_channel.__class__)
        
        # Step 1: Get key
        await user.send("""```🔐 Cipher Test Wizard
    Please send your encryption KEY (or type 'cancel' to abort):
    You can include your message after a colon like:
    mykey123:Hello world```""")
        
        try:
            # Wait for key input
            key_msg = await self.bot.wait_for('message', check=dm_check, timeout=120)
            if key_msg.content.lower() == 'cancel':
                return await user.send("```❌ Operation cancelled```")
            
            # Parse key and message
            if ':' in key_msg.content:
                key, text = key_msg.content.split(':', 1)
                text = text.strip()
            else:
                key = key_msg.content
                # Step 2: Get message if not provided
                await user.send("""```✉ Now please send your MESSAGE to encrypt
    (or type 'sample' to use default test message):```""")
                text_msg = await self.bot.wait_for('message', check=dm_check, timeout=120)
                text = "Hello World! This is a test message 123." if text_msg.content.lower() == 'sample' else text_msg.content
        
            # Process the cipher test
            await self.process_cipher_test(None, key, text, user=user)
            
        except asyncio.TimeoutError:
            await user.send("```⌛ Timeout: You took too long to respond```")
        except Exception as e:
            await user.send(f"```❌ Error: {str(e)}```")
            raise

    async def process_cipher_test(self, ctx, key, text, user=None):
        """Process cipher test and send results with automatic cipher detection"""
        target = user or ctx.author
        
        try:
            # Generate cipher mappings
            encrypt_map, decrypt_map = self.generate_cipher_mapping(key)
            
            # Detect if text appears to be already encrypted
            likely_encrypted = self.is_likely_encrypted(text)
            
            # Process based on detection
            if likely_encrypted:
                # Double decrypt if input appears encrypted
                decrypted_once = text.translate(decrypt_map)
                decrypted_twice = decrypted_once.translate(decrypt_map)
                
                # Also show what encryption of the decrypted text would look like
                encrypted_version = decrypted_once.translate(encrypt_map)
                
                result = (
                    f"```🔐 Cipher Test Results (Detected Encrypted Input)\n"
                    f"Key: {key}\n\n"
                    f"Original:       {text}\n"
                    f"After 1st pass: {decrypted_once}\n"
                    f"After 2nd pass: {decrypted_twice}\n"
                    f"Re-encrypted:   {encrypted_version}\n\n"
                    f"Note: Input appeared encrypted - showing decryption results```"
                )
            else:
                # Normal encryption/decryption flow
                encrypted = text.translate(encrypt_map)
                decrypted = encrypted.translate(decrypt_map)
                success = (decrypted == text)
                
                result = (
                    f"```🔐 Cipher Test Results\n"
                    f"Key: {key}\n"
                    f"Original:  {text}\n"
                    f"Encrypted: {encrypted}\n"
                    f"Decrypted: {decrypted}\n\n"
                    f"Round-trip: {'✅ SUCCESS' if success else '❌ FAILED'}```"
                )
            
            await target.send(result)
            if ctx and hasattr(ctx, 'reply'):  # More robust check for ctx
                reply_msg = ("```🔍 Test complete (encrypted input detected) - check DMs!```" 
                            if likely_encrypted 
                            else "```✅ Test complete - check your DMs!```")
                await ctx.reply(reply_msg)       
        except Exception as e:
            error_msg = f"```❌ Cipher Test Failed\nError: {str(e)}```"
            await target.send(error_msg)
            if ctx and hasattr(ctx, 'reply'):
                await ctx.reply("```❌ Test failed - check your DMs for details```")

    def is_likely_encrypted(self, text):
        """Heuristic to detect if text is likely encrypted"""
        # Check for high percentage of non-alphanumeric characters
        non_alpha = sum(1 for c in text if not c.isalnum() and not c.isspace())
        ratio = non_alpha / len(text) if text else 0
        
        # Check for unusual character distribution
        common_chars = sum(1 for c in text.lower() if c in 'etaoin shrdlu')
        uncommon_ratio = 1 - (common_chars / len(text)) if text else 0
        
        # Likely encrypted if:
        # 1. High non-alphanumeric ratio (>40%), or
        # 2. Very uncommon character distribution (>80% uncommon)
        return ratio > 0.4 or uncommon_ratio > 0.8

async def setup(bot):
    await bot.add_cog(Cypher(bot))