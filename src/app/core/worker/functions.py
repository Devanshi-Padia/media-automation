import asyncio
import logging

import uvloop
from arq.worker import Worker

from src.app.core.scheduler import scheduler
from src.app.core.db.database import async_get_db

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


# -------- background tasks --------
async def sample_background_task(ctx: Worker, name: str) -> str:
    await asyncio.sleep(5)
    return f"Task {name} is complete!"


# -------- base functions --------
async def startup(ctx: Worker) -> None:
    logging.info("Worker Started")


async def shutdown(ctx: Worker) -> None:
    logging.info("Worker end")


# -------- periodic scheduled post processor --------
async def process_due_scheduled_posts(ctx: Worker) -> None:
    """Periodically checks for due scheduled posts and executes them."""
    async for db in async_get_db():
        pending_posts = await scheduler.get_pending_scheduled_posts(db)
        for scheduled_post in pending_posts:
            platforms = scheduled_post.platforms.split(',')
            try:
                await scheduler.execute_scheduled_post(scheduled_post.post_id, platforms, db)
                logging.info(f"[SCHEDULER] Executed scheduled post {scheduled_post.post_id} for platforms {platforms}")
            except Exception as e:
                logging.error(f"[SCHEDULER] Failed to execute scheduled post {scheduled_post.post_id}: {e}")
