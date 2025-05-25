from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, Dict, Any
import json
import os

with open("data/config.json", "r") as f:
    config = json.load(f)
class Database:
    def __init__(self, uri: str = "mongodb://localhost:27017"):
        self.client = AsyncIOMotorClient(uri)
        self.db = self.client.bronxbot
        
    async def get_user_balance(self, user_id: int) -> int:
        """Get user balance, create if not exists"""
        user = await self.db.economy.find_one({"_id": user_id})
        if not user:
            await self.db.economy.insert_one({"_id": user_id, "balance": 1000})
            return 1000
        return user.get("balance", 0)
    
    async def update_balance(self, user_id: int, amount: int) -> bool:
        """Update user balance, returns False if insufficient funds"""
        current = await self.get_user_balance(user_id)
        if current + amount < 0:
            return False
            
        await self.db.economy.update_one(
            {"_id": user_id},
            {"$inc": {"balance": amount}},
            upsert=True
        )
        return True

    async def transfer_money(self, from_id: int, to_id: int, amount: int) -> bool:
        """Transfer money between users"""
        if amount <= 0:
            return False
            
        if not await self.update_balance(from_id, -amount):
            return False
            
        await self.update_balance(to_id, amount)
        return True

db = Database((config['MONGO_URI'], "mongodb://localhost:27017"))
