from playwright.async_api import async_playwright
import time
from typing import List, Dict
import json
from urllib.parse import urljoin
import re
import asyncio



#It creates a class of functions
class SeekScraper:
    #First initializes the class with the playwright and the browser
    def __init__(self): #When defining a class, self ensures that each instance of the class can store and access its own attributes and call its own methods.
        
        self.base_url = "https://www.seek.com.au" #Sets the base URL for the scraper
        self.timeout = 15000

    #Both enter and exits functions will open the browser and context, and after using it, they will close it.  
    async def __aenter__(self): #The enter function will help use the with statement
        try:
            self.playwright = await async_playwright().start() #Starts a playwright session.
            self.browser = await self.playwright.chromium.launch(
                    headless=True,
                    args=['--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-gpu',
                    '--disable-software-rasterizer',
                    '--disable-extensions',
                    '--disable-background-networking',
                    '--disable-features=TranslateUI,BlinkGenPropertyTrees',
                    '--disable-default-apps',
                    '--disable-sync'
                    ]) #Launches google chrome. Headless = FALSE means that the browser will be visible.
            
            self.context = await self.browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                ) #Sets a new context for the browser
            self.page = await self.context.new_page() #Opens a new page in google chrome.
            
            return self 
        
        except Exception as e:
            print(f"Error in __aenter__: {str(e)}")

            if hasattr(self, 'context') and self.context:
                await self.context.close()
            if hasattr(self, 'browser') and self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright') and self.playwright:
                await self.playwright.stop()
            raise   
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.context.close()
        await self.browser.close()
        await self.playwright.stop()

    
    
    #Scroller for the main page to load all the job posts in the first page
    async def scroll_page(self, page, scroll_delay=0.5): #It sets fist the class instance, the page we are using, and the scroll_delay (this can be changed for faster scrolling)
        """Scroll the page to load all content."""
        last_height = await page.evaluate('document.documentElement.scrollHeight') #This will give the starting height of the webpage
        
        while True: #While the last_height is different from the new_height, it will keep scrolling
            # Scroll to bottom
            await page.evaluate('window.scrollTo(0, document.documentElement.scrollHeight)')
            await asyncio.sleep(scroll_delay)
            
            new_height = await page.evaluate('document.documentElement.scrollHeight') #After the scroll it evaluates the new height of the page.
            if new_height == last_height: #If the new height is equal to the last_height, it means it arrived to the last part of the page.
                break
            last_height = new_height

    def extract_job_id(self, url: str) -> str:
        """Extract job ID from URL."""
        try:
            # Find the part after 'job/' and before '?'
            start_index = url.find('/job/') + 5  # +5 to skip '/job/'
            end_index = url.find('?', start_index)
            
            if end_index == -1:  # If there's no '?', take until the end
                return url[start_index:]
            return url[start_index:end_index]
        
        except Exception as e:
            return "Job ID not found"


    #It opens the first job post to extract the data. It extracts the title, company and requirements. This all goes inside the extract_job_details function.
    async def extract_job_details(self, job_url: str) -> Dict: #It uses the job_url (the url to the actual job listing) as a string. Dict is used to ask the function to give back a dictionary.
        """Extract details from a single job posting."""
        try:
            page = await self.context.new_page() #Cause we need to enter each job card, it opens a new page with that link of the job {job_url}
            await page.goto(job_url) #Now it follows the link to the job post
            await page.wait_for_load_state('domcontentloaded') #It waits for the page to load. It can be replaced for 'domcontentloaded' if it is faster.
            
            await self.scroll_page(page) #It scrolls the page in look for the elementes (selectors)

            job_details = {
                'url': job_url,  # Adding URL to job details. This adds the job URL to the json outcome
                'job_id': self.extract_job_id(job_url) #This will extract the job ID from the URL. It uses the extract_job_id function to do so.
            }

            # Selectors taken from the HTML code.
            #title_selector = '[data-automation="job-detail-title"], .j1ww7nx7'
            #company_selector = '[data-automation="advertiser-name"], .y735df0'
            #description_selector = '[data-automation="jobAdDetails"], .YCeva_0'
            #posting_time_selector = '[data-automation="jobDetailsPage"] span:has-text("Posted")'           

            
            
            #Extract job title
            try:
                title_selector = '[data-automation="job-detail-title"], .j1ww7nx7'
                await page.wait_for_selector(title_selector, timeout=20000)
                title_element = page.locator(title_selector)
                job_details['title'] = await title_element.inner_text()
            except Exception as e:
                job_details['title'] = "Title not found"

            #Extract company name. Same as title_selector
            try:
                company_selector = '[data-automation="advertiser-name"], .y735df0'
                await page.wait_for_selector(company_selector, timeout=20000)
                company_element = page.locator(company_selector)
                job_details['company'] = await company_element.inner_text()
            except Exception as e:
                job_details['company'] = "Company not found"

            #Extract job requirements. Same as title_selector
            try:
                description_selector = '[data-automation="jobAdDetails"], .YCeva_0'
                await page.wait_for_selector(description_selector, timeout=20000)
                description_element = page.locator(description_selector)
                job_details['requirements'] = await description_element.inner_text()
            except Exception as e:
                job_details['requirements'] = "Requirements not found"

            #Trying to extract the element of the HTML code with the word "Posted" in it. This will give the posting time of the job.
            
            try:
                posting_time_selector = '[data-automation="jobDetailsPage"] span:has-text("Posted")'
                await page.wait_for_selector(posting_time_selector, timeout=20000)
                posting_elements = await page.locator(posting_time_selector).all()
                
                posting_time = "Posting time not found"
                for element in posting_elements:
                    text = await element.inner_text()
                    if "Posted" in text and ("ago" in text or "h" in text or "d" in text or "m" in text):
                        posting_time = text
                        break
            
                job_details['posting_time'] = posting_time
            
            except Exception as e:
                job_details['posting_time'] = "Posting time not found"


            await page.close()
            return job_details #This returns all the fields of the job_details dictionary.

        except Exception as e:
            print(f"Error extracting job details: {str(e)}")
            return None



    #Paginator to go to the next main page. It looks for the next page link using the page-{number} selector. It returns the URL of the next page.
    async def get_next_page_url(self, current_page: int) -> str: #It takes the current page as variable for starting point ( is set to = 1 after)
        """Get the URL for the next page using the correct page selector."""
        try:
            # The next page number will be current_page + 1. This is used to complete the locator for the CSS element in the HTML code.
            next_page_num = current_page + 1
            
            # Look for the next page link using the page-{number} selector
            next_page_selector = f'[data-automation="page-{next_page_num}"]' #This is the CSS selector for the next buttom in seek.
            
            
            next_link = await self.page.locator(next_page_selector).first #It uses the locator function to find the next_page_selector in the HTML code.
            if next_link and await next_link.is_visible(): #This will check if there is an actual "next" button and if it is visible.
                href = await next_link.get_attribute('href') #The href is the part of the URL that will change when switching pages "/jobs-in-australia?page=2". This way we retrieve the href to add it after
                if href:
                    return urljoin(self.base_url, href) #Now its joining the base_url "https://www.seek.com.au" with the href "/jobs-in-australia?page=2". This will return the new URL to go and scrape
            
            
            return None
            
        except Exception as e:
            
            return None
    
    def _convert_to_days(self, posting_time: str) -> float:
        """Convert posting time to days with logging."""
        print(f"\nConverting posting time: {posting_time}")
        
        try:
            if not posting_time or 'not found' in posting_time:
                print("Invalid posting time, returning infinity")
                return float('inf')
            
            # Remove "Posted" prefix and clean the string
            cleaned_posted_time = posting_time.lower().replace('posted', '').strip()
            print(f"Cleaned time string: {cleaned_posted_time}")

            match = re.match(r'(\d+)\s*([mhd])', cleaned_posted_time)
            if not match:
                print(f"Could not parse time format: {cleaned_posted_time}")
                return float('inf')
                        
            value, unit = match.groups()
            value = float(value)
                    
            # Convert to days based on unit
            if unit == 'm':
                days = value / (24 * 60)
                print(f"Converting {value} minutes to {days:.2f} days")
            elif unit == 'h':
                days = value / 24
                print(f"Converting {value} hours to {days:.2f} days")
            else:  # unit == 'd'
                days = value
                print(f"Already in days: {days}")
                        
            return days
                    
        except Exception as e:
            print(f"Error converting time: {str(e)}")
            return float('inf')
    
    def _is_within_time_limit(self, posting_time: str, time_limit: str) -> bool:
        """
        Check if a posting time is within the specified time limit.
        Returns True if the posting is within the limit, False otherwise.
        """
        if not time_limit:
            return True
            
        job_days = self._convert_to_days(posting_time)
        limit_days = self._convert_to_days(time_limit)
        
        print(f"Comparing job time ({job_days:.2f} days) with limit ({limit_days:.2f} days)")
        return job_days <= limit_days
    

    #The actual scraper of each of the job cards. It extracts the job URL and then extracts the job details. I set a maximum of jobs and pages to test it.
    #This fucntion will call the extract_job_details for each job card URL
    async def scrape_jobs(self, search_url: str, num_jobs: int = None, max_pages: int = None, posted_time_limit: str = None) -> List[Dict]:
            try:
                print(f"Starting scrape with search URL: {search_url}")
                
                # Add retry mechanism for initial page load
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        await self.page.goto(search_url, timeout=self.timeout, wait_until='domcontentloaded')
                        # Wait for specific element that indicates page is ready
                        await self.page.wait_for_selector(
                            'article[data-automation="normalJob"], [data-automation="jobCard"]',
                            timeout=self.timeout,
                            state='visible'
                        )
                        break
                    except Exception as e:
                        print(f"Attempt {attempt + 1} failed: {str(e)}")
                        if attempt == max_retries - 1:
                            raise
                        await asyncio.sleep(5)

                # Reduce scroll delay to speed up processing
                await self.scroll_page(self.page, scroll_delay=0.2)

                all_jobs_data = []
                current_page = 1
                jobs_scraped = 0

                while True:
                    print(f"\nScraping page {current_page}")
                    
                    # Get all job cards with timeout and retry
                    try:
                        job_cards = await self.page.locator('article[data-automation="normalJob"], [data-automation="jobCard"]').all()
                        print(f"Found {len(job_cards)} job cards on page {current_page}")

                        for card in job_cards:
                            if num_jobs and jobs_scraped >= num_jobs:
                                return all_jobs_data

                            try:
                                # Get link with explicit wait
                                link_element = card.locator('a').first
                                href = await link_element.get_attribute('href', timeout=5000)
                                if not href:
                                    continue

                                job_url = urljoin(self.base_url, str(href))
                                print(f"\nProcessing job {jobs_scraped + 1}: {job_url}")

                                # Add retry mechanism for job details
                                for detail_attempt in range(3):
                                    try:
                                        job_details = await self.extract_job_details(job_url)
                                        if job_details:
                                            break
                                    except Exception as e:
                                        print(f"Job detail attempt {detail_attempt + 1} failed: {str(e)}")
                                        await asyncio.sleep(2)

                                if job_details:
                                    if posted_time_limit and not self._is_within_time_limit(job_details['posting_time'], posted_time_limit):
                                        return all_jobs_data

                                    all_jobs_data.append(job_details)
                                    jobs_scraped += 1
                                    print(f"Successfully scraped job {jobs_scraped}")
                                
                            except Exception as e:
                                print(f"Error processing job card: {str(e)}")
                                continue

                    except Exception as e:
                        print(f"Error getting job cards: {str(e)}")
                        break

                    if max_pages and current_page >= max_pages:
                        break

                    # Get next page with retry
                    try:
                        next_page_url = await self.get_next_page_url(current_page)
                        if not next_page_url:
                            break

                        await self.page.goto(next_page_url, timeout=self.timeout, wait_until='domcontentloaded')
                        await asyncio.sleep(2)
                        current_page += 1
                    except Exception as e:
                        print(f"Error navigating to next page: {str(e)}")
                        break

                return all_jobs_data

            except Exception as e:
                print(f"Error in scrape_jobs: {str(e)}")
                return []

    async def save_to_json(self, jobs_data: List[Dict], filename: str = 'seek_jobs_v3.json'):
        """Save scraped data to JSON file."""
    # Ensure all job details are fully resolved
        scraped_jobs = [] #creates an empty list for scraped jobs
        for job in jobs_data:
        # Create a new dict with resolved values
            scraped_job = {}
            for key, value in job.items():
                if key == 'title' or key == 'company' or key == 'requirements' or key == 'posting_time':
                # Ensure these values are strings, not coroutines
                    scraped_job[key] = str(value)
            else:
                scraped_job[key] = value
            scraped_jobs.append(scraped_job)

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(scraped_jobs, f, ensure_ascii=False, indent=2)
        print(f"\nSaved {len(scraped_jobs)} jobs to {filename}")

async def main():
    search_url = "https://www.seek.com.au/data-analyst-jobs/in-Townsville-QLD-4810?sortmode=ListedDate"

    start_time = time.time()
    
    async with SeekScraper() as scraper:
      
        jobs_data = await scraper.scrape_jobs(search_url, posted_time_limit="1d ago", max_pages=2)
        if jobs_data:
            await scraper.save_to_json(jobs_data)
            print(f"\nScraped {len(jobs_data)} jobs successfully!")
            print(f"Time taken: {time.time() - start_time:.2f} seconds")
        else:
            print("No jobs were scraped. Check the debug output above for details.")

    ##print(jobs_data)

if __name__ == "__main__":
    asyncio.run(main())

