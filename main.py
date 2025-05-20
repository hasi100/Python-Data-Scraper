import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import random
from urllib.parse import quote
import os
from fake_useragent import UserAgent

class GoogleScraper:
    def __init__(self):
        self.data = []
        self.ua = UserAgent()
        self.headers = {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        self.proxies = None  # You might want to add proxies to avoid being blocked

    def create_search_query(self, platform, niche):
        """Create a search query for Google"""
        email_domains = '"@gmail.com" OR "@yahoo.com" OR "@hotmail.com" OR "@outlook.com" OR "@aol.com"'
        query = f'site:{platform}.com "{niche}" {email_domains}'
        return query
    
    def extract_emails(self, text):
        """Extract email addresses from text"""
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, text)
        return emails[0] if emails else "NA"
    
    def extract_phone(self, text):
        """Extract phone numbers from text"""
        # This pattern looks for various phone number formats
        phone_pattern = r'(?:\+\d{1,3}[-\.\s]?)?\(?\d{3}\)?[-\.\s]?\d{3}[-\.\s]?\d{4}'
        phones = re.findall(phone_pattern, text)
        return phones[0] if phones else "NA"
    
    def extract_name_parts(self, text, handle):
        """Attempt to extract first and last name"""
        # Try to extract from handle first (common format: firstname.lastname)
        name_parts = handle.split('.')
        if len(name_parts) >= 2 and all(part.isalpha() for part in name_parts):
            return name_parts[0].capitalize(), name_parts[1].capitalize()
        
        # Otherwise try to find name patterns in the text
        name_pattern = r'(?:by|from|contact)\s+([A-Z][a-z]+)\s+([A-Z][a-z]+)'
        matches = re.search(name_pattern, text)
        if matches:
            return matches.group(1), matches.group(2)
        
        return "NA", "NA"
    
    def extract_business_name(self, text):
        """Extract potential business name"""
        # Look for business indicators followed by capitalized words
        business_pattern = r'(?:Company|Studio|Design|LLC|Inc|Services|Enterprise):\s*([A-Z][A-Za-z\s]+)(?:\.|$)'
        matches = re.search(business_pattern, text)
        if matches:
            return matches.group(1).strip()
        
        # Try to find other business name patterns
        caps_words_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s+(?:LLC|Inc|Design|Studio|Services)'
        matches = re.search(caps_words_pattern, text)
        if matches:
            return matches.group(0).strip()
        
        return "NA"
    
    def parse_result(self, result, platform):
        """Parse a single search result"""
        try:
            title = result.find('h3').text if result.find('h3') else ""
            snippet = result.find('div', {'class': 'VwiC3b'})
            snippet_text = snippet.text if snippet else ""
            url_element = result.find('a')
            url = url_element['href'] if url_element and 'href' in url_element.attrs else "NA"
            
            # Extract full text for parsing
            full_text = f"{title} {snippet_text}"
            
            # Extract Instagram handle/username from URL
            handle = "NA"
            if platform.lower() == "instagram":
                handle_match = re.search(r'instagram\.com/([^/\s]+)', url)
                if handle_match:
                    handle = handle_match.group(1)
            
            # Extract information
            email = self.extract_emails(full_text)
            phone = self.extract_phone(full_text)
            first_name, last_name = self.extract_name_parts(full_text, handle)
            business_name = self.extract_business_name(full_text)
            
            # If handle exists but first name is NA, use handle as first name
            if handle != "NA" and first_name == "NA":
                first_name = handle
            
            # Create profile link
            profile_link = f"https://www.{platform}.com/{handle}" if handle != "NA" else url
            
            return {
                "First Name": first_name,
                "Last Name": last_name,
                "Business Name": business_name,
                f"{platform.capitalize()} Link": profile_link,
                "Email": email,
                "Phone Number": phone
            }
        except Exception as e:
            print(f"Error parsing result: {e}")
            return {
                "First Name": "NA",
                "Last Name": "NA",
                "Business Name": "NA",
                f"{platform.capitalize()} Link": "NA",
                "Email": "NA",
                "Phone Number": "NA"
            }
    
    def scrape_google_page(self, query, page=0):
        """Scrape a single page of Google search results"""
        start = page * 10  # Google shows 10 results per page
        url = f"https://www.google.com/search?q={quote(query)}&start={start}"
        
        try:
            # Random delay to avoid being blocked
            time.sleep(random.uniform(2, 5))
            
            # Update the user agent for each request to vary the fingerprint
            self.headers['User-Agent'] = self.ua.random
            
            response = requests.get(url, headers=self.headers, proxies=self.proxies)
            
            if response.status_code != 200:
                print(f"Failed to retrieve page {page+1}: Status code {response.status_code}")
                return False
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all search results
            results = soup.find_all('div', {'class': 'g'})
            
            if not results:
                # Try alternative class for results
                results = soup.find_all('div', {'jsname': 'Cpkphb'})
            
            if not results:
                print(f"No results found on page {page+1}")
                return False
            
            print(f"Found {len(results)} results on page {page+1}")
            return results
            
        except Exception as e:
            print(f"Error scraping page {page+1}: {e}")
            return False
    
    def scrape_google(self, platform, niche, max_pages=5):
        """Scrape multiple pages of Google search results"""
        query = self.create_search_query(platform, niche)
        print(f"Starting search for: {query}")
        
        for page in range(max_pages):
            print(f"Scraping page {page+1}...")
            results = self.scrape_google_page(query, page)
            
            if not results:
                print(f"No more results or error on page {page+1}. Stopping.")
                break
            
            for result in results:
                parsed_data = self.parse_result(result, platform)
                if parsed_data["Email"] != "NA":  # Only add if we found an email
                    self.data.append(parsed_data)
            
            print(f"Total records found so far: {len(self.data)}")
        
        return self.data
    
    def save_to_excel(self, filename="scraped_data.xlsx"):
        """Save the scraped data to an Excel file"""
        if not self.data:
            print("No data to save.")
            return
        
        df = pd.DataFrame(self.data)
        df.to_excel(filename, index=False)
        print(f"Data saved to {filename}")
        print(f"Total records: {len(df)}")

def main():
    scraper = GoogleScraper()
    
    platform = input("Enter social media platform (e.g., instagram, facebook, linkedin): ").strip().lower()
    niche = input("Enter niche (e.g., Landscape, Cleaning, Roofing): ").strip()
    max_pages = int(input("Enter maximum number of pages to scrape (default: 5): ") or "5")
    output_file = input("Enter output filename (default: scraped_data.xlsx): ") or "scraped_data.xlsx"
    
    print(f"\nStarting scraper for {platform} profiles in the {niche} niche...")
    scraper.scrape_google(platform, niche, max_pages)
    scraper.save_to_excel(output_file)
    print("\nScraping completed!")

if __name__ == "__main__":
    main()