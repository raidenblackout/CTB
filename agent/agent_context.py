# Crypto_Trading_Bot/agent/agent_context.py

from datetime import datetime
from typing import Optional, List, Dict, Any, Type
import logging
from agent.trading_models import AgentPortfolio
from crypto_market_exchange_manager.market_data_models.models import BaseModel

from api_client.OllamaClient import OllamaClient
from crypto_news_aggregator.utils import helpers
from sentiment_analysis.sentiment_analyzer import SentimentAnalyzer

from crypto_news_aggregator.news_sources.base_source import BaseNewsSource
from crypto_news_aggregator.utils.data_models import Article # Assuming Article is defined here

from crypto_market_exchange_manager.data_sources.base_market_source import BaseMarketDataSource
from crypto_market_exchange_manager.market_data_models.models import OHLCV, Ticker, OrderBook, Trade as MarketTradeData



logger = logging.getLogger(__name__)

from agent.exchange_adapters.base_exchange_adapter import BaseExchangeAdapter

class AgentContext:
    def __init__(self,
                 sentiment_analyzer: Optional[SentimentAnalyzer] = None,
                 news_aggregator_sources: Optional[List[BaseNewsSource]] = None,
                 market_data_source: Optional[BaseMarketDataSource] = None,
                 exchange_adapter: Optional[BaseExchangeAdapter] = None, # New field
                 agent_config: Optional[Dict[str, Any]] = None):
        # ... (assignments for other services) ...
        self.exchange_adapter = exchange_adapter # Store the injected adapter
        self.config = agent_config if agent_config else {}
        self.sentiment_analyzer = sentiment_analyzer
        self.news_aggregator_sources = news_aggregator_sources if news_aggregator_sources else []
        self.market_data_source = market_data_source
        
        logger.info("AgentContext initialized.")
        if self.sentiment_analyzer:
            logger.info("SentimentAnalyzer available in context.")
        if self.news_aggregator_sources:
            logger.info(f"{len(self.news_aggregator_sources)} News Aggregator source(s) available in context.")
        if self.market_data_source: # <<< ADDED LOGGING FOR THIS
            logger.info("MarketDataSource available in context.")
        else:
            logger.warning("MarketDataSource not available in context. Some functionalities might be limited.")
        if self.exchange_adapter:
            logger.info(f"ExchangeAdapter ({self.exchange_adapter.__class__.__name__}) available in context.")
        else:
            logger.warning("No ExchangeAdapter provided to AgentContext. Trading will not be possible.")


    async def get_recent_articles(self, symbols: Optional[List[str]] = None, limit_per_source: int = 10) -> List[Article]:
        """
        Fetches and aggregates recent articles from all configured news sources.
        """
        all_articles: List[Article] = []
        if not self.news_aggregator_sources:
            logger.warning("No news aggregator sources configured in AgentContext.")
            return []

        for source in self.news_aggregator_sources:
            try:
                target_coins_keywords = {coin: [coin] for coin in symbols} if symbols else {}
                # Fetch news from the source
                articles = source.fetch_news(target_coins_keywords=target_coins_keywords, limit=limit_per_source)
                all_articles.extend(articles)
                logger.debug(f"Fetched {len(articles)} articles from {source.__class__.__name__}")
            except Exception as e:
                logger.error(f"Error fetching news from {source.__class__.__name__}: {e}")
        print(f"Fetched {len(all_articles)} articles from all sources.")
        unique_articles_dict = {article.link: article for article in all_articles if hasattr(article, 'link')}
        print(f"Found {len(unique_articles_dict)} unique articles.")
        sorted_articles = helpers.sort_articles_by_date(list(unique_articles_dict.values()))
        # sorted_articles = {article.link: article for article in sorted_articles if hasattr(article, 'link')}
        # sorted_articles = sorted(list(unique_articles_dict.values()), key=lambda x: x.published_at if hasattr(x, 'published_at') else datetime.min, reverse=True)
        print(f"Sorted {len(sorted_articles)} articles by date.")
        return sorted_articles