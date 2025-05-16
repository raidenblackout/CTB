# crypto_news_aggregator/main.py
from typing import List
from . import config
from .utils.helpers import setup_logging, deduplicate_articles, sort_articles_by_date
from .utils.data_models import Article
from .news_sources.rss_source import RSSSource
from .news_sources.newsapi_source import NewsApiSource
from .news_sources.cryptopanic_source import CryptoPanicSource
# Import your Ollama interaction module here when ready
# from llm_processor import OllamaProcessor

logger = setup_logging()

def get_top_recent_articles(num_articles: int = 10):
    """
    Main function to fetch and process the latest crypto news articles.
    :param num_articles: Number of articles to fetch and process.
    """
    logger.info("Starting Crypto News Aggregator...")
    all_raw_articles: List[Article] = []

    # Initialize news sources
    rss_sources = [RSSSource(name, url) for name, url in config.RSS_FEEDS_CONFIG.items()]
    newsapi_source = NewsApiSource()
    cryptopanic_source = CryptoPanicSource()

    active_sources = [*rss_sources] # Start with RSS
    if newsapi_source.api_key:
        active_sources.append(newsapi_source)
    if cryptopanic_source.api_key:
        active_sources.append(cryptopanic_source)

    if not active_sources:
        logger.warning("No active news sources configured or API keys missing. Exiting.")
        return

    # Fetch news from all active sources
    for source in active_sources:
        try:
            logger.info(f"Fetching from source: {source.source_name}")
            # Pass the full TARGET_COINS dict to each source; they will filter internally
            articles = source.fetch_news(config.TARGET_COINS)
            all_raw_articles.extend(articles)
            logger.info(f"Fetched {len(articles)} articles from {source.source_name}")
        except Exception as e:
            logger.error(f"Failed to fetch news from {source.source_name}: {e}", exc_info=True)


    logger.info(f"Total articles collected before deduplication: {len(all_raw_articles)}")

    # Deduplicate and sort
    unique_articles = deduplicate_articles(all_raw_articles)
    sorted_articles = sort_articles_by_date(unique_articles)

    logger.info(f"Total unique articles after processing: {len(sorted_articles)}")

    # --- Display or Process Articles ---
    if not sorted_articles:
        logger.info("No articles found matching criteria.")
        return

    logger.info(f"\n--- Top {num_articles} Recent Unique Articles ---")
    for i, article in enumerate(sorted_articles[:num_articles]):
        logger.info(
            f"{i+1}. [{', '.join(article.related_coins)}] {article.title} ({article.source_name}) - {article.published_at.strftime('%Y-%m-%d %H:%M')}"
        )
        logger.debug(f"   Link: {article.link}")
        logger.debug(f"   Snippet: {article.content_snippet[:100] if article.content_snippet else 'N/A'}...")


    # --- LLM Processing (Placeholder) ---
    # Here you would integrate your Ollama LLM processing
    # ollama_processor = OllamaProcessor(model_name="mistral:latest", host="http://your_ollama_host:port")
    # for article in sorted_articles:
    #     try:
    #         sentiment_result = ollama_processor.get_sentiment(article.title + (article.content_snippet or ""))
    #         logger.info(f"Sentiment for '{article.title[:50]}...': {sentiment_result}")
    #         # Store sentiment, generate signals, etc.
    #     except Exception as e:
    #         logger.error(f"Error processing article '{article.title[:50]}...' with LLM: {e}")

    logger.info("News aggregation finished.")
    return sorted_articles[:num_articles]  # Return the top articles for further processing if needed
