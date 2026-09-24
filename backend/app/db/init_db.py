from sqlalchemy.ext.asyncio import AsyncEngine
from app.db.session import engine, Base
from app.db.models import *  # noqa
import asyncio
import logging

logger = logging.getLogger(__name__)


async def init_db() -> None:
    logger.info("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully")


async def drop_db() -> None:
    logger.warning("Dropping all database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.warning("All database tables dropped")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(init_db())