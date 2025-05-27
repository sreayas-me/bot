import motor.motor_asyncio
import pymongo
import json
import datetime
import os
import asyncio
import logging
from typing import Dict, Any, Optional
import threading

with open('data/config.json') as f:
    config = json.load(f)

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
        self._connected = False
        self.logger = logging.getLogger('SyncDatabase')
        # Initialize SQLite connection
        import sqlite3
        self.conn = sqlite3.connect('data/database.sqlite', check_same_thread=False)
        self.cursor = self.conn.cursor()
        # Create tables if they don't exist
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS economy (
                user_id INTEGER,
                guild_id INTEGER DEFAULT 0,
                wallet INTEGER DEFAULT 0,
                bank INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, guild_id)
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS guild_stats (
                guild_id INTEGER,
                stat_type TEXT,
                count INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, stat_type)
            )
        """)
        self.conn.commit()

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