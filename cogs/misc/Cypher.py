import random
import string
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
    async def cipher_test(self, ctx, key: str = None):
        """Test the cipher with a sample message"""
        if not key:
            return await ctx.reply("```Usage: cipher_test [key]```")
        
        test_message = "Hello World! This is a test message 123."
        
        try:
            encrypt_map, decrypt_map = self.generate_cipher_mapping(key)
            encrypted = test_message.translate(encrypt_map)
            decrypted = encrypted.translate(decrypt_map)
            
            result = f"""```🧪 Cipher Test Results
Key: {key}
Original:  {test_message}
Encrypted: {encrypted}
Decrypted: {decrypted}
Success: {test_message == decrypted}```"""
            
            await ctx.author.send(result)
            await ctx.reply("```Test results sent to your DMs```")
            
        except Exception as e:
            await ctx.reply(f"```Test failed: {str(e)}```")

async def setup(bot):
    await bot.add_cog(Cypher(bot))