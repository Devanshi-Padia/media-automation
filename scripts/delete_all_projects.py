import asyncio
from sqlalchemy import delete
from src.app.core.db.database import async_get_db
from src.app.models.project import Project, SocialMediaCredential

async def main():
    async for db in async_get_db():
        await db.execute(delete(SocialMediaCredential))
        await db.execute(delete(Project))
        await db.commit()
        print("All projects and related credentials deleted.")

if __name__ == "__main__":
    asyncio.run(main()) 