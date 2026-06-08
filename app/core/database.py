from pymongo import ASCENDING, IndexModel
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    db = None

db = Database()

async def connect_to_mongo():
    logger.info("Connecting to MongoDB...")
    db.client = AsyncIOMotorClient(settings.MONGODB_URI)
    db.db = db.client[settings.MONGODB_DATABASE]
    try:
        # Verify connection
        await db.client.admin.command('ping')
        
        # RNF-12: Integridad - Crear índice TTL para ofertas obsoletas
        # Las ofertas se borrarán cuando su 'fecha_expiracion' sea alcanzada
        await db.db["ofertas_laborales"].create_index(
            [("fecha_expiracion", ASCENDING)], 
            expireAfterSeconds=0
        )
        
        logger.info("Connected to MongoDB Atlas and TTL Indexes created!")
    except Exception as e:
        logger.error(f"Could not connect to MongoDB: {e}")
        raise e

async def close_mongo_connection():
    logger.info("Closing MongoDB connection...")
    if db.client:
        db.client.close()
    logger.info("MongoDB connection closed.")

def get_database():
    return db.db
