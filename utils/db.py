import motor
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, Dict, Any, List
import os
import asyncio
import pymongo
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure
from cogs.logging.logger import CogLogger
import json
import datetime

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
                await self.client.admin.command('ping')
                self.db = self.client.bronxbot
                self.connected = True
                logger.info("Successfully connected to MongoDB")
                return True
            except (ServerSelectionTimeoutError, ConnectionFailure) as e:
                retries += 1
                logger.warning(f"Database connection attempt {retries} failed: {e}")
                if retries < max_retries:
                    await asyncio.sleep(5) 
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

    async def store_stats(self, guild_id: int, stat_type: str, value: int = 1):
        """Update guild statistics"""
        try:
            await self.ensure_connected()
            
            stats = await self.db.stats.find_one({"_id": guild_id})
            if not stats:
                stats = {
                    "_id": guild_id,
                    "stats": {
                        "messages": 0,
                        "gained": 0,
                        "lost": 0
                    },
                    "timestamp": datetime.datetime.utcnow()
                }
                await self.db.stats.insert_one(stats)

            update_field = f"stats.{stat_type}"
            await self.db.stats.update_one(
                {"_id": guild_id},
                {"$inc": {update_field: value}}
            )
            return True
        except Exception as e:
            logger.error(f"Error updating stats for guild {guild_id}: {e}")
            return False

    async def get_stats(self, guild_id: int) -> dict:
        """Get guild statistics"""
        try:
            await self.ensure_connected()
            stats = await self.db.stats.find_one({"_id": guild_id})
            if not stats:
                stats = {
                    "_id": guild_id,
                    "stats": {
                        "messages": 0,
                        "gained": 0,
                        "lost": 0
                    },
                    "timestamp": datetime.datetime.utcnow()
                }
                await self.db.stats.insert_one(stats)
            return stats.get("stats", {})
        except Exception as e:
            logger.error(f"Error getting stats for guild {guild_id}: {e}")
            return {}

    async def reset_stats(self, guild_id: int):
        """Reset guild statistics"""
        try:
            await self.ensure_connected()
            await self.db.stats.update_one(
                {"_id": guild_id},
                {
                    "$set": {
                        "stats": {
                            "messages": 0,
                            "gained": 0,
                            "lost": 0
                        },
                        "timestamp": datetime.datetime.utcnow()
                    }
                },
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error resetting stats for guild {guild_id}: {e}")
            return False

    async def get_wallet_balance(self, user_id: int, guild_id: int = None) -> int:
        """Get user's wallet balance for specific server"""
        try:
            await self.ensure_connected()
            key = f"{user_id}_{guild_id}" if guild_id else str(user_id)
            user = await self.db.economy.find_one({"_id": key})
            return user.get("wallet", 0) if user else 0
        except Exception as e:
            logger.error(f"Failed to get wallet: {e}")
            return 0

    async def get_bank_balance(self, user_id: int, guild_id: int = None) -> int:
        """Get user's bank balance for specific server"""
        try:
            await self.ensure_connected()
            key = f"{user_id}_{guild_id}" if guild_id else str(user_id)
            user = await self.db.economy.find_one({"_id": key})
            return user.get("bank", 0) if user else 0
        except Exception as e:
            logger.error(f"Failed to get bank: {e}")
            return 0

    async def update_wallet(self, user_id: int, amount: int, guild_id: int = None) -> bool:
        """Update user's wallet balance for specific server"""
        try:
            await self.ensure_connected()
            key = f"{user_id}_{guild_id}" if guild_id else str(user_id)
            result = await self.db.economy.update_one(
                {"_id": key},
                {"$inc": {"wallet": amount}},
                upsert=True
            )
            return bool(result.modified_count or result.upserted_id)
        except Exception as e:
            logger.error(f"Failed to update wallet: {e}")
            return False

    async def update_bank(self, user_id: int, amount: int, guild_id: int = None) -> bool:
        """Update user's bank balance for specific server"""
        try:
            await self.ensure_connected()
            key = f"{user_id}_{guild_id}" if guild_id else str(user_id)
            result = await self.db.economy.update_one(
                {"_id": key},
                {"$inc": {"bank": amount}},
                upsert=True
            )
            return bool(result.modified_count or result.upserted_id)
        except Exception as e:
            logger.error(f"Failed to update bank: {e}")
            return False

    async def get_global_net_worth(self, user_id: int, excluded_guilds: list = None) -> int:
        """Get user's total net worth across all servers excluding specified ones"""
        try:
            await self.ensure_connected()
            total = 0
            pattern = f"^{user_id}_"
            async for doc in self.db.economy.find({"_id": {"$regex": pattern}}):
                guild_id = int(doc["_id"].split("_")[1])
                if excluded_guilds and guild_id in excluded_guilds:
                    continue
                total += doc.get("wallet", 0) + doc.get("bank", 0)
            return total
        except Exception as e:
            logger.error(f"Failed to get global net worth: {e}")
            return 0

    async def add_potion(self, user_id: int, potion_data: dict) -> bool:
        """Add active potion effect to user"""
        try:
            await self.ensure_connected()
            expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=potion_data['duration'])
            
            await self.db.potions.insert_one({
                "user_id": user_id,
                "potion": potion_data['name'],
                "type": potion_data['type'],
                "multiplier": potion_data['multiplier'],
                "expires_at": expires_at
            })
            return True
        except Exception as e:
            logger.error(f"Failed to add potion for user {user_id}: {e}")
            return False

    async def get_active_potions(self, user_id: int) -> list:
        """Get user's active potion effects"""
        try:
            await self.ensure_connected()
            current_time = datetime.datetime.utcnow()
            
            # Clean expired potions first
            await self.db.potions.delete_many({
                "user_id": user_id,
                "expires_at": {"$lt": current_time}
            })
            
            # Get active potions
            return await self.db.potions.find({
                "user_id": user_id,
                "expires_at": {"$gt": current_time}
            }).to_list(length=None)
            
        except Exception as e:
            logger.error(f"Failed to get potions for user {user_id}: {e}")
            return []

    async def apply_potion_effects(self, user_id: int, amount: int, effect_type: str) -> int:
        """Apply active potion effects to a value"""
        try:
            potions = await self.get_active_potions(user_id)
            multiplier = 1.0
            
            for potion in potions:
                if potion['type'] == effect_type:
                    multiplier *= potion['multiplier']
            
            return int(amount * multiplier)
            
        except Exception as e:
            logger.error(f"Failed to apply potion effects for user {user_id}: {e}")
            return amount

    async def add_buff(self, user_id: int, buff_data: dict) -> bool:
        """Add buff to user"""
        try:
            await self.ensure_connected()
            await self.db.buffs.insert_one({
                "user_id": user_id,
                "type": buff_data["type"],
                "multiplier": buff_data["multiplier"],
                "expires_at": buff_data["expires_at"]
            })
            return True
        except Exception as e:
            logger.error(f"Failed to add buff for user {user_id}: {e}")
            return False

    async def remove_buff(self, user_id: int, buff_type: str) -> bool:
        """Remove buff from user"""
        try:
            await self.ensure_connected()
            result = await self.db.buffs.delete_one({
                "user_id": user_id,
                "type": buff_type
            })
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Failed to remove buff from user {user_id}: {e}")
            return False

    async def get_active_buffs(self, user_id: int) -> List[dict]:
        """Get user's active buffs"""
        try:
            await self.ensure_connected()
            current_time = datetime.datetime.utcnow().timestamp()
            return await self.db.buffs.find({
                "user_id": user_id,
                "expires_at": {"$gt": current_time}
            }).to_list(None)
        except Exception as e:
            logger.error(f"Failed to get buffs for user {user_id}: {e}")
            return []

    async def apply_buffs(self, user_id: int, amount: int, buff_type: str) -> int:
        """Apply active buffs to a value"""
        try:
            buffs = await self.get_active_buffs(user_id)
            multiplier = 1.0
            
            for buff in buffs:
                if buff["type"] == buff_type:
                    multiplier *= buff["multiplier"]
            
            return int(amount * multiplier)
        except Exception as e:
            logger.error(f"Failed to apply buffs for user {user_id}: {e}")
            return amount

    async def add_global_buff(self, buff_data: dict) -> bool:
        """Add a global buff"""
        try:
            await self.ensure_connected()
            # Remove any existing global buffs
            await self.db.global_buffs.delete_many({})
            # Add new buff
            await self.db.global_buffs.insert_one(buff_data)
            return True
        except Exception as e:
            logger.error(f"Failed to add global buff: {e}")
            return False

    async def get_global_buff(self) -> Optional[dict]:
        """Get current global buff if active"""
        try:
            await self.ensure_connected()
            current_time = datetime.datetime.utcnow().timestamp()
            buff = await self.db.global_buffs.find_one({
                "expires_at": {"$gt": current_time}
            })
            return buff
        except Exception as e:
            logger.error(f"Failed to get global buff: {e}")
            return None

    async def get_shop_items(self, guild_id: int = None) -> dict:
        """Get shop items for global or server shop"""
        try:
            await self.ensure_connected()
            if guild_id:
                shop = await self.db.shops.find_one({"_id": f"server_{guild_id}"})
            else:
                shop = await self.db.shops.find_one({"_id": "global"})
            return shop.get("items", {}) if shop else {}
        except Exception as e:
            logger.error(f"Failed to get shop items: {e}")
            return {}

    async def add_shop_item(self, item_data: dict, guild_id: int = None) -> bool:
        """Add item to global or server shop"""
        try:
            await self.ensure_connected()
            shop_id = f"server_{guild_id}" if guild_id else "global"
            await self.db.shops.update_one(
                {"_id": shop_id},
                {"$set": {f"items.{item_data['id']}": item_data}},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Failed to add shop item: {e}")
            return False

    async def remove_shop_item(self, item_id: str, guild_id: int = None) -> bool:
        """Remove item from global or server shop"""
        try:
            await self.ensure_connected()
            shop_id = f"server_{guild_id}" if guild_id else "global"
            result = await self.db.shops.update_one(
                {"_id": shop_id},
                {"$unset": {f"items.{item_id}": ""}}
            )
            return bool(result.modified_count)
        except Exception as e:
            logger.error(f"Failed to remove shop item: {e}")
            return False

    async def add_to_inventory(self, user_id: int, guild_id: int, item_data: dict) -> bool:
        """Add item to user's inventory"""
        try:
            await self.ensure_connected()
            key = f"{user_id}_{guild_id}"
            
            await self.db.inventory.update_one(
                {"_id": key},
                {"$push": {"items": item_data}},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Failed to add item to inventory: {e}")
            return False

    async def get_inventory(self, user_id: int, guild_id: int) -> list:
        """Get user's inventory"""
        try:
            await self.ensure_connected()
            key = f"{user_id}_{guild_id}"
            inv = await self.db.inventory.find_one({"_id": key})
            return inv.get("items", []) if inv else []
        except Exception as e:
            logger.error(f"Failed to get inventory: {e}")
            return []

    async def remove_from_inventory(self, user_id: int, guild_id: int, item_id: str) -> bool:
        """Remove item from inventory"""
        try:
            await self.ensure_connected()
            key = f"{user_id}_{guild_id}"
            
            result = await self.db.inventory.update_one(
                {"_id": key},
                {"$pull": {"items": {"id": item_id}}}
            )
            return bool(result.modified_count)
        except Exception as e:
            logger.error(f"Failed to remove item from inventory: {e}")
            return False

db = Database(config["MONGO_URI"] if "MONGO_URI" in config else "mongodb://localhost:27017")