import os
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from app.database import get_active_monitors, update_monitor_last_check
from app.services.scraper import WebsiteScraper
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('gigsniper.scheduler')

# Configure the scheduler
jobstores = {
    'default': MemoryJobStore()
}

executors = {
    'default': ThreadPoolExecutor(max_workers=3)  # Using ThreadPoolExecutor instead of ProcessPoolExecutor
}

job_defaults = {
    'coalesce': True,       # Combine multiple waiting runs into a single run
    'max_instances': 1,     # Only allow one instance of each job to run at a time
    'misfire_grace_time': 15 * 60  # Allow jobs to be 15 minutes late
}

scheduler = AsyncIOScheduler(
    jobstores=jobstores,
    executors=executors,
    job_defaults=job_defaults
)

scraper = WebsiteScraper()

def run_async(coro):
    """Helper function to run async functions in the scheduler."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

def check_monitor_sync(monitor_id: int, url: str):
    """Synchronous wrapper for check_monitor."""
    logger.info(f"Starting check for monitor {monitor_id} ({url}) at {datetime.now().isoformat()}")
    try:
        result = run_async(check_monitor_async(monitor_id, url))
        logger.info(f"Completed check for monitor {monitor_id} at {datetime.now().isoformat()}")
        return result
    except Exception as e:
        logger.error(f"Error in check_monitor_sync for monitor {monitor_id}: {e}")
        raise

async def check_monitor_async(monitor_id: int, url: str):
    """Check a single monitor for changes."""
    try:
        new_jobs = await scraper.check_for_changes(monitor_id)
        if new_jobs:
            logger.info(f"Found {len(new_jobs)} new jobs for monitor {monitor_id}")
        await update_monitor_last_check(monitor_id)
    except Exception as e:
        logger.error(f"Error checking monitor {monitor_id}: {e}")

async def schedule_monitors():
    """Schedule all active monitors."""
    logger.info("Scheduling active monitors...")
    monitors = await get_active_monitors()
    
    for monitor in monitors:
        job_id = f"monitor_{monitor['id']}"
        # Try to remove existing job if it exists
        try:
            scheduler.remove_job(job_id)
        except:
            # Job doesn't exist yet, that's fine
            pass
        
        # Schedule new job with the sync wrapper
        next_run = datetime.now()
        scheduler.add_job(
            check_monitor_sync,  # Use the sync wrapper
            'interval',
            minutes=monitor['interval'],
            id=job_id,
            args=[monitor['id'], monitor['url']],
            next_run_time=next_run  # Run immediately
        )
        logger.info(f"Scheduled monitor {monitor['id']} ({monitor['url']}) to run every {monitor['interval']} minutes. Next run at {next_run.isoformat()}")

def start_scheduler():
    """Start the scheduler."""
    if not scheduler.running:
        scheduler.start()
        logger.info(f"Scheduler started at {datetime.now().isoformat()}")

def stop_scheduler():
    """Stop the scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped") 