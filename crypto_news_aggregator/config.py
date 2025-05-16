# crypto_news_aggregator/config.py
import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")
CRYPTOPANIC_API_KEY = os.getenv("CRYPTOPANIC_API_KEY")

# Target Coins and their keywords
# Structure: "TICKER": ["Keyword1", "Keyword2", "Full Name"]
TARGET_COINS = {
    "BTC": ["Bitcoin", "BTC"],
    "ETH": ["Ethereum", "ETH", "Ether"],
    "SOL": ["Solana", "SOL"],
    "ADA": ["Cardano", "ADA"],
    # Add more coins as needed
}

# RSS Feeds
# Structure: "Source Name": "URL"
RSS_FEEDS_CONFIG = {
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "CoinTelegraph": "https://cointelegraph.com/rss",
    "BitcoinMagazine": "https://bitcoinmagazine.com/feed",
}

# NewsAPI settings
NEWSAPI_DAYS_AGO = 3 # How many days back to fetch news from NewsAPI
NEWSAPI_LANGUAGE = "en"
NEWSAPI_SORT_BY = "publishedAt" # relevance, popularity, publishedAt

# CryptoPanic settings
CRYPTOPANIC_FILTER = "important" # Optional: hot|bullish|bearish|lol|toxic|importanti|saved
CRYPTOPANIC_KIND = "news" # Optional: news|media

# General settings
MAX_ARTICLES_PER_SOURCE_TYPE = 50 # Max articles to process from each major source type (RSS, NewsAPI, CryptoPanic)
REQUEST_TIMEOUT = 15 # Seconds