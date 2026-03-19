import os
import re
import time
from datetime import datetime
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

BASE_URL = "https://www.sanmigueldesalinas.es"
DOCS_DIR = "docs"
START_YEAR = 2023
START_MONTH = 1


def generate_monthly_urls():
    urls = []
    current = datetime.now()
    year = START_YEAR
    month = START_MONTH
    while (year, month) <= (current.year, current.month):
        urls.append(f"{BASE_URL}/{year}/{month:02d}/")
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
    return urls


def make_filename(url, title):
    slug = url.rstrip("/").split("/")[-1]
    slug = re.sub(r"[^\w\-]", "_", slug)
    return f"{slug}.txt"


def get_article_links(page, url):
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    soup = BeautifulSoup(page.content(), "html.parser")
    links = []
    for h2 in soup.find_all("h2", class_="entry-title"):
        a = h2.find("a")
        if a and a.get("href"):
            links.append(a["href"])
    return links


def scrape_article(page, url):
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    soup = BeautifulSoup(page.content(), "html.parser")

    # Title
    h1 = soup.find("h1", class_="entry-title")
    title = h1.get_text(strip=True) if h1 else "Unknown title"

    # Date
    date_span = soup.find("span", class_="published")
    date = date_span.get_text(strip=True) if date_span else "Unknown date"

    # Body — get all text inside the article tag, excluding nav/meta elements
    article = soup.find("article")
    if not article:
        return None

    # Remove unwanted elements
    for tag in article.find_all(["nav", "footer", "script", "style"]):
        tag.decompose()
    for tag in article.find_all(class_=["post-meta", "et_pb_post_hide_featured_image"]):
        tag.decompose()

    # Extract remaining text
    body = article.get_text(separator="\n", strip=True)

    return f"{title}\n\n{date}\n\n{body}"


def main():
    os.makedirs(DOCS_DIR, exist_ok=True)
    monthly_urls = generate_monthly_urls()
    print(
        f"Generated {len(monthly_urls)} monthly URLs from {START_YEAR}/{START_MONTH:02d} to present"
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Set a realistic user agent
        page.set_extra_http_headers(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )

        all_links = []
        for i, monthly_url in enumerate(monthly_urls):
            print(f"[{i+1}/{len(monthly_urls)}] Collecting links from {monthly_url}")
            try:
                links = get_article_links(page, monthly_url)
                all_links.extend(links)
                print(f"  Found {len(links)} articles")
                time.sleep(1)  # polite delay
            except Exception as e:
                print(f"  Error: {e}")
                continue

        print(f"\nTotal articles found: {len(all_links)}")

        # Deduplicate
        all_links = list(dict.fromkeys(all_links))
        print(f"After deduplication: {len(all_links)}")

        scraped = 0
        skipped = 0
        errors = 0

        for i, url in enumerate(all_links):
            filename = make_filename(url, "")
            filepath = os.path.join(DOCS_DIR, filename)

            if os.path.exists(filepath):
                skipped += 1
                continue

            print(f"[{i+1}/{len(all_links)}] Scraping: {url}")
            try:
                content = scrape_article(page, url)
                if content:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(content)
                    scraped += 1
                time.sleep(1)  # polite delay
            except Exception as e:
                print(f"  Error: {e}")
                errors += 1
                continue

        browser.close()

    print(f"\nDone. Scraped: {scraped}, Skipped: {skipped}, Errors: {errors}")
    print(f"Documents saved to {DOCS_DIR}/")


if __name__ == "__main__":
    main()
