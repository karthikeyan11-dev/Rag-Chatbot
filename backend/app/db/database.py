import os
import logging
import asyncio
import sys

# Windows-specific fix for Psycopg/SQLAlchemy async
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.db.models import Base
from dotenv import load_dotenv

# Configure logging for database module
logger = logging.getLogger(__name__)

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "backend", ".env")
load_dotenv(dotenv_path)

# --- STRICT POSTGRESQL CONFIGURATION ---

# Get Database URL from environment variables
DATABASE_URL = os.getenv("DATABASE_URL")

# FAIL FAST: Enforce PostgreSQL-only architecture
if not DATABASE_URL:
    logger.critical("DATABASE_URL is missing in environment variables. Application cannot start without a PostgreSQL connection.")
    raise EnvironmentError("DATABASE_URL is required for cloud-native PostgreSQL persistence. SQLite fallbacks have been removed.")

if not DATABASE_URL.startswith(("postgresql", "postgres")):
    logger.critical("Invalid DATABASE_URL. Only PostgreSQL (postgresql+psycopg) is supported in this architecture.")
    raise ValueError("Invalid database dialect. This system strictly requires PostgreSQL.")

logger.info(f"Connecting to Cloud-Native Database: {DATABASE_URL.split('@')[-1]}") # Log endpoint only for security

# Create async engine for AWS RDS PostgreSQL
# We add pool_pre_ping for better connection reliability in cloud environments
engine = create_async_engine(
    DATABASE_URL, 
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# Create async session factory
async_session_factory = async_sessionmaker(
    engine, 
    expire_on_commit=False, 
    class_=AsyncSession
)

async def init_db():
    """Initialize the AWS RDS database and create tables."""
    try:
        async with engine.begin() as conn:
            # Strictly create tables in the connected PostgreSQL database
            await conn.run_sync(Base.metadata.create_all)
        logger.info("RDS PostgreSQL tables synchronized successfully.")
    except Exception as e:
        logger.error(f"Failed to synchronize RDS PostgreSQL tables: {e}")
        # Do not raise here to keep the server alive if DB is partially ready
        # raise

async def get_db():
    """Dependency for getting async database session."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
