import requests
from bs4 import BeautifulSoup
import re
import time
from datetime import datetime
from openai import OpenAI
import yfinance as yf
from pymongo import MongoClient

# MongoDB setup
mongo_client = MongoClient("mongodb://localhost:27017/")
db = mongo_client["stock_monitor"]
collection = db["stock_articles"]

# OpenAI API Key
client = OpenAI(api_key="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")  # Replace with your real key

seen_urls = set()

ticker_blacklist = {
    "USA", "CEO", "TV", "CNBC", "SEC", "AI", "GDP", "WSJ", "PR", "INC", "LLC",
    "S&P", "ETF", "IPO", "EPS", "DJIA", "TSX", "NYT", "NEWS", "USD", "YEN"
}

def get_latest_news():
    url = "https://finviz.com/news.ashx?v=3"
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
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
        raw_url = a_tag['href']
        link = raw_url if raw_url.startswith("http") else "https://finviz.com" + raw_url
        if link in seen_urls:
            continue

        time_info = td_tags[0].text.strip()
        info_text = td_tags[1].text.strip()

        info_lines = [line.strip() for line in info_text.split("\n") if line.strip()]
        publisher = info_lines[-1] if len(info_lines) >= 1 else "Unknown"

        tickers = [line for line in info_lines if re.fullmatch(r"[A-Z]{1,5}", line)
                   and line.upper() not in ticker_blacklist]

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

def run_monitoring_loop():
    print("📡 Starting Finviz News Monitor... (Ctrl+C to stop)\n")
    while True:
        try:
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

                    price_dict = {}
                    if article["tickers"]:
                        for ticker in article["tickers"]:
                            price = get_stock_price(ticker)
                            price_dict[ticker] = price
                            print(f"💲 Current Price for {ticker}: ${price}")
                        print(f"🏷️ Stocks Mentioned: {', '.join(article['tickers'])}")
                    else:
                        print("🏷️ Stocks Mentioned: N/A")

                    print("\n💬 Sentiment Analysis:")
                    analysis = analyze_news(article['title'])
                    print(analysis)

                    doc = {
                        "title": article['title'],
                        "url": article['url'],
                        "publisher": article['publisher'],
                        "time_info": article['time_info'],
                        "date_scraped": f"{current_date} {current_time}",
                        "tickers": article['tickers'],
                        "prices": price_dict,
                        "analysis": analysis
                    }
                    collection.insert_one(doc)
                    print("✅ Stored article in MongoDB.\n")

                    print("⏳ Sleeping for 60 seconds...\n")
                    break  # Only handle one new article at a time
            else:
                print("❌ No news articles found.\n⏳ Sleeping for 60 seconds...\n")

            time.sleep(60)

        except Exception as e:
            print(f"❌ Error: {e}\n⏳ Sleeping for 60 seconds...\n")
            time.sleep(60)

# Uncomment this if running directly for testing:
# if __name__ == "__main__":
#     run_monitoring_loop()
