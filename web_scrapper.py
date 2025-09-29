from playwright.sync_api import sync_playwright
import pandas as pd
import json
from datetime import datetime
import time

# =============================================================================
# STEP 1: Scrape basic info (titles, dates, URLs)
# =============================================================================

def scrape_met_listings():
    """Get basic exhibition info from The Met"""
    print("\n📍 Scraping The Met listings...")
    exhibitions = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            page.goto("https://www.metmuseum.org/exhibitions", 
                     wait_until="networkidle", timeout=60000)
            time.sleep(3)  # Wait for dynamic content
            
            # Use article selector - we know this finds 42 items
            cards = page.query_selector_all("article")
            print(f"   Found {len(cards)} articles")
            
            for card in cards:
                try:
                    # Extract title - try multiple selectors
                    title = ""
                    for t_sel in ["h3", "h2", "h4", "[class*='title']", "a"]:
                        elem = card.query_selector(t_sel)
                        if elem:
                            text = elem.inner_text().strip()
                            if len(text) > 5:  # Make sure it's substantial
                                title = text
                                break
                    
                    # Extract date - try multiple selectors
                    date = ""
                    for d_sel in ["[class*='date']", "time", "span"]:
                        elem = card.query_selector(d_sel)
                        if elem:
                            date = elem.inner_text().strip()
                            break
                    
                    # Extract URL - try multiple ways
                    url = ""
                    link = card.query_selector("a")
                    if link:
                        url = link.get_attribute("href") or ""
                        if url and not url.startswith("http"):
                            url = f"https://www.metmuseum.org{url}"
                    
                    # If we have a title and URL, add it!
                    if title and url:
                        exhibitions.append({
                            "museum": "The Met",
                            "title": title,
                            "date": date,
                            "url": url
                        })
                        print(f"   ✓ {title[:60]}")
                        
                except Exception as e:
                    continue
            
            print(f"\n   ✅ Successfully extracted {len(exhibitions)} Met exhibitions")
                    
        except Exception as e:
            print(f"   ❌ Error: {e}")
        finally:
            browser.close()
    
    return exhibitions


def scrape_guggenheim_listings():
    """Get basic exhibition info from Guggenheim"""
    print("\n📍 Scraping Guggenheim listings...")
    exhibitions = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            page.goto("https://www.guggenheim.org/exhibitions", 
                     wait_until="networkidle", timeout=60000)
            time.sleep(2)
            
            # Find exhibition cards
            cards = page.query_selector_all("article")
            print(f"   Found {len(cards)} potential exhibitions")
            
            for card in cards:
                # Extract title
                title_elem = card.query_selector("h2, h3")
                title = title_elem.inner_text().strip() if title_elem else ""
                
                # Extract date (look for text with month names)
                date = ""
                for elem in card.query_selector_all("span, [class*='date']"):
                    text = elem.inner_text().strip()
                    if any(month in text.lower() for month in 
                           ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 
                            'jul', 'aug', 'sep', 'oct', 'nov', 'dec']):
                        date = text
                        break
                
                # Extract URL
                link = card.query_selector("a")
                url = ""
                if link:
                    href = link.get_attribute("href")
                    if href:
                        url = href if href.startswith("http") else f"https://www.guggenheim.org{href}"
                
                if title and url:
                    exhibitions.append({
                        "museum": "Guggenheim",
                        "title": title,
                        "date": date,
                        "url": url
                    })
                    print(f"   ✓ {title[:60]}")
                    
        except Exception as e:
            print(f"   ❌ Error: {e}")
        finally:
            browser.close()
    
    return exhibitions


# =============================================================================
# STEP 2: Get descriptions from individual pages
# =============================================================================

def get_description_from_url(url, museum_name, browser):
    """Visit a single URL and extract the description"""
    try:
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=30000)
        time.sleep(1)
        
        description = ""
        
        # Museum-specific selectors
        if "metmuseum.org" in url:
            selectors = [
                "div.exhibition__description p",
                "div[class*='description'] p",
                "div[class*='intro'] p",
                ".rich-text p",
                "article p"
            ]
            
            # Try each selector
            for selector in selectors:
                elems = page.query_selector_all(selector)
                if elems:
                    paragraphs = []
                    for elem in elems[:3]:  # Get up to 3 paragraphs
                        text = elem.inner_text().strip()
                        if len(text) > 20:  # Must be substantial
                            paragraphs.append(text)
                    
                    if paragraphs:
                        description = " ".join(paragraphs)
                        break
        
        elif "guggenheim.org" in url:
            selectors = [
                "div.exhibition-description p",
                "div[class*='description'] p",
                "div.content p",
                "article p"
            ]
            
            for selector in selectors:
                elems = page.query_selector_all(selector)
                if elems:
                    paragraphs = []
                    for elem in elems[:3]:
                        text = elem.inner_text().strip()
                        if len(text) > 20:
                            paragraphs.append(text)
                    
                    if paragraphs:
                        description = " ".join(paragraphs)
                        break
        
        # Fallback: try to find any substantial paragraph
        if not description:
            paragraphs = page.query_selector_all("p")
            for p in paragraphs[:10]:
                text = p.inner_text().strip()
                skip_words = ['cookie', 'privacy', 'menu', 'search', 'skip to']
                if len(text) > 50 and not any(word in text.lower() for word in skip_words):
                    description = text
                    break
        
        page.close()
        return description[:500]  # Limit to 500 characters
        
    except Exception as e:
        print(f"      ⚠ Could not get description: {str(e)[:50]}")
        try:
            page.close()
        except:
            pass
        return ""


def add_descriptions(exhibitions):
    """Add descriptions to each exhibition by visiting URLs"""
    print(f"\n📝 Fetching descriptions from {len(exhibitions)} pages...")
    print("   (This will take a few minutes)")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        for i, exhibition in enumerate(exhibitions, 1):
            print(f"   [{i}/{len(exhibitions)}] {exhibition['title'][:50]}...")
            
            description = get_description_from_url(
                exhibition['url'], 
                exhibition['museum'],
                browser
            )
            
            exhibition['description'] = description
            time.sleep(1)  # Be polite to servers
        
        browser.close()
    
    return exhibitions


# =============================================================================
# STEP 3: Save to CSV and JSON
# =============================================================================

def save_results(exhibitions):
    """Save exhibitions to CSV and JSON files"""
    if not exhibitions:
        print("\n⚠ No exhibitions to save!")
        return
    
    # Create DataFrame
    df = pd.DataFrame(exhibitions)
    
    # Add timestamp
    df['scraped_at'] = datetime.now().isoformat()
    
    # Generate filenames
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_file = f"nyc_museums_{timestamp}.csv"
    json_file = f"nyc_museums_{timestamp}.json"
    
    # Save CSV
    df.to_csv(csv_file, index=False, encoding='utf-8')
    
    # Save JSON
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(exhibitions, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print("\n" + "="*70)
    print(f"✅ SUCCESS! Scraped {len(df)} exhibitions")
    print("="*70)
    print(f"📄 Saved to: {csv_file}")
    print(f"📄 Saved to: {json_file}")
    print(f"\n📊 Breakdown by museum:")
    print(df['museum'].value_counts().to_string())
    
    # Show sample
    print(f"\n📋 Sample data:")
    print("="*70)
    for idx, row in df.head(3).iterrows():
        print(f"\n{row['museum']}: {row['title']}")
        print(f"Date: {row['date']}")
        if row.get('description'):
            print(f"Description: {row['description'][:150]}...")
        print(f"URL: {row['url']}")


# =============================================================================
# MAIN PROGRAM
# =============================================================================

def main():
    print("="*70)
    print("NYC MUSEUMS EXHIBITION SCRAPER")
    print("="*70)
    
    # Ask user what they want to do
    print("\nOptions:")
    print("1. Quick scrape (titles + URLs only) - FAST")
    print("2. Full scrape (includes descriptions) - SLOW but complete")
    print()
    choice = input("Enter 1 or 2: ").strip()
    
    if choice not in ["1", "2"]:
        print("Invalid choice, defaulting to option 1 (quick scrape)")
        choice = "1"
    
    # STEP 1: Get all listings
    all_exhibitions = []
    all_exhibitions.extend(scrape_met_listings())
    time.sleep(2)  # Be nice to servers
    all_exhibitions.extend(scrape_guggenheim_listings())
    
    print(f"\n✓ Collected {len(all_exhibitions)} exhibitions with titles and URLs")
    
    # STEP 2: Get descriptions if requested
    if choice == "2":
        print("\n" + "="*70)
        print("🔍 Now fetching descriptions from each exhibition page...")
        print("="*70)
        all_exhibitions = add_descriptions(all_exhibitions)
    else:
        print("\n⏩ Skipping descriptions (you chose option 1)")
        # Add empty description field
        for ex in all_exhibitions:
            ex['description'] = ""
    
    # STEP 3: Save everything
    save_results(all_exhibitions)
    
    print("\n✨ Done!")


if __name__ == "__main__":
    main()