import os
import sys
import asyncio
from dotenv import load_dotenv
from firecrawl import FirecrawlApp
import logging

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('scraper_test')

async def test_scraping():
    """Test the scraping functionality directly."""
    try:
        # Load environment variables
        load_dotenv()
        
        # Initialize Firecrawl
        firecrawl = FirecrawlApp(api_key=os.getenv("FIRECRAWL_API_KEY"))
        logger.info("Initialized Firecrawl")

        # Test URL
        test_url = "https://kappachan.github.io/GigSniper/"
        logger.info(f"Testing scraping for URL: {test_url}")

        # Test direct scraping
        result = firecrawl.scrape_url(
            test_url,
            {
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
            }
        )

        # Log the full response for debugging
        logger.info("Full Firecrawl response:")
        logger.info(result)

        # Process extracted jobs
        if 'json' in result and 'items' in result['json']:
            jobs = result['json']['items']
            logger.info(f"Found {len(jobs)} jobs")
            
            for i, job in enumerate(jobs, 1):
                logger.info(f"\nJob {i}:")
                logger.info(f"Title: {job.get('title', '')}")
                logger.info(f"Details: {job.get('details', '')}")
                logger.info(f"Description: {job.get('description', '')}")
                logger.info(f"URL: {job.get('url', '')}")
                
                # Parse the details string
                details = job.get('details', '').split('•')
                job_type = details[0].strip() if len(details) > 0 else ''
                location = details[1].strip() if len(details) > 1 else ''
                salary_range = details[2].strip() if len(details) > 2 else ''
                
                logger.info("Parsed details:")
                logger.info(f"- Job Type: {job_type}")
                logger.info(f"- Location: {location}")
                logger.info(f"- Salary Range: {salary_range}")

        # Test fallback HTML parsing
        logger.info("\nTesting fallback HTML parsing:")
        if 'html' in result:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(result['html'], 'lxml')
            job_cards = soup.select('.space-y-6 > div.bg-white')
            
            logger.info(f"Found {len(job_cards)} job cards via HTML parsing")
            
            for i, card in enumerate(job_cards, 1):
                title = card.select_one('h3').get_text(strip=True) if card.select_one('h3') else ''
                details = card.select_one('p.text-sm.text-gray-500').get_text(strip=True) if card.select_one('p.text-sm.text-gray-500') else ''
                description = card.select_one('div.mt-2').get_text(strip=True) if card.select_one('div.mt-2') else ''
                url = card.select_one('a')['href'] if card.select_one('a') else ''
                
                logger.info(f"\nHTML Parsed Job {i}:")
                logger.info(f"Title: {title}")
                logger.info(f"Details: {details}")
                logger.info(f"URL: {url}")

    except Exception as e:
        logger.error(f"Error in test_scraping: {e}", exc_info=True)

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_scraping()) 