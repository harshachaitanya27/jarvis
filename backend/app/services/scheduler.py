"""Nightly scheduler.

Runs the generation batch every morning so episodes are ready when the user
wakes. Thin glue over the same ``run_for_all`` coroutine the CLI uses — run it
as a long-lived process:

    python -m app.services.scheduler
"""

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.cli import run_for_all
from app.config import get_settings

log = logging.getLogger(__name__)

# Hour of day (local server time) to run the nightly batch.
NIGHTLY_HOUR = 4


def build_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_for_all,
        trigger=CronTrigger(hour=NIGHTLY_HOUR, minute=0),
        id="nightly-generation",
        max_instances=1,
        coalesce=True,
    )
    return scheduler


async def _serve() -> None:
    scheduler = build_scheduler()
    scheduler.start()
    log.info("scheduler started; nightly generation at %02d:00", NIGHTLY_HOUR)
    try:
        await asyncio.Event().wait()  # run forever
    finally:
        scheduler.shutdown()


def main() -> None:
    logging.basicConfig(level=get_settings().log_level)
    asyncio.run(_serve())


if __name__ == "__main__":
    main()
