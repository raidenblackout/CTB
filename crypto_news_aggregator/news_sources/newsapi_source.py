# crypto_news_aggregator/news_sources/newsapi_source.py
import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from .base_source import BaseNewsSource
from ..utils.data_models import Article
from .. import config # For API key and settings

class NewsApiSource(BaseNewsSource):
    BASE_URL = "https://newsapi.org/v2/everything"

    def __init__(self):
        super().__init__("NewsAPI.org")
        if not config.NEWSAPI_KEY:
            self.logger.warning("NewsAPI key not found. This source will be skipped.")
            self.api_key = None
        else:
            self.api_key = config.NEWSAPI_KEY

    def fetch_news(self, target_coins_keywords: Dict[str, List[str]], limit: Optional[int] = 10) -> List[Article]:
        if not self.api_key:
            return []

        all_articles: List[Article] = []
        self.logger.info(f"Fetching news from NewsAPI.org")

        for coin_ticker, keywords in target_coins_keywords.items():
            self.logger.debug(f"Querying NewsAPI for {coin_ticker} (Keywords: {keywords})")
            query = " OR ".join(f'"{k}"' for k in keywords) # Exact phrase matching
            from_date = (datetime.now() - timedelta(days=config.NEWSAPI_DAYS_AGO)).strftime('%Y-%m-%dT%H:%M:%S')

            params = {
                "q": query,
                "from": from_date,
                "sortBy": config.NEWSAPI_SORT_BY,
                "language": config.NEWSAPI_LANGUAGE,
                "apiKey": self.api_key,
                "pageSize": 50 # Request a decent number, NewsAPI might limit this
            }
            try:
                response = requests.get(self.BASE_URL, params=params, timeout=config.REQUEST_TIMEOUT)
                response.raise_for_status()
                data = response.json()

                raw_articles = data.get("articles", [])
                # For NewsAPI, the keywords used in the query are directly relevant to the coin
                # So we can assume articles returned are for this specific coin_ticker's keywords.
                # We'll use a simplified _filter_and_create_articles call by creating a temp target.
                temp_target_for_coin = {coin_ticker: keywords}

                articles_for_coin = self._filter_and_create_articles(
                    raw_items=raw_articles,
                    target_coins_keywords=temp_target_for_coin, # Filter specifically for this coin's keywords
                    title_key="title",
                    link_key="url",
                    date_key="publishedAt",
                    content_key="description", # NewsAPI provides 'description'
                    source_name_override=lambda item: item.get("source", {}).get("name", "NewsAPI") # Dynamic source name
                )
                # Assign the specific coin ticker to these articles
                for article in articles_for_coin:
                    article.related_coins = [coin_ticker]

                all_articles.extend(articles_for_coin)
                self.logger.info(f"  Found {len(articles_for_coin)} articles for {coin_ticker} via NewsAPI")

            except requests.exceptions.RequestException as e:
                self.logger.error(f"Error fetching from NewsAPI for '{query}': {e}")
            except Exception as e:
                self.logger.error(f"An unexpected error occurred with NewsAPI for '{query}': {e}")
        return all_articles