from datetime import datetime, timedelta, timezone
import logging
from typing import Any
from pymongo import AsyncMongoClient, ReturnDocument
from .config import Settings
logger=logging.getLogger("Database")

class Database:
    def __init__(self, settings:Settings):
        self.settings=settings; self.client=None; self.db=None; self.sessions=None; self.logs=None
    async def connect(self)->None:
        self.client=AsyncMongoClient(self.settings.mongo_uri, serverSelectionTimeoutMS=self.settings.mongo_server_selection_timeout_ms, connectTimeoutMS=self.settings.mongo_connect_timeout_ms, socketTimeoutMS=self.settings.mongo_socket_timeout_ms, appName="telegram-security-bot")
        await self.client.admin.command({"ping":1})
        self.db=self.client[self.settings.db_name]
        self.sessions=self.db["active_sessions"]; self.logs=self.db["access_logs"]
        await self.sessions.create_index("session_id",unique=True)
        await self.sessions.create_index("user_id",unique=True)
        await self.sessions.create_index("expires_at",expireAfterSeconds=0)
        await self.logs.create_index([("user_id",1),("chat_id",1),("timestamp",-1)])
        if self.settings.access_log_ttl_days>0:
            await self.logs.create_index("timestamp",expireAfterSeconds=self.settings.access_log_ttl_days*86400)
        logger.info("MongoDB conectado correctamente.")
    async def close(self)->None:
        if self.client is not None:
            await self.client.close(); self.client=None
    async def is_ready(self)->bool:
        if self.client is None: return False
        try:
            await self.client.admin.command({"ping":1}); return True
        except Exception:
            logger.exception("MongoDB no está listo."); return False
    async def create_session(self,session:dict[str,Any])->None:
        await self.sessions.update_one({"user_id":session["user_id"]},{"$set":session},upsert=True)
    async def get_session(self,session_id:str):
        return await self.sessions.find_one({"session_id":session_id})
    async def increment_attempts(self,session_id:str):
        return await self.sessions.find_one_and_update({"session_id":session_id,"attempts":{"$lt":self.settings.captcha_max_attempts},"expires_at":{"$gt":datetime.now(timezone.utc)}},{"$inc":{"attempts":1}},return_document=ReturnDocument.AFTER)
    async def consume_session(self,session_id:str):
        return await self.sessions.find_one_and_delete({"session_id":session_id})
    async def delete_user_session(self,user_id:int)->None:
        await self.sessions.delete_many({"user_id":user_id})
    async def log_access(self,*,user_id:int,chat_id:int,status:str,details:str="",session_id:str|None=None)->None:
        doc={"user_id":user_id,"chat_id":chat_id,"status":status,"details":details,"timestamp":datetime.now(timezone.utc)}
        if session_id: doc["session_id"]=session_id
        await self.logs.insert_one(doc)
    @staticmethod
    def expiration(seconds:int): return datetime.now(timezone.utc)+timedelta(seconds=seconds)
