from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import IndexModel, ASCENDING
from app.core.config import settings
from app.models.user import UserInDB
from app.models.report import ReportInDB
from app.models.comment import CommentInDB
from app.models.message import MessageInDB
from app.utils.security import get_password_hash
import asyncio
import logging

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    database: AsyncIOMotorDatabase = None


db = Database()


async def get_database() -> AsyncIOMotorDatabase:
    return db.database


async def init_db():
    """Initialize database connection and create indexes"""
    try:
        # Connect to MongoDB
        db.client = AsyncIOMotorClient(settings.mongo_uri)
        db.database = db.client[settings.database_name]
        
        # Test connection
        await db.client.admin.command('ping')
        logger.info("Successfully connected to MongoDB")
        
        # Create indexes
        await create_indexes()
        
        # Create admin user if not exists
        await create_admin_user()
        
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise


async def create_indexes():
    """Create database indexes for optimal performance"""
    try:
        # Users collection indexes
        users_indexes = [
            IndexModel([("email", ASCENDING)], unique=True),
            IndexModel([("status", ASCENDING)]),
            IndexModel([("role", ASCENDING)])
        ]
        await db.database.users.create_indexes(users_indexes)
        
        # Reports collection indexes
        reports_indexes = [
            # Index unique partiel: s'applique seulement aux rapports avec week_iso
            IndexModel(
                [("user_id", ASCENDING), ("week_iso", ASCENDING)], 
                unique=True,
                partialFilterExpression={"week_iso": {"$exists": True}}
            ),
            IndexModel([("week_iso", ASCENDING)]),
            IndexModel([("user_id", ASCENDING)]),
            IndexModel([("created_at", ASCENDING)])
        ]
        await db.database.reports.create_indexes(reports_indexes)
        
        # Comments collection indexes
        comments_indexes = [
            IndexModel([("report_id", ASCENDING)]),
            IndexModel([("admin_id", ASCENDING)]),
            IndexModel([("created_at", ASCENDING)])
        ]
        await db.database.comments.create_indexes(comments_indexes)
        
        # Messages collection indexes
        messages_indexes = [
            IndexModel([("receiver_id", ASCENDING), ("created_at", ASCENDING)]),
            IndexModel([("sender_id", ASCENDING)]),
            IndexModel([("read_status", ASCENDING)])
        ]
        await db.database.messages.create_indexes(messages_indexes)
        
        logger.info("Database indexes created successfully")
        
    except Exception as e:
        logger.error(f"Failed to create indexes: {e}")


async def create_admin_user():
    """Create default admin user if not exists"""
    try:
        # Check if admin user exists
        admin_exists = await db.database.users.find_one({"email": settings.admin_email})
        
        if not admin_exists:
            # Create admin user
            admin_user = UserInDB(
                email=settings.admin_email,
                name=settings.admin_name,
                hashed_password=get_password_hash(settings.admin_password),
                role="admin",
                status="active"
            )
            
            await db.database.users.insert_one(admin_user.model_dump(by_alias=True))
            logger.info(f"Admin user created: {settings.admin_email}")
        else:
            logger.info("Admin user already exists")
            
    except Exception as e:
        logger.error(f"Failed to create admin user: {e}")


async def close_db():
    """Close database connection"""
    if db.client:
        db.client.close()
        logger.info("Database connection closed")