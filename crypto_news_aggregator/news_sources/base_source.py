# crypto_news_aggregator/news_sources/base_source.py
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Dict, Optional
from ..utils.data_models import Article
from ..utils.helpers import logger

class BaseNewsSource(ABC):
    def __init__(self, source_name: str):
        self.source_name = source_name
        self.logger = logger # Use shared logger

    @abstractmethod
    def fetch_news(self, target_coins_keywords: Dict[str, List[str]]) -> List[Article]:
        """
        Fetches news articles relevant to the target_coins.
        target_coins_keywords: A dictionary like {"BTC": ["Bitcoin", "BTC"], "ETH": ["Ethereum"]}
        Returns a list of Article objects.
        """
        pass

    def _filter_and_create_articles(
        self,
        raw_items: List[Dict],
        target_coins_keywords: Dict[str, List[str]],
        title_key: str,
        link_key: str,
        date_key: str,
        source_name_override: Optional[str] = None,
        content_key: Optional[str] = None,
        date_parser_func: Optional[callable] = None
    ) -> List[Article]:
        """Helper to process raw items into Article objects, filtering by keywords."""
        processed_articles: List[Article] = []
        for item in raw_items:
            title = item.get(title_key, "")
            link = item.get(link_key)
            raw_date = item.get(date_key)
            content_snippet = item.get(content_key, "") if content_key else title # Fallback

            if not title or not link or not raw_date:
                self.logger.debug(f"Skipping item due to missing critical fields: {item}")
                continue

            try:
                published_at = date_parser_func(raw_date) if date_parser_func else datetime.fromisoformat(str(raw_date).replace('Z', '+00:00'))
            except Exception as e:
                self.logger.warning(f"Could not parse date '{raw_date}' for article '{title}': {e}. Using current time.")
                published_at = datetime.now()


            item_content_lower = (title + " " + (content_snippet if content_snippet else "")).lower()
            related_coins_found: List[str] = []

            for coin_ticker, keywords in target_coins_keywords.items():
                if any(keyword.lower() in item_content_lower for keyword in keywords):
                    related_coins_found.append(coin_ticker)

            if related_coins_found:
                try:
                # Parse the raw date
                    published_at = date_parser_func(raw_date) if date_parser_func else datetime.fromisoformat(str(raw_date).replace('Z', '+00:00'))
                    
                    # Ensure the datetime is offset-aware (default to UTC if no timezone is provided)
                    if published_at.tzinfo is None:
                        published_at = published_at.replace(tzinfo=timezone.utc)
                except Exception as e:
                    self.logger.warning(f"Could not parse date '{raw_date}' for article '{title}': {e}. Using current time.")
                    published_at = datetime.now(timezone.utc)  # Use current time with UTC timezone
                    
                try:
                    article = Article(
                        title=title,
                        link=link,
                        published_at = date_parser_func(raw_date) if date_parser_func else datetime.fromisoformat(str(raw_date).replace('Z', '+00:00')),
                        source_name=str(source_name_override) or str(self.source_name),
                        content_snippet=content_snippet,
                        related_coins=list(set(related_coins_found)) # Ensure uniqueness
                    )
                    processed_articles.append(article)
                except Exception as e: # Catches Pydantic validation errors, etc.
                    self.logger.error(f"Error creating Article object for '{title}': {e}")
                    self.logger.error(f"  title: {title} (type: {type(title)})")
                    self.logger.error(f"  link: {link} (type: {type(link)})")
                    self.logger.error(f"  published_at: {published_at} (type: {type(published_at)})")
                    self.logger.error(f"  source_name: {source_name_override or self.source_name} (type: {type(source_name_override or self.source_name)})")
                    self.logger.error(f"  content_snippet: {content_snippet} (type: {type(content_snippet)})")
        return processed_articles