import asyncio
import logging
import os

import app.db.models  # noqa: F401 - import side-effect to register models with Base.metadata
from app.db.models import User, UserRole
from app.db.session import Base, async_session_factory, engine
from sqlalchemy import select

logger = logging.getLogger(__name__)


async def init_db() -> None:
    logger.info("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully")

    await bootstrap_admin()


async def bootstrap_admin() -> None:
    """Create the first admin from the environment, idempotently.

    Why this exists
    ---------------
    ``install.sh`` writes ``ADMIN_EMAIL`` / ``ADMIN_PASSWORD`` into ``.env``, and
    ``POST /auth/register`` requires an *existing* ADMIN to authorise it — but
    nothing ever created that first admin. On a fresh install there was
    therefore no way to log in at all: a chicken-and-egg deadlock that made the
    whole auth/RBAC/WebSocket layer unreachable.

    Rules:
      * no-op when ``ADMIN_EMAIL``/``ADMIN_PASSWORD`` are absent (tests, CI)
      * no-op when the user already exists — safe to run on every boot, and it
        never overwrites a password an operator has since changed
      * if the user exists but is not an admin, the role is promoted (the
        operator explicitly declared them as the admin)
    """
    email = (os.getenv("ADMIN_EMAIL") or "").strip().lower()
    password = os.getenv("ADMIN_PASSWORD") or ""

    if not email or not password:
        logger.debug("ADMIN_EMAIL/ADMIN_PASSWORD not set — skipping admin bootstrap")
        return

    if len(password) < 12:
        logger.warning(
            "ADMIN_PASSWORD is shorter than 12 characters — refusing to create a "
            "weak admin account. Set a stronger password and restart."
        )
        return

    # Imported lazily: app.core.auth reads settings at import time.
    from app.core.auth import get_password_hash

    async with async_session_factory() as session:
        existing = (
            await session.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()

        if existing is not None:
            changed = False
            if existing.role != UserRole.ADMIN:
                logger.info("Promoting existing user %s to ADMIN", email)
                existing.role = UserRole.ADMIN
                changed = True
            if not existing.is_active:
                existing.is_active = True
                changed = True
            if changed:
                await session.commit()
            else:
                logger.info("Bootstrap admin %s already present — no changes", email)
            return

        session.add(
            User(
                email=email,
                hashed_password=get_password_hash(password),
                full_name=os.getenv("ADMIN_FULL_NAME") or "AARK Administrator",
                role=UserRole.ADMIN,
                is_active=True,
                is_superuser=True,
            )
        )
        await session.commit()
        logger.info("Bootstrap admin created: %s", email)


async def drop_db() -> None:
    logger.warning("Dropping all database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.warning("All database tables dropped")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(init_db())
