# crypto_news_aggregator/utils/helpers.py
from datetime import timezone
import logging
from typing import List, Set
from .data_models import Article

def setup_logging(level=logging.INFO):
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(module)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger(__name__)

logger = setup_logging()

def deduplicate_articles(articles: List[Article]) -> List[Article]:
    """Deduplicates a list of Article objects based on title and link."""
    seen_articles: Set[Article] = set()
    unique_articles: List[Article] = []
    for article in articles:
        if article not in seen_articles:
            unique_articles.append(article)
            seen_articles.add(article)
    logger.info(f"Deduplicated articles: {len(articles)} -> {len(unique_articles)}")
    return unique_articles

def sort_articles_by_date(articles: List[Article], reverse: bool = True) -> List[Article]:
    """Sorts articles by published_at date."""
    for article in articles:
        if article.published_at.tzinfo is None:
            article.published_at = article.published_at.replace(tzinfo=timezone.utc)
    return sorted(articles, key=lambda x: x.published_at, reverse=reverse)