from datetime import datetime
import os
import time
import hashlib
from bs4 import BeautifulSoup
import httpx
from firecrawl import FirecrawlApp
from pydantic import BaseModel
from app.database import (
    create_snapshot,
    create_job,
    get_latest_snapshot,
    supabase
)
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('gigsniper.scraper')

class JobSchema(BaseModel):
    title: str
    description: str
    url: str
    location: str = ""
    company: str = ""
    salary_range: str = ""
    job_type: str = ""
    posted_date: str = ""

class WebsiteScraper:
    def __init__(self):
        self.firecrawl = FirecrawlApp(api_key=os.getenv("FIRECRAWL_API_KEY"))

    async def _track_api_call(self, endpoint: str, start_time: float, response=None, error=None):
        """Track API call details."""
        try:
            response_time = time.time() - start_time
            
            # Extract relevant data
            status_code = None
            error_message = None
            credits_used = 1  # Default cost

            if error:
                if hasattr(error, 'status_code'):
                    status_code = error.status_code
                error_message = str(error)
            elif response:
                if isinstance(response, dict):
                    status_code = response.get('metadata', {}).get('statusCode')
                    credits_used = 1  # Default for now, adjust if API provides usage info

            # Log API call details first (this will always work)
            logger.info(
                f"API Call: {endpoint} | Status: {status_code} | Credits: {credits_used} | "
                f"Time: {response_time:.2f}s{' | Error: ' + error_message if error_message else ''}"
            )

            try:
                # Try to insert into Supabase
                supabase.table("api_calls").insert({
                    "endpoint": endpoint,
                    "status_code": status_code,
                    "error_message": error_message,
                    "credits_used": credits_used,
                    "response_time": response_time
                }).execute()
            except Exception as db_error:
                # Log database error but don't fail the whole operation
                logger.error(f"Failed to save API call to database: {db_error}")

        except Exception as e:
            # Log any other unexpected errors
            logger.error(f"Unexpected error in API call tracking: {str(e)}")

    async def add_monitor(self, url: str, interval: int):
        """Add a new URL to monitor."""
        try:
            # Get the monitor from the database
            monitor = supabase.table("monitors").select("*").eq("url", url).single().execute()
            if not monitor.data:
                raise ValueError(f"Monitor not found for URL: {url}")
            
            # Create initial full snapshot using Firecrawl
            await self._create_full_snapshot(url, monitor.data['id'])

        except Exception as e:
            logger.error(f"Error adding monitor: {e}")
            raise

    async def _create_full_snapshot(self, url: str, monitor_id: int):
        """Create a full snapshot with intelligent LLM-based extraction."""
        start_time = time.time()
        try:
            # First try with Firecrawl's JSON extraction
            result = self.firecrawl.scrape_url(url, {
                'formats': ['json', 'html'],
                'onlyMainContent': False,
                'waitFor': 2000,
                'jsonOptions': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'items': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'title': {'type': 'string'},
                                        'details': {'type': 'string'},
                                        'description': {'type': 'string'},
                                        'url': {'type': 'string'}
                                    },
                                    'required': ['title', 'details', 'url']
                                }
                            }
                        },
                        'required': ['items']
                    },
                    'prompt': """
                    Extract ALL job listings from this careers page. Each job posting should be in a div with class 'bg-white' and have:
                    - Title (in h3 tag)
                    - Details (in p tag with class 'text-sm text-gray-500')
                    - Description (in div.mt-2)
                    - URL (in 'Apply Now' link)
                    
                    IMPORTANT: You MUST return ALL jobs found in the 'items' array.
                    Each job should be a separate object in the array.
                    Do not combine jobs or skip any jobs.
                    Look for job listings in divs with class 'bg-white'.
                    """
                }
            })

            # Track API call
            await self._track_api_call('scrape_full', start_time, response=result)

            # Get content for snapshot
            content = result.get('html', '')
            content_hash = hashlib.md5(content.encode()).hexdigest() if content else ''

            # Create snapshot only if we have valid content and hash
            if content and content_hash:
                snapshot = await create_snapshot(monitor_id, content, content_hash)
                logger.info(f"Created snapshot with hash: {content_hash} and content length: {len(content)}")
            else:
                logger.error(f"Cannot create snapshot: empty content or hash. Content length: {len(content) if content else 0}")
                raise ValueError("Empty content or hash returned from Firecrawl")

            # Process and save extracted jobs
            jobs_data = []
            
            # Try primary extraction method (JSON)
            if 'json' in result and 'items' in result['json']:
                logger.info("Using primary extraction method (JSON)")
                jobs = result['json']['items']
                logger.info(f"Found {len(jobs)} jobs")
                
                for job in jobs:
                    try:
                        # Parse the details string
                        details = job.get('details', '').split('•')
                        job_type = details[0].strip() if len(details) > 0 else ''
                        location = details[1].strip() if len(details) > 1 else ''
                        salary_range = details[2].strip() if len(details) > 2 else ''

                        jobs_data.append({
                            'title': job.get('title', '').strip(),
                            'description': job.get('description', ''),
                            'url': job.get('url', ''),
                            'job_type': job_type,
                            'location': location,
                            'salary_range': salary_range
                        })
                    except Exception as e:
                        logger.error(f"Error processing job: {e}")
                        logger.error(f"Job data: {job}")
                        continue

            # If primary method failed, try fallback with HTML parsing
            if not jobs_data and 'html' in result:
                logger.info("Primary extraction failed, trying HTML parsing fallback")
                try:
                    soup = BeautifulSoup(result['html'], 'lxml')
                    job_cards = soup.select('.space-y-6 > div.bg-white')
                    
                    logger.info(f"Found {len(job_cards)} job cards via HTML parsing")
                    
                    for card in job_cards:
                        try:
                            title = card.select_one('h3').get_text(strip=True) if card.select_one('h3') else ''
                            details = card.select_one('p.text-sm.text-gray-500').get_text(strip=True) if card.select_one('p.text-sm.text-gray-500') else ''
                            description = card.select_one('div.mt-2').get_text(strip=True) if card.select_one('div.mt-2') else ''
                            url = card.select_one('a')['href'] if card.select_one('a') else ''
                            
                            # Parse details
                            detail_parts = details.split('•')
                            job_type = detail_parts[0].strip() if len(detail_parts) > 0 else ''
                            location = detail_parts[1].strip() if len(detail_parts) > 1 else ''
                            salary_range = detail_parts[2].strip() if len(detail_parts) > 2 else ''
                            
                            jobs_data.append({
                                'title': title,
                                'description': description,
                                'url': url,
                                'job_type': job_type,
                                'location': location,
                                'salary_range': salary_range
                            })
                        except Exception as e:
                            logger.error(f"Error processing HTML job card: {e}")
                            continue
                except Exception as e:
                    logger.error(f"Error in HTML parsing fallback: {e}")

            logger.info(f"Total jobs found: {len(jobs_data)}")

            if not jobs_data:
                logger.warning("No jobs found with either extraction method")
            else:
                logger.info(f"Processing {len(jobs_data)} jobs")
                for i, job_data in enumerate(jobs_data):
                    logger.info(f"Processing job {i+1}/{len(jobs_data)}")
                    logger.info(f"Job data: {job_data}")
                    
                    # Validate required fields
                    if not all(job_data.get(field) for field in ['title', 'description', 'url']):
                        logger.error(f"Missing required fields in job data: {job_data}")
                        logger.error(f"Missing fields: {[field for field in ['title', 'description', 'url'] if not job_data.get(field)]}")
                        continue

                    # Create job
                    try:
                        job = await create_job(
                            monitor_id=monitor_id,
                            title=job_data['title'],
                            description=job_data['description'],
                            url=job_data['url'],
                            metadata={
                                'location': job_data.get('location', ''),
                                'salary_range': job_data.get('salary_range', ''),
                                'job_type': job_data.get('job_type', ''),
                                'posted_date': job_data.get('posted_date', '')
                            }
                        )
                        logger.info(f"Created new job: {job_data['title']}")
                    except Exception as e:
                        logger.error(f"Error creating job: {e}")
                        continue

        except Exception as e:
            # Track the error
            await self._track_api_call('scrape_full', start_time, error=e)
            logger.error(f"Error creating full snapshot: {e}")
            raise

    async def _quick_check(self, url: str) -> tuple[str, str]:
        """Perform a quick check of the page for changes."""
        start_time = time.time()
        try:
            result = self.firecrawl.scrape_url(url, {
                'url': url,
                'formats': ['markdown']
            })
            
            # Track successful API call
            await self._track_api_call('scrape_quick', start_time, response=result)
            
            content = result.get('data', {}).get('markdown', '')
            content_hash = result.get('data', {}).get('metadata', {}).get('contentHash', '')
            return content, content_hash
        except Exception as e:
            # Track failed API call
            await self._track_api_call('scrape_quick', start_time, error=e)
            logger.error(f"Error in quick check: {e}")
            raise

    async def _check_page_changed(self, url: str, last_etag: str = None, last_modified: str = None) -> dict:
        """
        Check if page has changed using HTTP headers (no API costs).
        Returns dict with change status and new headers.
        """
        headers = {}
        if last_etag:
            headers['If-None-Match'] = last_etag
        if last_modified:
            headers['If-Modified-Since'] = last_modified

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, follow_redirects=True)
                
                # If we get a 304 Not Modified AND we have a previous snapshot, use that
                if response.status_code == 304 and last_etag:
                    return {
                        'changed': False,  # 304 = Not Modified
                        'etag': response.headers.get('ETag'),
                        'last_modified': response.headers.get('Last-Modified'),
                        'content': None,
                        'error': None
                    }
                else:
                    # Either the page changed or we need an initial snapshot
                    return {
                        'changed': True,
                        'etag': response.headers.get('ETag'),
                        'last_modified': response.headers.get('Last-Modified'),
                        'content': response.text,
                        'error': None
                    }
        except Exception as e:
            logger.error(f"Error checking page {url}: {str(e)}")
            return {
                'changed': True,  # Assume changed on error to be safe
                'etag': None,
                'last_modified': None,
                'content': None,
                'error': str(e)
            }

    def _calculate_content_hash(self, content: str) -> str:
        """Calculate hash of the main content area (ignoring headers, footers, etc.)"""
        try:
            # Parse HTML
            soup = BeautifulSoup(content, 'lxml')
            
            # Remove elements that change but don't matter
            for elem in soup.find_all(['script', 'style', 'meta', 'link', 'noscript']):
                elem.decompose()
            
            # Get clean text
            text = soup.get_text(separator=' ', strip=True)
            
            # Calculate hash
            return hashlib.md5(text.encode()).hexdigest()
        except Exception as e:
            logger.error(f"Error calculating content hash: {str(e)}")
            return hashlib.md5(content.encode()).hexdigest()  # Fallback to raw content

    async def _update_monitor_headers(self, monitor_id: int, etag: str = None, last_modified: str = None):
        """Update the monitor's HTTP cache headers."""
        try:
            update_data = {
                "last_check": datetime.utcnow().isoformat()
            }
            
            # Only add headers if they exist
            if etag is not None:
                update_data["last_etag"] = etag
            if last_modified is not None:
                update_data["last_modified"] = last_modified

            # Log the update attempt
            logger.info(f"Updating monitor {monitor_id} headers: {update_data}")
            
            # Perform the update
            result = supabase.table("monitors").update(update_data).eq("id", monitor_id).execute()
            
            if not result.data:
                logger.warning(f"No rows updated for monitor {monitor_id}")
            else:
                logger.info(f"Successfully updated headers for monitor {monitor_id}")
                
        except Exception as e:
            logger.error(f"Error updating monitor headers: {str(e)}")
            # Don't raise the exception - this is not critical enough to fail the whole check

    async def check_for_changes(self, monitor_id: int):
        """
        Three-phase check process to minimize API costs:
        1. HTTP header check (free)
        2. Content hash comparison (free)
        3. Firecrawl extraction (only if real changes detected)
        """
        # Get monitor details
        monitor = supabase.table("monitors").select("*").eq("id", monitor_id).single().execute()
        if not monitor.data:
            raise ValueError(f"Monitor {monitor_id} not found")
        
        monitor = monitor.data
        latest_snapshot = await get_latest_snapshot(monitor_id)
        
        # Check if we have all jobs
        jobs_count = supabase.table("jobs").select("count", count="exact").eq("monitor_id", monitor_id).execute()
        has_all_jobs = jobs_count.count >= 4 if jobs_count else False  # We expect 4 jobs from the test page
        
        # Log the current state
        logger.info(f"Current state for monitor {monitor_id}:")
        logger.info(f"Latest snapshot: {latest_snapshot['content_hash'] if latest_snapshot else 'None'}")
        logger.info(f"Last ETag: {monitor.get('last_etag', 'None')}")
        logger.info(f"Last Modified: {monitor.get('last_modified', 'None')}")
        logger.info(f"Jobs count: {jobs_count.count if jobs_count else 0}")
        logger.info(f"Has all jobs: {has_all_jobs}")

        try:
            # If we're missing jobs, force a full extraction
            if not has_all_jobs:
                logger.info("Missing jobs detected, forcing full extraction")
                await self._create_full_snapshot(monitor['url'], monitor_id)
                return []

            # Phase 1: Quick HTTP Check (Free)
            logger.info(f"Phase 1: HTTP check for monitor {monitor_id}")
            http_check = await self._check_page_changed(
                monitor['url'],
                last_etag=monitor.get('last_etag') if latest_snapshot else None,
                last_modified=monitor.get('last_modified') if latest_snapshot else None
            )

            if http_check['error']:
                logger.warning(f"HTTP check error for {monitor['url']}: {http_check['error']}")
                # Force full extraction on error
                await self._create_full_snapshot(monitor['url'], monitor_id)
                return []
            elif not http_check['changed'] and latest_snapshot:
                logger.info(f"No changes detected via HTTP check for monitor {monitor_id}")
                await self._update_monitor_headers(
                    monitor_id,
                    http_check['etag'],
                    http_check['last_modified']
                )
                return []

            # Phase 2: Content Hash Check (Free)
            if http_check['content']:
                logger.info(f"Phase 2: Content hash check for monitor {monitor_id}")
                current_hash = self._calculate_content_hash(http_check['content'])
                logger.info(f"Calculated hash: {current_hash}")
                
                if not latest_snapshot:
                    logger.info(f"No previous snapshot found for monitor {monitor_id}, creating initial snapshot")
                    await self._create_full_snapshot(monitor['url'], monitor_id)
                    return []
                elif current_hash == latest_snapshot['content_hash']:
                    logger.info(f"No significant changes detected via content hash for monitor {monitor_id}")
                    await self._update_monitor_headers(
                        monitor_id,
                        http_check['etag'],
                        http_check['last_modified']
                    )
                    return []
                else:
                    logger.info(f"Content hash changed for monitor {monitor_id}")
                    logger.info(f"Old hash: {latest_snapshot['content_hash']}")
                    logger.info(f"New hash: {current_hash}")
                    await self._create_full_snapshot(monitor['url'], monitor_id)
                    return []

            return []  # No changes detected

        except Exception as e:
            logger.error(f"Error in check_for_changes: {str(e)}")
            raise 