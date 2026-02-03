"""
Text Scraper Module
Extracts clean text content from websites.
"""
import requests
from bs4 import BeautifulSoup
import pandas as pd
from config import REQUEST_TIMEOUT, TEXT_LIMIT


def scrape_website_text(url: str, max_retries: int = 3) -> dict:
    """
    Visits the website and extracts visible text plus navigation signals.
    Includes retry logic with HTTPS/HTTP fallback.
    
    Returns:
        dict: {
            "text_content": str,
            "nav_links": list[str],
            "meta_description": str,
            "error": str or None
        }
    """
    result = {
        "text_content": "",
        "nav_links": [],
        "meta_description": "",
        "error": None
    }
    
    if pd.isna(url) or url == "":
        result["error"] = "No URL provided"
        return result
    
    # Clean URL
    original_url = url
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }
    
    # Try different URL variations
    urls_to_try = [url]
    if url.startswith('https://'):
        urls_to_try.append(url.replace('https://', 'http://'))  # HTTP fallback
    if 'www.' not in url:
        urls_to_try.append(url.replace('://', '://www.'))  # Add www
    
    last_error = None
    
    for try_url in urls_to_try:
        for attempt in range(max_retries):
            try:
                print(f"   Scraping: {try_url}..." + (f" (attempt {attempt+1})" if attempt > 0 else ""))
                
                # Try with SSL verification first, then without if it fails
                try:
                    response = requests.get(try_url, headers=headers, timeout=REQUEST_TIMEOUT, verify=True)
                except requests.exceptions.SSLError:
                    # Retry without SSL verification for problematic certificates
                    import urllib3
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                    response = requests.get(try_url, headers=headers, timeout=REQUEST_TIMEOUT, verify=False)
                
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract meta description
                meta_tag = soup.find('meta', attrs={'name': 'description'})
                if meta_tag and meta_tag.get('content'):
                    result["meta_description"] = meta_tag.get('content', '')
                
                # Extract navigation links (before removing nav elements)
                result["nav_links"] = extract_nav_links(soup)
                
                # Clean up: remove scripts, styles, etc. for text extraction
                for element in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
                    element.extract()
                
                # Extract and clean text
                text = soup.get_text(separator=' ')
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                clean_text = ' '.join(chunk for chunk in chunks if chunk)
                
                result["text_content"] = clean_text[:TEXT_LIMIT]
                return result  # Success!
                
            except Exception as e:
                last_error = e
                import time
                time.sleep(1)  # Brief pause before retry
    
    result["error"] = f"Scraping Error: {last_error}"
    return result


def extract_nav_links(soup: BeautifulSoup) -> list:
    """
    Extracts navigation link texts to identify business activities.
    Looks for common nav patterns and link texts.
    """
    nav_links = []
    
    # Find all navigation elements
    nav_elements = soup.find_all(['nav', 'header'])
    
    for nav in nav_elements:
        links = nav.find_all('a')
        for link in links:
            link_text = link.get_text(strip=True)
            if link_text and len(link_text) < 50:  # Filter out long non-nav text
                nav_links.append(link_text)
    
    # Also check for common menu patterns
    menu_classes = ['menu', 'nav', 'navigation', 'navbar']
    for cls in menu_classes:
        menus = soup.find_all(class_=lambda x: x and cls in x.lower() if x else False)
        for menu in menus:
            links = menu.find_all('a')
            for link in links:
                link_text = link.get_text(strip=True)
                if link_text and len(link_text) < 50 and link_text not in nav_links:
                    nav_links.append(link_text)
    
    return nav_links
