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

    #Both enter and exits functions will open the browser and context, and after using it, they will close it.  
    async def __aenter__(self): #The enter function will help use the with statement
        self.playwright = await async_playwright().start() #Starts a playwright session.
        self.browser = await self.playwright.chromium.launch(headless=False) #Launches google chrome. Headless = FALSE means that the browser will be visible.
        self.context = await self.browser.new_context() #Sets a new context for the browser
        self.page = await self.context.new_page() #Opens a new page in google chrome.
        return self  
        
    
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

            # Selectors taken from the HTML code.
            title_selector = '[data-automation="job-detail-title"], .j1ww7nx7'
            company_selector = '[data-automation="advertiser-name"], .y735df0'
            description_selector = '[data-automation="jobAdDetails"], .YCeva_0'
            posting_time_selector = '[data-automation="jobDetailsPage"] span:has-text("Posted")'           

            job_details = {
                'url': job_url,  # Adding URL to job details. This adds the job URL to the json outcome
                'job_id': self.extract_job_id(job_url) #This will extract the job ID from the URL. It uses the extract_job_id function to do so.
            }
            
            #Extract job title
            try: #Uses the try sentence to extract the job title
                await page.wait_for_selector(title_selector, timeout=20000) #It uses the function page.wait to mention the selector it must look for and the time it must wait for it to appear.
                job_details['title'] = page.locator(title_selector).inner_text() #Uses the page.locator to locate the title_selector (CCS code) and then uses the inner_text() function to extract the text.
            
            except Exception as e: 
            
                job_details['title'] = "Title not found"

            #Extract company name. Same as title_selector
            try:
                await page.wait_for_selector(company_selector, timeout=20000)
                job_details['company'] = await page.locator(company_selector).inner_text()
            
            except Exception as e:
            
                job_details['company'] = "Company not found"

            #Extract job requirements. Same as title_selector
            try:
                await page.wait_for_selector(description_selector, timeout=20000)
                job_details['requirements'] = await page.locator(description_selector).inner_text()
            
            except Exception as e:
            
                job_details['requirements'] = "Requirements not found"

            #Trying to extract the element of the HTML code with the word "Posted" in it. This will give the posting time of the job.
            
            try:
                await page.wait_for_selector(posting_time_selector, timeout=20000)
                posting_elements = await page.locator(posting_time_selector).all()
            
            # Loop through all elements that contain "Posted" and get the first valid one
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
    async def scrape_jobs(self, search_url: str, num_jobs: int = None, max_pages: int = None, posted_time_limit: str = None) -> List[Dict]: #It uses the self instance, the search_url (the URL of the search), num_jobs (the maximum number of jobs to scrape) and max_pages (the maximum number of pages to scrape). It is asked to return a dictionary response
        """Scrape multiple job listings across multiple pages."""
        try:
            print(f"Starting scrape with search URL: {search_url}")
            await self.page.goto(search_url) #It opens the search_url of the job card
            await self.page.wait_for_load_state('domcontentloaded') #could be replaced by 'domcontentloaded' if it is faster
            

            #Sets current_page = 1 to start from the first page. jobs_scraped = 0 to start from the first job. Also sets current_page = 1 for starting in the first page. It sets the starting point
            all_jobs_data = [] #Empty list to populate with the results
            current_page = 1
            jobs_scraped = 0 #How many job have been scraped at the beggining. This will be growing as we keep scraping

            while True: #it will keep running until there is no more data retireved or the break statement
                print(f"\nScraping page {current_page}")
                await self.scroll_page(self.page) #This will scroll through the job card url looking for the selectors

                # Find all job cards on current page
                job_cards = await self.page.locator('article[data-automation="normalJob"], [data-automation="jobCard"]').all() #This will locate the CSS selector for job cards in the HTML code
                print(f"Found {len(job_cards)} job cards on page {current_page}")

                # Process each job card. This wil enter each job card to look for the JOb_details
                for card in job_cards: #Loop to go through each job card
                    try:
                        if num_jobs and jobs_scraped >= num_jobs: #This will give the end of the function running. When we get to the max amount of jobs set in num_jobs.
                            
                            return all_jobs_data

                        # Get job URL
                        job_link = card.locator('a').first
                        href = await job_link.get_attribute('href') #This will get the href of the job card and combine it with the job linkURL
                        if not href:
                            continue

                        href = str(href)
                        job_url = urljoin(self.base_url, href)
                        print(f"\nProcessing job {jobs_scraped + 1}")
                        print(f"Job URL: {job_url}")
                        

                        # Extract job details
                        job_details = await self.extract_job_details(job_url)
                        if not job_details:
                            print("Failed to extract job details")
                            continue

                        posting_time = job_details['posting_time']
                        print(f"Job posting time: {posting_time}")
                        
                            # Check if we've reached our target posting time
                        if posted_time_limit and not self._is_within_time_limit(posting_time, posted_time_limit):
                            # Convert posting times to days for comparison
                            print(f"Job posted {posting_time} exceeds time limit of {posted_time_limit}")
                            return all_jobs_data
                                              
                        all_jobs_data.append(job_details)
                        jobs_scraped += 1
                        print(f"Successfully scraped job {jobs_scraped}")

                    except Exception as e:
                        print(f"Error processing job card: {str(e)}")
                        continue

                # Check if we should continue to next page
                if max_pages and current_page >= max_pages:
                    
                    break

                # Get next page URL using the correct selector
                next_page_url = await self.get_next_page_url(current_page)
                if not next_page_url:
                    
                    break

                # Navigate to next page
                
                await self.page.goto(next_page_url)
                await self.page.wait_for_load_state('domcontentloaded')
                await asyncio.sleep(3)  # Wait for page to stabilize
                current_page += 1

            return all_jobs_data #This will return all the details scraped from each card in the dictionary

        except Exception as e:
            print(f"Error in scrape_jobs: {str(e)}")
            return []
    


    async def save_to_json(self, jobs_data: List[Dict], filename: str = 'seek_jobs_v3.json'):
        """Save scraped data to JSON file."""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(jobs_data, f, ensure_ascii=False, indent=2)
        print(f"\nSaved {len(jobs_data)} jobs to {filename}")

async def main():
    search_url = "https://www.seek.com.au/data-analyst-jobs/in-Brisbane-QLD-4000?page=1&sortmode=ListedDate"

    start_time = time.time()
    
    async with SeekScraper() as scraper:
      
        jobs_data = await scraper.scrape_jobs(search_url, posted_time_limit="1d ago", max_pages=20)
        if jobs_data:
            await scraper.save_to_json(jobs_data)
            print(f"\nScraped {len(jobs_data)} jobs successfully!")
            print(f"Time taken: {time.time() - start_time:.2f} seconds")
        else:
            print("No jobs were scraped. Check the debug output above for details.")

if __name__ == "__main__":
    asyncio.run(main())