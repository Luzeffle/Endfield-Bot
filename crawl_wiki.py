import requests
from bs4 import BeautifulSoup
import os
import time
from urllib.parse import urljoin, urlparse

# --- CONFIGURATION ---
START_URL = "https://endfield.wiki.gg/"
DOMAIN = "endfield.wiki.gg"
MAX_PAGES = 1000
OUTPUT_DIR = "data/wiki_crawl"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

visited_urls = set()

def save_page(url, content):
    # Create a valid filename
    path_parts = urlparse(url).path.split('/')
    filename = path_parts[-1] if path_parts[-1] else "index"
    
    # Add .txt extension
    filename = f"{filename}.txt"
    
    # Clean illegal characters
    for char in '<>:"/\\|?*':
        filename = filename.replace(char, "_")

    path = os.path.join(OUTPUT_DIR, filename)
    
    # Write to file
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"URL: {url}\n\n")
        f.write(content)
    print(f"✅ Saved: {filename}")

def crawl(url):
    # 1. Check limits
    if url in visited_urls or len(visited_urls) >= MAX_PAGES:
        return
    
    visited_urls.add(url)
    print(f"🕷️ Crawling ({len(visited_urls)}/{MAX_PAGES}): {url}")
    
    try:
        headers = {'User-Agent': 'EndfieldBot/1.0'}
        
        # --- FIX: Only ONE request with timeout ---
        try:
            response = requests.get(url, headers=headers, timeout=10)
        except requests.exceptions.Timeout:
            print(f"⚠️ Timed out: {url}")
            return
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error: {e}")
            return

        if response.status_code != 200:
            print(f"❌ Failed to retrieve {url} (Status: {response.status_code})")
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 3. Extract Content
        content_div = soup.find('div', class_='mw-parser-output')
        
        if content_div:
            # Save the text
            text = content_div.get_text(separator='\n')
            save_page(url, text)
            
            # 4. Find Links
            for link in content_div.find_all('a', href=True):
                # Stop if we hit the page limit
                if len(visited_urls) >= MAX_PAGES:
                    break

                href = link['href']
                full_url = urljoin(url, href)
                
                # Filter bad links
                if (DOMAIN in full_url) and \
                   (":" not in href.split("/")[-1]) and \
                   ("#" not in href) and \
                   (full_url not in visited_urls):
                    
                    time.sleep(0.5) # Be polite
                    crawl(full_url)
        else:
            print(f"⚠️ No content div found on {url}")

    except Exception as e:
        print(f"❌ Critical Error: {e}")

# --- START ---
print(f"Starting crawl at {START_URL}...")
crawl(START_URL)
print("--- Crawl Finished ---")