import asyncio
from datetime import datetime
from sqlalchemy import select
from app.models.database import AsyncSessionLocal, Monitor
from app.services.scraper import WebsiteScraper

class JobScheduler:
    def __init__(self):
        self.running = False
        self.scraper = WebsiteScraper()
        self.tasks = {}

    def start(self):
        """Start the scheduler."""
        self.running = True
        asyncio.create_task(self._schedule_loop())

    def stop(self):
        """Stop the scheduler."""
        self.running = False
        for task in self.tasks.values():
            task.cancel()

    async def _schedule_loop(self):
        """Main scheduling loop."""
        while self.running:
            try:
                await self._check_monitors()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                print(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    async def _check_monitors(self):
        """Check all active monitors and schedule checks if needed."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Monitor).where(Monitor.is_active == True)
            )
            monitors = result.scalars().all()

            for monitor in monitors:
                monitor_id = monitor.id
                
                # If monitor is not already being checked
                if monitor_id not in self.tasks or self.tasks[monitor_id].done():
                    # Check if it's time to run this monitor
                    if self._should_check_monitor(monitor):
                        # Schedule the check
                        self.tasks[monitor_id] = asyncio.create_task(
                            self._run_monitor_check(monitor_id)
                        )

    def _should_check_monitor(self, monitor: Monitor) -> bool:
        """Determine if a monitor should be checked based on its interval."""
        if not monitor.last_check:
            return True
        
        elapsed = (datetime.utcnow() - monitor.last_check).total_seconds()
        return elapsed >= (monitor.interval * 60)  # Convert minutes to seconds

    async def _run_monitor_check(self, monitor_id: int):
        """Run a check for a specific monitor."""
        try:
            new_jobs = await self.scraper.check_for_changes(monitor_id)
            if new_jobs:
                # Here you would typically trigger notifications
                print(f"Found {len(new_jobs)} new jobs for monitor {monitor_id}")
        except Exception as e:
            print(f"Error checking monitor {monitor_id}: {e}") 