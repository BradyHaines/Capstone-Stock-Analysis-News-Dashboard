import os
import threading
from flask import Flask, render_template, request
from pymongo import MongoClient
from datetime import datetime
from monitor_with_mongo import run_monitoring_loop

app = Flask(__name__)

# MongoDB setup
mongo_client = MongoClient("mongodb://localhost:27017/")
db = mongo_client["stock_monitor"]
collection = db["stock_articles"]

def fetch_articles(ticker_filter="", sentiment_filter="All", sort_field="date_scraped", sort_order="desc"):
    query = {}
    if ticker_filter:
        query["tickers"] = ticker_filter
    if sentiment_filter != "All":
        query["analysis"] = {"$regex": f"Sentiment: {sentiment_filter}", "$options": "i"}

    sort_direction = -1 if sort_order == "desc" else 1
    return list(collection.find(query).sort(sort_field, sort_direction))

def start_monitor_thread():
    monitor_thread = threading.Thread(target=run_monitoring_loop, daemon=True)
    monitor_thread.start()

@app.route("/")
def index():
    ticker_filter = request.args.get("ticker", "").upper()
    sentiment_filter = request.args.get("sentiment", "All")
    sort_field = request.args.get("sort_field", "date")
    sort_order = request.args.get("sort_order", "desc")

    query = {}
    if ticker_filter:
        query["tickers"] = ticker_filter

    if sentiment_filter != "All":
        query["analysis"] = {"$regex": f"Sentiment: {sentiment_filter}", "$options": "i"}

    sort_by = "date_scraped" if sort_field == "date" else "analysis"
    direction = -1 if sort_order == "desc" else 1

    articles = list(collection.find(query).sort(sort_by, direction))

    last_updated = articles[0]["date_scraped"] if articles else None

    return render_template("index.html",
                           articles=articles,
                           last_updated=last_updated)


if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
        start_monitor_thread()
    app.run(debug=True, use_reloader=False)
