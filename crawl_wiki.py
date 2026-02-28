import requests
from bs4 import BeautifulSoup
import os
import time
from urllib.parse import urljoin, urlparse
from collections import deque

# --- CONFIGURATION ---
START_URL = "https://game8.co/games/Arknights-Endfield"
DOMAIN = "game8.co"
MAX_PAGES = 2000
OUTPUT_DIR = "data/wiki_crawl"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# --- IMPROVED SELECTORS FOR GAME8 ---
# These are the common containers Game8 uses for actual guide content
CONTENT_SELECTORS = [
    'div.archive-style-wrapper', 
    'div.archive-content', 
    'div#archive-html',
    'article'
]

def save_page(url, content):
    path_parts = urlparse(url).path.strip('/').split('/')
    # Create a descriptive name based on the URL path
    filename = "_".join(path_parts) if path_parts[0] else "index"
    filename = f"{filename[:150]}.txt" # Cap length for OS limits
    
    for char in '<>:"/\\|?*':
        filename = filename.replace(char, "_")

    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"URL: {url}\n\n")
        f.write(content)
    print(f"✅ Saved: {filename}")

def start_crawl():
    queue = deque([START_URL])
    visited_urls = set()
    
    # Standard Browser Header to avoid 403 Forbidden
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    print(f"Starting crawl at {START_URL}...")

    while queue and len(visited_urls) < MAX_PAGES:
        url = queue.popleft()
        if url in visited_urls:
            continue
        
        visited_urls.add(url)
        print(f"🕷️ Crawling ({len(visited_urls)}/{MAX_PAGES}): {url}")

        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"❌ Status {response.status_code} for {url}")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 1. FIND CONTENT USING MULTIPLE SELECTORS
            content_div = None
            for selector in CONTENT_SELECTORS:
                content_div = soup.select_one(selector)
                if content_div:
                    break
            
            if content_div:
                # Remove unwanted elements (ads, navs) before saving
                for unwanted in content_div.select('.a-ad, .p-entry__external-links'):
                    unwanted.decompose()
                
                text = content_div.get_text(separator='\n', strip=True)
                save_page(url, text)
                
                # 2. FIND AND QUEUE LINKS
                for link in content_div.find_all('a', href=True):
                    href = link['href']
                    full_url = urljoin(url, href)
                    
                    # Stay on domain and skip anchors/media
                    if DOMAIN in full_url and "#" not in href:
                        # Focus on Arknights-Endfield related paths
                        if "/games/Arknights-Endfield" in full_url and full_url not in visited_urls:
                            queue.append(full_url)
                
            else:
                print(f"⚠️ No content div found on {url}")

            time.sleep(1.0) # Polite delay for Game8 servers

        except Exception as e:
            print(f"❌ Error on {url}: {e}")

    print(f"--- Crawl Finished. Total pages visited: {len(visited_urls)} ---")

if __name__ == "__main__":
    start_crawl()