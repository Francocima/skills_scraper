from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from seek_scraper_async_v6 import SeekScraper

# Create FastAPI instance
app = FastAPI(title="Seek Scraper API",
             description="API for scraping job listings from Seek.com.au")

# Define the request model
class ScraperRequest(BaseModel):
    search_url: str
    posted_time_limit: Optional[str] = None
    max_pages: Optional[int] = None
    num_jobs: Optional[int] = None

# Define the API endpoint
@app.post("/scrape")
async def scrape_jobs(request: ScraperRequest):
    try:
        async with SeekScraper() as scraper:
            jobs_data = await scraper.scrape_jobs(
                request.search_url,
                posted_time_limit=request.posted_time_limit,
                max_pages=request.max_pages,
                num_jobs=request.num_jobs
            )
            return {"status": "success", "data": jobs_data}
    except Exception as e:
        raise HTTPException(status_code=600, detail=str(e))


# Add a test endpoint
@app.get("/health-test")
async def root():
    return {"message": "Seek Scraper API is running. Health check OK."}

# Add a POST test endpoint
@app.post("/post-test")
async def root(request: ScraperRequest):
  body = await request.json()
  print(body)  # Debugging
  return {"message": "Data received", "data": body}

    
