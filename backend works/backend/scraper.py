import requests
from bs4 import BeautifulSoup
import pandas as pd
import datetime
import os

# Configuration for the portals
PORTALS = {
    "NALSA": "https://nalsa.gov.in/notifications/",
    "CyberCrime": "https://cybercrime.gov.in/",
    "SancharSaathi": "https://ceir.sancharsaathi.gov.in/latest-updates",
}

def scrape_portal_requests(name, url):
    """Generic function to scrape a portal using requests."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CitizenAssistanceAI/1.0"
    }
    print(f"[*] Checking {name} for updates...")
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        updates = []
        
        # Logic specific to each site (customized based on 2026 layouts)
        if name == "NALSA":
            # Looking for notification lists
            items = soup.select(".notification-list li, .views-row")
            for item in items[:5]:
                title = item.get_text(strip=True)
                link = item.find('a')['href'] if item.find('a') else url
                updates.append({"title": title, "link": link})
        
        elif name == "CyberCrime":
            # Looking for "What's New" or marquee sections
            items = soup.select(".news-ticker a, .whats-new-item")
            for item in items[:5]:
                updates.append({"title": item.get_text(strip=True), "link": item.get('href')})

        return updates

    except Exception as e:
        print(f"[!] Error scraping {name}: {e}")
        return []

def main():
    all_updates = []
    for name, url in PORTALS.items():
        results = scrape_portal_requests(name, url)
        for res in results:
            all_updates.append({
                "portal": name,
                "title": res['title'],
                "link": res['link'],
                "scraped_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
    
    # Save to CSV (The "Database" Update)
    df = pd.DataFrame(all_updates)
    if not os.path.isfile('portal_updates.csv'):
        df.to_csv('portal_updates.csv', index=False)
    else: # Append only new updates
        df.to_csv('portal_updates.csv', mode='a', header=False, index=False)
        
    print(f"\n[✓] Database updated with {len(all_updates)} new items.")

if __name__ == "__main__":
    main()