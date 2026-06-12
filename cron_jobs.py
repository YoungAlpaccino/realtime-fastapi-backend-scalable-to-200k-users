"""
Background ticks — refresh aggregates, prune audit, sweep cache.

These run inside the same process via APScheduler. For very large
deployments they would be moved to a separate worker.
"""
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)


def register_jobs(scheduler: AsyncIOScheduler, cache):
    scheduler.add_job(cache.refresh, "interval", seconds=60, id="cache.refresh")
    scheduler.add_job(prune_audit, "cron", hour=3, id="audit.prune")
    scheduler.add_job(rebuild_aggregates, "interval", minutes=15, id="aggregates")


async def prune_audit():
    cutoff = datetime.utcnow() - timedelta(days=30)
    logger.info("would prune audit < %s", cutoff)
    # DEMO: real impl runs a bounded DELETE in batches.


async def rebuild_aggregates():
    logger.info("would refresh materialized aggregates")
    # DEMO: real impl calls REFRESH MATERIALIZED VIEW CONCURRENTLY ...
