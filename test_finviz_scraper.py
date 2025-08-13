import requests
from bs4 import BeautifulSoup

def fetch_latest_article():
    url = "https://finviz.com/news.ashx?v=3"
    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    news_table = soup.find("table", class_="t-home-table")
    if not news_table:
        print("❌ News table not found.")
        return

    first_row = news_table.find("tr")
    if not first_row:
        print("❌ No rows found in the news table.")
        return

    link_tag = first_row.find("a")
    source_tag = first_row.find_all("td")[-1] if first_row.find_all("td") else None

    if link_tag:
        title = link_tag.text.strip()
        url = "https://finviz.com" + link_tag['href']
        source = source_tag.text.strip() if source_tag else "Unknown"
        print("✅ Latest Article Detected:")
        print(f"📰 Title: {title}")
        print(f"🔗 URL: {url}")
        print(f"🗞️ Source: {source}")
    else:
        print("❌ No article link found.")

fetch_latest_article()
