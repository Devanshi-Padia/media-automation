import asyncio
import logging

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.config import settings
from src.app.core.db.database import local_session
from src.app.core.security import get_password_hash
from src.app.models.user import User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def delete_all_users(session: AsyncSession):
    """Deletes all users from the database."""
    await session.execute(delete(User))
    logger.info("All users deleted.")


async def create_first_superuser(session: AsyncSession):
    """Creates the first superuser based on environment settings."""
    email = settings.ADMIN_EMAIL
    result = await session.execute(select(User).filter_by(email=email))
    user = result.scalar_one_or_none()

    if user is None:
        new_user = User(
            name=settings.ADMIN_NAME,
            username=settings.ADMIN_USERNAME,
            email=settings.ADMIN_EMAIL,
            hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
            is_superuser=True,
            is_email_verified=True,
        )
        session.add(new_user)
        await session.flush()
        logger.info(f"Admin user '{settings.ADMIN_USERNAME}' created successfully.")
    else:
        logger.info(f"Admin user '{settings.ADMIN_USERNAME}' already exists.")


async def main():
    """Deletes all users and creates the first superuser."""
    logger.info("Starting user deletion and creation process...")
    async with local_session() as session:
        await delete_all_users(session)
        await create_first_superuser(session)
        await session.commit()
    logger.info("Process finished.")


if __name__ == "__main__":
    asyncio.run(main())
