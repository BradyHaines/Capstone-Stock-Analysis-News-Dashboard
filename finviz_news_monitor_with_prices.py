import requests
from bs4 import BeautifulSoup
import re
import time
from datetime import datetime
from openai import OpenAI
import yfinance as yf
from dateutil import parser as date_parser

# Initialize OpenAI client
client = OpenAI(api_key="")  # Replace with your actual key

seen_urls = set()

def get_latest_news():
    url = "https://finviz.com/news.ashx?v=3"
    headers = {'User-Agent': 'Mozilla/5.0'}
    soup = BeautifulSoup(requests.get(url, headers=headers).text, "html.parser")
    news_section = soup.find("div", id="news")

    if not news_section:
        return []

    rows = news_section.find_all("tr")
    for row in rows:
        td_tags = row.find_all("td")
        a_tag = row.find("a")

        if not a_tag or len(td_tags) < 2:
            continue

        title = a_tag.text.strip()
        link = "https://finviz.com" + a_tag['href']
        if link in seen_urls:
            continue

        time_info = td_tags[0].text.strip()
        raw_info = td_tags[1].text.strip()

        # Clean info block lines
        info_lines = [line.strip() for line in raw_info.split("\n") if line.strip()]
        publisher = info_lines[-1] if len(info_lines) >= 2 else "Unknown"
        # Detect tickers
        tickers = [line for line in info_lines if re.fullmatch(r"[A-Z]{2,5}", line) and line not in {"CEO", "USA", "GDP", "SEC", "HTS"}]

        return [{
            "title": title,
            "url": link,
            "publisher": publisher,
            "time_info": time_info,
            "tickers": list(set(tickers))
        }]

    return []

def get_stock_price(ticker):
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period="1d")
        return round(data["Close"].iloc[-1], 2)
    except:
        return "N/A"

def analyze_news(title):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a financial news analyst."},
                {"role": "user", "content": f'''
Analyze this financial news headline:

"{title}"

Return the result in this format:
Summary: <summary>
Sentiment: <Positive/Negative/Neutral>
Recommendation: <Buy/Hold/Sell>
'''}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {e}"

def get_current_datetime():
    now = datetime.now()
    human_time = now.strftime("%I:%M %p").lstrip("0")
    human_date = now.strftime("%m/%d/%Y")
    return human_time, human_date

def main():
    print("📡 Starting Finviz News Monitor... (Ctrl+C to stop)\n")
    try:
        while True:
            articles = get_latest_news()
            if articles:
                for article in articles:
                    if article["url"] in seen_urls:
                        continue
                    seen_urls.add(article["url"])

                    print("🆕 New Article Detected!")
                    print(f"📰 Title: {article['title']}")
                    print(f"🔗 URL: {article['url']}")
                    print(f"✍️ Publisher: {article['publisher']}")

                    current_time, current_date = get_current_datetime()
                    print(f"🕒 Time/Date: {article['time_info']} ago | {current_time}, {current_date}")

                    if article["tickers"]:
                        for ticker in article["tickers"]:
                            price = get_stock_price(ticker)
                            print(f"💲 Current Price for {ticker}: {price}")
                        print(f"🏷️ Stocks Mentioned: {', '.join(article['tickers'])}")

                    else:
                        print("🏷️ Stocks Mentioned: N/A")

                    print("\n💬 Sentiment Analysis:")
                    result = analyze_news(article['title'])
                    print(result)

                    print("\n⏳ Sleeping for 60 seconds...\n")
                    break  # Only process one new article at a time
            else:
                print("❌ No news articles found.\n⏳ Sleeping for 60 seconds...\n")
            time.sleep(60)

    except KeyboardInterrupt:
        print("\n🛑 Monitor stopped by user.")

if __name__ == "__main__":
    main()
