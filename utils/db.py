import motor.motor_asyncio
import pymongo
import json
import datetime
import os
import asyncio
import logging
from typing import Dict, Any, Optional
import threading

# Initialize default config
config = {
    "MONGO_URI": os.getenv("MONGO_URI"),
    "TOKEN": os.getenv("DISCORD_TOKEN"),
    "CLIENT_ID": os.getenv("DISCORD_CLIENT_ID"),
    "CLIENT_SECRET": os.getenv("DISCORD_CLIENT_SECRET"),
    "OWNER_ID": os.getenv("DISCORD_BOT_OWNER_ID")
}

# Try to load from config file if environment variables are not set
if not all([config["MONGO_URI"], config["TOKEN"], config["CLIENT_ID"]]):
    try:
        with open('data/config.json') as f:
            file_config = json.load(f)
            # Update config with file values only if env vars are not set
            for key in config:
                if not config[key] and key in file_config:
                    config[key] = file_config[key]
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.warning(f"Could not load config.json: {e}. Using environment variables only.")

class AsyncDatabase:
    """Async database class for use with Discord bot"""
    _instance = None
    _client = None
    _db = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.logger = logging.getLogger('AsyncDatabase')
        self._connected = False

    @property
    def client(self):
        if self._client is None:
            MONGO_URI = os.getenv('MONGO_URI', config['MONGO_URI'])
            self._client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
        return self._client
        
    @property
    def db(self):
        if self._db is None:
            self._db = self.client.bronxbot
        return self._db

    async def ensure_connected(self) -> bool:
        """Ensure database connection is active"""
        if not self._connected:
            try:
                await self.client.admin.command('ping')
                self._connected = True
                self.logger.info("Async database connection established")
            except Exception as e:
                self.logger.error(f"Async database connection failed: {e}")
                return False
        return True

    async def get_wallet_balance(self, user_id: int, guild_id: int = None) -> int:
        """Get user's wallet balance"""
        if not await self.ensure_connected():
            return 0
        user = await self.db.users.find_one({"_id": str(user_id)})
        return user.get("wallet", 0) if user else 0

    async def get_bank_balance(self, user_id: int, guild_id: int = None) -> int:
        """Get user's bank balance"""
        if not await self.ensure_connected():
            return 0
        user = await self.db.users.find_one({"_id": str(user_id)})
        return user.get("bank", 0) if user else 0

    async def get_bank_limit(self, user_id: int, guild_id: int = None) -> int:
        """Get user's bank limit"""
        if not await self.ensure_connected():
            return 10000
        user = await self.db.users.find_one({"_id": str(user_id)})
        return user.get("bank_limit", 10000) if user else 10000

    async def update_wallet(self, user_id: int, amount: int, guild_id: int = None) -> bool:
        """Update user's wallet balance"""
        if not await self.ensure_connected():
            return False
        result = await self.db.users.update_one(
            {"_id": str(user_id)},
            {"$inc": {"wallet": amount}},
            upsert=True
        )
        return result.modified_count > 0 or result.upserted_id is not None

    async def update_bank(self, user_id: int, amount: int, guild_id: int = None) -> bool:
        """Update user's bank balance"""
        if not await self.ensure_connected():
            return False
        result = await self.db.users.update_one(
            {"_id": str(user_id)},
            {"$inc": {"bank": amount}},
            upsert=True
        )
        return result.modified_count > 0 or result.upserted_id is not None

    async def get_guild_settings(self, guild_id: int) -> Dict[str, Any]:
        """Get guild settings"""
        if not await self.ensure_connected():
            return {}
        settings = await self.db.guild_settings.find_one({"_id": str(guild_id)})
        return settings if settings else {}

    async def update_guild_settings(self, guild_id: int, settings: Dict[str, Any]) -> bool:
        """Update guild settings"""
        if not await self.ensure_connected():
            return False
        result = await self.db.guild_settings.update_one(
            {"_id": str(guild_id)},
            {"$set": settings},
            upsert=True
        )
        return result.modified_count > 0 or result.upserted_id is not None

    async def store_stats(self, guild_id: int, stat_type: str) -> None:
        """Store guild stats"""
        if not await self.ensure_connected():
            return
        await self.db.stats.update_one(
            {"_id": str(guild_id)},
            {"$inc": {stat_type: 1}},
            upsert=True
        )

    async def get_stats(self, guild_id: int) -> Dict[str, int]:
        """Get guild stats"""
        if not await self.ensure_connected():
            return {}
        stats = await self.db.stats.find_one({"_id": str(guild_id)})
        return stats if stats else {}

    async def reset_stats(self, guild_id: int) -> bool:
        """Reset guild stats"""
        if not await self.ensure_connected():
            return False
        result = await self.db.stats.delete_one({"_id": str(guild_id)})
        return result.deleted_count > 0

    async def add_global_buff(self, buff_data: Dict[str, Any]) -> bool:
        """Add global buff"""
        if not await self.ensure_connected():
            return False
        result = await self.db.global_buffs.insert_one(buff_data)
        return result.inserted_id is not None

    async def get_user_balance(self, user_id: int, guild_id: int = None) -> int:
        """Get user's total balance"""
        wallet = await self.get_wallet_balance(user_id, guild_id)
        bank = await self.get_bank_balance(user_id, guild_id)
        return wallet + bank

    async def transfer_money(self, from_id: int, to_id: int, amount: int, guild_id: int = None) -> bool:
        """Transfer money between users"""
        if not await self.ensure_connected():
            return False
            
        from_balance = await self.get_wallet_balance(from_id, guild_id)
        if from_balance < amount:
            return False
            
        async with await self.client.start_session() as session:
            async with session.start_transaction():
                if not await self.update_wallet(from_id, -amount, guild_id):
                    return False
                if not await self.update_wallet(to_id, amount, guild_id):
                    await self.update_wallet(from_id, amount, guild_id)  # Rollback
                    return False
                return True

    async def update_balance(self, user_id: int, amount: int, guild_id: int = None) -> bool:
        """Update user's wallet balance, handling both positive and negative amounts"""
        current = await self.get_wallet_balance(user_id, guild_id)
        if amount < 0 and abs(amount) > current:  # Check if user has enough for deduction
            return False
        return await self.update_wallet(user_id, amount, guild_id)

    async def increase_bank_limit(self, user_id: int, amount: int, guild_id: int = None) -> bool:
        """Increase user's bank storage limit"""
        if not await self.ensure_connected():
            return False
        result = await self.db.users.update_one(
            {"_id": str(user_id)},
            {"$inc": {"bank_limit": amount}},
            upsert=True
        )
        return result.modified_count > 0 or result.upserted_id is not None

    async def get_global_net_worth(self, user_id: int, excluded_guilds: list = None) -> int:
        """Get user's total net worth across all guilds"""
        if not await self.ensure_connected():
            return 0
        excluded_guilds = excluded_guilds or []
        pipeline = [
            {"$match": {"_id": str(user_id)}},
            {"$project": {
                "total": {"$add": ["$wallet", "$bank"]}
            }}
        ]
        result = await self.db.users.aggregate(pipeline).to_list(1)
        return result[0]["total"] if result else 0

    async def get_inventory(self, user_id: int, guild_id: int = None) -> list:
        """Get user's inventory"""
        if not await self.ensure_connected():
            return []
        user = await self.db.users.find_one({"_id": str(user_id)})
        return user.get("inventory", []) if user else []

    async def add_potion(self, user_id: int, potion: dict) -> bool:
        """Add active potion effect to user"""
        if not await self.ensure_connected():
            return False
        expiry = datetime.datetime.utcnow() + datetime.timedelta(minutes=potion['duration'])
        result = await self.db.active_potions.insert_one({
            "user_id": str(user_id),
            "type": potion['buff_type'],
            "multiplier": potion['multiplier'],
            "expires_at": expiry
        })
        return result.inserted_id is not None

    async def remove_from_inventory(self, user_id: int, guild_id: int, item_id: str) -> bool:
        """Remove item from user's inventory"""
        if not await self.ensure_connected():
            return False
        result = await self.db.users.update_one(
            {"_id": str(user_id)},
            {"$pull": {"inventory": {"id": item_id}}}
        )
        return result.modified_count > 0


class SyncDatabase:
    """Synchronous database class for use with Flask web interface"""
    _instance = None
    _client = None
    _db = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(SyncDatabase, cls).__new__(cls)
                    cls._instance._connected = False
                    cls._instance.logger = logging.getLogger('SyncDatabase')
        return cls._instance
        
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
            
        self._initialized = True
        self._connected = False
        self.logger = logging.getLogger('SyncDatabase')
        
        # Ensure data directory exists
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
        os.makedirs(data_dir, exist_ok=True)
        
        # Get database path from environment or use default
        db_path = os.getenv('SQLITE_DATABASE_PATH', os.path.join(data_dir, 'database.sqlite'))
        self.logger.info(f"Using SQLite database at {db_path}")
        
        try:
            # Initialize SQLite connection
            import sqlite3
            self.conn = sqlite3.connect(db_path, check_same_thread=False)
            self.cursor = self.conn.cursor()
            
            # Create tables if they don't exist
            self._create_tables()
            self.conn.commit()
            
            self.logger.info("SQLite database initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize SQLite database: {e}")
            raise
            
    def _create_tables(self):
        """Create database tables if they don't exist"""
        try:
            # Economy table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS economy (
                    user_id INTEGER,
                    guild_id INTEGER DEFAULT 0,
                    wallet INTEGER DEFAULT 0,
                    bank INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, guild_id)
                )
            """)
            
            # Guild stats table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS guild_stats (
                    guild_id INTEGER,
                    stat_type TEXT,
                    count INTEGER DEFAULT 0,
                    PRIMARY KEY (guild_id, stat_type)
                )
            """)
        except Exception as e:
            self.logger.error(f"Error creating tables: {e}")
            raise

    @property
    def client(self):
        if self._client is None:
            MONGO_URI = os.getenv('MONGO_URI', config['MONGO_URI'])
            # Use pymongo for synchronous operations
            self._client = pymongo.MongoClient(MONGO_URI)
        return self._client
        
    @property
    def db(self):
        if self._db is None:
            self._db = self.client.bronxbot
        return self._db

    def ensure_connected(self) -> bool:
        """Ensure database connection is active"""
        if not self._connected:
            try:
                self.client.admin.command('ping')
                self._connected = True
                self.logger.info("Sync database connection established")
            except Exception as e:
                self.logger.error(f"Sync database connection failed: {e}")
                return False
        return True

    def get_guild_settings(self, guild_id: str) -> Dict[str, Any]:
        """Get guild settings synchronously"""
        if not self.ensure_connected():
            return {}
        try:
            settings = self.db.guild_settings.find_one({"_id": str(guild_id)})
            return settings if settings else {}
        except Exception as e:
            self.logger.error(f"Error getting guild settings: {e}")
            return {}

    def update_guild_settings(self, guild_id: str, settings: Dict[str, Any]) -> bool:
        """Update guild settings synchronously"""
        if not self.ensure_connected():
            return False
        try:
            result = self.db.guild_settings.update_one(
                {"_id": str(guild_id)},
                {"$set": settings},
                upsert=True
            )
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            self.logger.error(f"Error updating guild settings: {e}")
            return False

    def get_user_balance(self, user_id: int, guild_id: int = None):
        """Get user's wallet and bank balance"""
        try:
            self.cursor.execute("""
                SELECT wallet, bank FROM economy 
                WHERE user_id = ? AND guild_id = ?
            """, (user_id, guild_id or 0))
            result = self.cursor.fetchone()
            if result:
                return {"wallet": result[0], "bank": result[1]}
            return {"wallet": 0, "bank": 0}
        except Exception as e:
            self.logger.error(f"Error getting balance: {e}")
            return {"wallet": 0, "bank": 0}

    # Change store_stats to be async-compatible
    async def store_stats(self, guild_id: int, stat_type: str):
        """Store guild statistics asynchronously"""
        return self.store_stats_sync(guild_id, stat_type)
    
    def store_stats_sync(self, guild_id: int, stat_type: str):
        """Store guild statistics synchronously"""
        try:
            valid_types = ["messages", "gained", "lost"]
            if stat_type not in valid_types:
                return False
                
            self.cursor.execute("""
                INSERT INTO guild_stats (guild_id, stat_type, count)
                VALUES (?, ?, 1)
                ON CONFLICT(guild_id, stat_type) DO UPDATE 
                SET count = count + 1
            """, (guild_id, stat_type))
            self.conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Error storing stats: {e}")
            return False

    def get_stats(self, guild_id: int):
        """Get guild statistics"""
        try:
            self.cursor.execute("""
                SELECT stat_type, count FROM guild_stats
                WHERE guild_id = ?
            """, (guild_id,))
            results = self.cursor.fetchall()
            return {stat[0]: stat[1] for stat in results}
        except Exception as e:
            self.logger.error(f"Error getting stats: {e}")
            return {}


# Create global database instances
async_db = AsyncDatabase.get_instance()  # For Discord bot
db = SyncDatabase()  # For Flask web interface