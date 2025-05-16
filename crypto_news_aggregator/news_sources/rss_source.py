# crypto_news_aggregator/news_sources/rss_source.py
import feedparser
from typing import List, Dict, Any, Optional
from datetime import datetime
from .base_source import BaseNewsSource
from ..utils.data_models import Article
class RSSSource(BaseNewsSource):
    def __init__(self, source_name: str, feed_url: str):
        super().__init__(source_name)
        self.feed_url = feed_url

    def _parse_rss_date(self, entry: Any) -> datetime:
        """Attempts to parse date from various RSS entry formats."""
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            return datetime(*entry.published_parsed[:6])
        if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            return datetime(*entry.updated_parsed[:6])
        # Add more fallbacks if necessary, e.g., parsing from entry.published string
        self.logger.warning(f"No standard parsed date for entry in {self.source_name}. Using current time.")
        return datetime.now()


    def fetch_news(self, target_coins_keywords: Dict[str, List[str]], limit: Optional[int] = 10) -> List[Article]:
        self.logger.info(f"Fetching news from RSS feed: {self.source_name} ({self.feed_url})")
        articles: List[Article] = []
        try:
            feed = feedparser.parse(self.feed_url, request_headers={'User-Agent': 'MyCryptoNewsAggregator/1.0'})
            if feed.bozo: # Indicates an error during parsing
                self.logger.warning(f"Error parsing RSS feed {self.feed_url}: {feed.bozo_exception}")
                # return articles # Optionally return empty or try to process what was parsed

            raw_items = []
            for entry in feed.entries:
                raw_items.append({
                    "title": entry.title,
                    "link": entry.link,
                    "published_date_obj": entry, # Pass the whole entry for flexible date parsing
                    "summary": entry.get("summary", entry.title) # Use title if summary is missing
                })

            articles = self._filter_and_create_articles(
                raw_items=raw_items,
                target_coins_keywords=target_coins_keywords,
                title_key="title",
                link_key="link",
                date_key="published_date_obj", # Key for the object to pass to date_parser_func
                content_key="summary",
                date_parser_func=self._parse_rss_date,
                source_name_override=self.source_name # Use the specific RSS source name
            )

        except Exception as e:
            self.logger.error(f"An unexpected error occurred fetching RSS feed {self.feed_url}: {e}")
        self.logger.info(f"Found {len(articles)} relevant articles from {self.source_name}")
        return articles