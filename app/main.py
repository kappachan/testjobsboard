from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import uvicorn
import os
from dotenv import load_dotenv

from app.database import create_monitor, get_all_jobs
from app.scheduler import start_scheduler, schedule_monitors, stop_scheduler
from app.services.scraper import WebsiteScraper

load_dotenv()

app = FastAPI(title="GigSniper")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Initialize services
scraper = WebsiteScraper()

@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup."""
    start_scheduler()
    await schedule_monitors()

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    stop_scheduler()

@app.get("/")
async def home(request: Request):
    """Render the home page."""
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )

@app.post("/monitor")
async def add_monitor(
    request: Request,
    url: str = Form(...),
    interval: int = Form(...)
):
    """Add a new URL to monitor."""
    try:
        # Validate interval
        if interval < 5:
            raise HTTPException(status_code=400, detail="Interval must be at least 5 minutes")
        
        # Create monitor in database first
        monitor = await create_monitor(url, interval)
        
        # Create initial snapshot and schedule monitoring
        await scraper.add_monitor(url, interval)
        await schedule_monitors()  # Reschedule all monitors
        
        return RedirectResponse(url="/", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/jobs")
async def list_jobs(request: Request):
    """List all monitored jobs and their status."""
    jobs = await get_all_jobs(limit=100)  # Get last 100 jobs
    return templates.TemplateResponse(
        "jobs.html",
        {"request": request, "jobs": jobs}
    )

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=bool(os.getenv("DEBUG", True))
    ) 