import motor.motor_asyncio
import json
import datetime
import os
import logging
from typing import Dict, Any, Optional

with open('data/config.json') as f:
    config = json.load(f)

# Create singleton class for database access that manages its own client
class AsyncDatabase:
    _instance = None
    _client = None
    _db = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.logger = logging.getLogger('Database')
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
class Database:
    _instance = None
    _client = None
    _db = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance._connected = False
            cls._instance.logger = logging.getLogger('Database')
        return cls._instance
        
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
                self.logger.info("Database connection established")
            except Exception as e:
                self.logger.error(f"Database connection failed: {e}")
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

# Create global database instance
db = Database()