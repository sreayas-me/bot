from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, Dict, Any
import os
import asyncio
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure
from cogs.logging.logger import CogLogger
import json

with open("data/config.json", "r") as f:
    config = json.load(f)
logger = CogLogger('Database')

class Database:
    def __init__(self, uri: str = "mongodb://localhost:27017"):
        self.uri = uri
        self.client = None
        self.db = None
        self.connected = False
        
    async def connect(self, max_retries=3):
        """Establish database connection with retries"""
        retries = 0
        while not self.connected and retries < max_retries:
            try:
                self.client = AsyncIOMotorClient(self.uri)
                await self.client.admin.command('ping')  # Test connection
                self.db = self.client.bronxbot
                self.connected = True
                logger.info("Successfully connected to MongoDB")
                return True
            except (ServerSelectionTimeoutError, ConnectionFailure) as e:
                retries += 1
                logger.warning(f"Database connection attempt {retries} failed: {e}")
                if retries < max_retries:
                    await asyncio.sleep(5)  # Wait before retrying
                else:
                    logger.error("Failed to connect to database after maximum retries")
                    raise
    
    async def ensure_connected(self):
        """Ensure database connection is active"""
        if not self.connected:
            await self.connect()
        return self.connected

    async def get_user_balance(self, user_id: int) -> int:
        """Get user balance, create if not exists"""
        try:
            await self.ensure_connected()
            user = await self.db.economy.find_one({"_id": user_id})
            if not user:
                await self.db.economy.insert_one({"_id": user_id, "balance": 1000})
                return 1000
            return user.get("balance", 0)
        except Exception as e:
            logger.error(f"Error getting balance for user {user_id}: {e}")
            return 0
    
    async def update_balance(self, user_id: int, amount: int) -> bool:
        """Update user balance, returns False if insufficient funds"""
        try:
            await self.ensure_connected()
            current = await self.get_user_balance(user_id)
            if current + amount < 0:
                return False
                
            await self.db.economy.update_one(
                {"_id": user_id},
                {"$inc": {"balance": amount}},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error updating balance for user {user_id}: {e}")
            return False

    async def transfer_money(self, from_id: int, to_id: int, amount: int) -> bool:
        """Transfer money between users"""
        try:
            await self.ensure_connected()
            if amount <= 0:
                return False
                
            if not await self.update_balance(from_id, -amount):
                return False
                
            await self.update_balance(to_id, amount)
            return True
        except Exception as e:
            logger.error(f"Error transferring money: {e}")
            return False

# Initialize with environment variable or default to localhost
db = Database(config["MONGO_URI"] if "MONGO_URI" in config else "mongodb://localhost:27017")
