# Crypto_Trading_Bot/agent/strategies/ai_based/sentiment_llm_strategy.py

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone

from agent.strategies.base_strategy import BaseStrategy
from agent.agent_context import AgentContext
from agent.trading_models import TradingSignal, OrderAction, AgentPortfolio
# Assuming Article model is available
from crypto_news_aggregator.utils.data_models import Article

logger = logging.getLogger(__name__)

class SentimentLLMStrategy(BaseStrategy):
    """
    A strategy that uses sentiment analysis of recent crypto news (potentially using an LLM)
    to generate trading signals.
    """
    def __init__(self, strategy_name: str, context: AgentContext, config: Dict[str, Any]):
        super().__init__(strategy_name, context, config)
        
        self.target_symbols: List[str] = self.config.get("target_symbols", ["BTC", "ETH"]) # Symbols like "BTC", not "BTC/USDT"
        self.news_fetch_limit: int = self.config.get("news_fetch_limit", 10) # Articles per source
        self.sentiment_threshold_buy: float = self.config.get("sentiment_threshold_buy", 0.6) # e.g., score > 0.6
        self.sentiment_threshold_sell: float = self.config.get("sentiment_threshold_sell", -0.4) # e.g., score < -0.4
        self.trade_quantity_percentage: float = self.config.get("trade_quantity_percentage", 0.05) # 5% of available quote
        self.news_max_age_hours: int = self.config.get("news_max_age_hours", 24) # Consider news up to 24 hours old
        self.quote_currency: str = self.config.get("quote_currency", "USDT") # Currency to use for buying/selling

        self.active_positions: Dict[str, bool] = {symbol: False for symbol in self.target_symbols}

    async def initialize(self) -> None:
        await super().initialize()
        logger.info(f"[{self.strategy_name}] Initializing SentimentLLMStrategy for symbols: {self.target_symbols}.")
        if not self.context.sentiment_analyzer:
            logger.warning(f"[{self.strategy_name}] SentimentAnalyzer not available in context. Strategy may not function correctly.")
        if not self.context.news_aggregator_sources or len(self.context.news_aggregator_sources) == 0:
            logger.warning(f"[{self.strategy_name}] No news aggregator sources available in context. Strategy may not function correctly.")

    async def _get_relevant_recent_news(self) -> Dict[str, List[Article]]:
        """
        Fetches recent news articles relevant to target symbols.
        """
        relevant_news: Dict[str, List[Article]] = {symbol: [] for symbol in self.target_symbols}
        
        # Use context's aggregated news fetching if available and suitable
        # For this strategy, we might want more control or specific filtering
        all_articles = await self.context.get_recent_articles(
            symbols=self.target_symbols, # Pass general symbols like "BTC"
            limit_per_source=self.news_fetch_limit
        )
        
        logger.info(f"[{self.strategy_name}] Fetched {len(all_articles)} articles from news sources.")
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.news_max_age_hours)

        for article in all_articles:
            if article.published_at < cutoff_time:
                continue # Skip old news

            # Check if article.symbols (from CryptoPanic, etc.) match our target_symbols
            # Or if article title/content mentions target symbols (more complex NLP needed for this)
            for target_sym in self.target_symbols:
                # Assuming article.symbols contains coin tickers like "BTC", "ETH"
                if target_sym.upper() in [s.upper() for s in article.related_coins if isinstance(s, str)]:
                    relevant_news[target_sym].append(article)
                    break # Avoid adding same article for multiple symbols if it mentions many
                # Basic title check as a fallback
                elif target_sym.upper() in article.title.upper():
                    relevant_news[target_sym].append(article)
                    break
        
        for sym, articles in relevant_news.items():
            logger.info(f"[{self.strategy_name}] Found {len(articles)} relevant recent articles for {sym}.")
        return relevant_news

    async def _analyze_sentiment_for_symbol(self, symbol: str, articles: List[Article]) -> float:
        """
        Analyzes sentiment for a given symbol based on a list of articles.
        Returns an aggregated sentiment score (e.g., average).
        """
        if not self.context.sentiment_analyzer or not articles:
            return 0.0

        total_score = 0.0
        valid_analyses = 0
        
        for article in articles:
            text_to_analyze = article.title
            if article.content_snippet: # Prioritize content if available and not too long
                 # Simple heuristic: use first 500 chars of content if available
                text_to_analyze += ". " + article.content_snippet[:500] 

            try:
                # Assuming analyze_sentiment returns a dict like {'label': 'POSITIVE', 'score': 0.8}
                # The score should ideally be normalized, e.g., -1 (very negative) to +1 (very positive)
                sentiment_result = self.context.sentiment_analyzer.analyze_sentiment(text_to_analyze, target_coin=symbol)
                convert = {
                    "Positive": 1.0,
                    "Negative": -1.0,
                    "Neutral": 0.0
                }

                if convert.get(sentiment_result) is not None:
                    total_score += convert[sentiment_result]
                    valid_analyses += 1
                    logger.debug(f"[{self.strategy_name}] Sentiment for '{article.title}' ({symbol}): {convert[sentiment_result]:.2f}")
                else:
                    logger.warning(f"[{self.strategy_name}] Invalid sentiment result for article: {article.title}")
            except Exception as e:
                logger.error(f"[{self.strategy_name}] Error analyzing sentiment for article '{article.title}': {e}")
        
        if valid_analyses == 0:
            return 0.0
        
        average_score = total_score / valid_analyses
        logger.info(f"[{self.strategy_name}] Average sentiment score for {symbol} from {valid_analyses} articles: {average_score:.3f}")
        return average_score

    async def generate_signals(self, portfolio: AgentPortfolio) -> List[TradingSignal]:
        signals: List[TradingSignal] = []

        if not self.context.sentiment_analyzer:
            logger.warning(f"[{self.strategy_name}] Sentiment analyzer not configured. Cannot generate signals.")
            return signals
        
        relevant_news_by_symbol = await self._get_relevant_recent_news()

        for symbol_base in self.target_symbols: # e.g., "BTC"
            trading_pair = f"{symbol_base}/{self.quote_currency}" # e.g., "BTC/USDT"
            articles_for_symbol = relevant_news_by_symbol.get(symbol_base, [])
            
            if not articles_for_symbol:
                logger.info(f"[{self.strategy_name}] No recent relevant news found for {symbol_base}. Generating HOLD signal for {trading_pair}.")
                signals.append(TradingSignal(
                    symbol=trading_pair,
                    action=OrderAction.HOLD,
                    strategy_name=self.strategy_name,
                    metadata={"reason": f"No recent news for {symbol_base}"}
                ))
                continue

            average_sentiment_score = await self._analyze_sentiment_for_symbol(symbol_base, articles_for_symbol)

            # Get current price (important for context, though this strategy is sentiment-first)
            current_price = None
            if self.context.market_data_source:
                try:
                    logger.info(f"[{self.strategy_name}] Fetching current price for {trading_pair}.")
                    ticker = self.context.market_data_source.fetch_ticker(trading_pair)
                    current_price = ticker.last if ticker else None
                except Exception as e:
                    logger.warning(f"[{self.strategy_name}] Could not fetch ticker for {trading_pair}: {e}")

            logger.info(f"[{self.strategy_name}] {trading_pair} - Avg Sentiment: {average_sentiment_score:.3f}, Current Price: {current_price}")

            # Determine action based on sentiment score
            action = OrderAction.HOLD
            confidence = 0.5 # Default confidence for HOLD

            if average_sentiment_score > self.sentiment_threshold_buy:
                if not self.active_positions.get(symbol_base, False):
                     if portfolio.cash_balance.get(self.quote_currency, 0) > 0: # Check for quote currency
                        action = OrderAction.BUY
                        confidence = min(0.5 + (average_sentiment_score - self.sentiment_threshold_buy) * 0.5, 0.95) # Scale confidence
                        logger.info(f"[{self.strategy_name}] BUY signal for {trading_pair} due to positive sentiment ({average_sentiment_score:.3f}).")
                     else:
                        logger.warning(f"[{self.strategy_name}] Positive sentiment for {trading_pair}, but no {self.quote_currency} balance to buy.")
                else:
                    logger.info(f"[{self.strategy_name}] Positive sentiment for {trading_pair}, but already in an active position.")


            elif average_sentiment_score < self.sentiment_threshold_sell:
                if self.active_positions.get(symbol_base, False): # Only sell if holding the asset
                    if portfolio.asset_holdings.get(symbol_base, 0) > 0: # Check for base currency
                        action = OrderAction.SELL
                        confidence = min(0.5 + abs(average_sentiment_score - self.sentiment_threshold_sell) * 0.5, 0.95)
                        logger.info(f"[{self.strategy_name}] SELL signal for {trading_pair} due to negative sentiment ({average_sentiment_score:.3f}).")
                    else:
                        logger.warning(f"[{self.strategy_name}] Negative sentiment for {trading_pair}, but no {symbol_base} to sell. Position state inconsistent.")
                        self.active_positions[symbol_base] = False # Correct state
                else:
                    logger.info(f"[{self.strategy_name}] Negative sentiment for {trading_pair}, but not in an active position.")
            
            signal_metadata = {
                "reason": f"Sentiment score: {average_sentiment_score:.3f}",
                "num_articles_analyzed": len(articles_for_symbol),
                "sentiment_threshold_buy": self.sentiment_threshold_buy,
                "sentiment_threshold_sell": self.sentiment_threshold_sell,
                "current_price": current_price
            }

            if action != OrderAction.HOLD:
                signals.append(TradingSignal(
                    symbol=trading_pair,
                    action=action,
                    confidence=confidence,
                    quantity_percentage=self.trade_quantity_percentage if action == OrderAction.BUY else 1.0, # Buy portion, sell all
                    price=current_price, # Could be market order
                    strategy_name=self.strategy_name,
                    metadata=signal_metadata
                ))
                # Update assumed position optimistically. Real updates via on_order_update.
                if action == OrderAction.BUY: self.active_positions[symbol_base] = True
                elif action == OrderAction.SELL: self.active_positions[symbol_base] = False
            else:
                 signals.append(TradingSignal(
                    symbol=trading_pair,
                    action=OrderAction.HOLD,
                    confidence=confidence,
                    strategy_name=self.strategy_name,
                    metadata=signal_metadata
                ))


        return signals

    async def on_order_update(self, executed_order: Any) -> None:
        await super().on_order_update(executed_order)
        # Assuming executed_order is an ExecutedOrder model
        symbol_base = executed_order.symbol.split('/')[0]
        if symbol_base in self.target_symbols and executed_order.status == "FILLED":
            if executed_order.action == OrderAction.BUY:
                self.active_positions[symbol_base] = True
                logger.info(f"[{self.strategy_name}] Position for {symbol_base} became active after BUY order {executed_order.order_id}.")
            elif executed_order.action == OrderAction.SELL:
                self.active_positions[symbol_base] = False
                logger.info(f"[{self.strategy_name}] Position for {symbol_base} became inactive after SELL order {executed_order.order_id}.")
    
    def get_status(self) -> Dict[str, Any]:
        status = super().get_status()
        status.update({
            "target_symbols": self.target_symbols,
            "sentiment_threshold_buy": self.sentiment_threshold_buy,
            "sentiment_threshold_sell": self.sentiment_threshold_sell,
            "active_positions": self.active_positions,
        })
        return status

# Create __init__.py for ai_based folder
# Crypto_Trading_Bot/agent/strategies/ai_based/__init__.py
"""
AI-based trading strategies.
"""
from .sentiment_llm_strategy import SentimentLLMStrategy

__all__ = [
    "SentimentLLMStrategy"
]