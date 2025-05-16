# crypto_news_aggregator/news_sources/cryptopanic_source.py
from datetime import datetime
import requests
from typing import List, Dict
from .base_source import BaseNewsSource
from ..utils.data_models import Article
from .. import config # For API key and settings

class CryptoPanicSource(BaseNewsSource):
    BASE_URL = "https://cryptopanic.com/api/v1/posts/"

    def __init__(self):
        super().__init__("CryptoPanic")
        if not config.CRYPTOPANIC_API_KEY:
            self.logger.warning("CryptoPanic API key not found. This source will be skipped.")
            self.api_key = None
        else:
            self.api_key = config.CRYPTOPANIC_API_KEY

    def _get_related_coins_from_item(self, item: Dict, target_coins_keywords: Dict[str, List[str]]) -> List[str]:
        """Determines related coin tickers from a CryptoPanic item and our target list."""
        found_tickers = []
        # CryptoPanic API provides 'currencies' with codes
        api_item_currencies = [c.get("code") for c in item.get("currencies", []) if c.get("code")]
        if not api_item_currencies: # Fallback to title if no currencies in API response
            title_lower = item.get("title", "").lower()
            for ticker, keywords in target_coins_keywords.items():
                if any(keyword.lower() in title_lower for keyword in keywords):
                    found_tickers.append(ticker)
        else:
            for ticker in target_coins_keywords.keys(): # Check our target tickers
                if ticker.upper() in [c.upper() for c in api_item_currencies]:
                    found_tickers.append(ticker)
        return list(set(found_tickers)) # Unique list


    def fetch_news(self, target_coins_keywords: Dict[str, List[str]]) -> List[Article]:
        if not self.api_key:
            return []

        self.logger.info("Fetching news from CryptoPanic")
        articles: List[Article] = []

        # CryptoPanic API uses currency tickers. Extract them from target_coins_keywords.
        # We'll use the keys of target_coins_keywords as the primary tickers.
        currency_tickers = ",".join(target_coins_keywords.keys())

        params = {
            "auth_token": self.api_key,
            "public": "true", # Get publicly available posts
            "currencies": currency_tickers,
        }
        if config.CRYPTOPANIC_FILTER:
            params["filter"] = config.CRYPTOPANIC_FILTER
        if config.CRYPTOPANIC_KIND:
            params["kind"] = config.CRYPTOPANIC_KIND

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=config.REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            raw_items = data.get("results", [])

            for item in raw_items:
                title = item.get("title")
                link = item.get("url")
                published_at_str = item.get("created_at") # E.g., "2024-03-15T10:00:00Z"
                source_domain = item.get("source", {}).get("domain", "CryptoPanic")

                if not title or not link or not published_at_str:
                    self.logger.debug(f"Skipping CryptoPanic item due to missing fields: {title}")
                    continue

                related_coins = self._get_related_coins_from_item(item, target_coins_keywords)
                if not related_coins: # Skip if not relevant to any of our target coins
                    self.logger.debug(f"Skipping CryptoPanic item as not related to target coins: {title}")
                    continue

                try:
                    article = Article(
                        title=title,
                        link=link,
                        published_at=datetime.fromisoformat(published_at_str.replace('Z', '+00:00')),
                        source_name=source_domain,
                        content_snippet=title, # CryptoPanic titles are often descriptive enough
                        related_coins=related_coins
                    )
                    articles.append(article)
                except Exception as e:
                    self.logger.error(f"Error creating Article from CryptoPanic item '{title}': {e}")

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching from CryptoPanic for tickers '{currency_tickers}': {e}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred with CryptoPanic: {e}")

        self.logger.info(f"Found {len(articles)} relevant articles from CryptoPanic")
        return articles