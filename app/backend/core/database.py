import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL")

# global mongodb client
mongodb_client: AsyncIOMotorClient = None
database = None

async def connect_to_mongo():
    """init MongoDB connection"""
    global mongodb_client, database
    try:
        mongodb_client = AsyncIOMotorClient(MONGODB_URL)
        db_name = MONGODB_URL.split("/")[-1] if "/" in MONGODB_URL else "infralens"
        database = mongodb_client[db_name]
        await database.command("ping")
        print(f"Connected to MongoDB database: {db_name}")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        raise

async def close_mongo_connection():
    global mongodb_client
    if mongodb_client:
        mongodb_client.close()
        print("MongoDB connection closed")

def get_database():
    """Get database instance"""
    return database
