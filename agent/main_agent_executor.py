# Crypto_Trading_Bot/agent/main_agent_executor.py
# ... (other imports) ...
import logging
import os
from typing import Optional
from agent.agent_config import load_agent_config, FullAgentConfig, ExchangeAdapterConfig
from agent.agent_context import AgentContext
from agent.exchange_adapters.mock_exchange_adapter_with_real_prices import MockExchangeAdapterWithRealtimeData
from agent.trading_agent import TradingAgent
from agent.exchange_adapters import BaseExchangeAdapter, MockExchangeAdapter
from agent.trading_models import AgentPortfolio
from api_client.OllamaClient import OllamaClient
from crypto_market_exchange_manager.data_sources.binance_source import BinanceSource
from crypto_news_aggregator.news_sources.cryptopanic_source import CryptoPanicSource
from crypto_news_aggregator.news_sources.newsapi_source import NewsApiSource
from crypto_news_aggregator.news_sources.rss_source import RSSSource
from sentiment_analysis.sentiment_analyzer import SentimentAnalyzer # Import specific adapters
# from agent.exchange_adapters import CCXTExchangeAdapter # When you implement it

# ... (setup_agent_logging) ...
logger = logging.getLogger(__name__)

async def main():
    # 1. Load Agent Configuration
    path = os.path.dirname(os.path.abspath(__file__))
    config_file_path = os.path.join(path, 'agent_config.yaml')
    agent_full_config: FullAgentConfig = load_agent_config(config_file_path=config_file_path)
    print(f"Full Agent Config {agent_full_config}")  # Debugging line to check the loaded config
    # ... (Initialize Ollama, SentimentAnalyzer, News Sources, Market Data Source as before) ...
    
    ollama_cli = OllamaClient()
    sentiment_anlyzr = SentimentAnalyzer(api_client=ollama_cli) 
    news_sources = [RSSSource("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"), 
                    RSSSource("CoinTelegraph", "https://cointelegraph.com/rss"),
                    RSSSource("BitcoinMagazine", "https://bitcoinmagazine.com/feed"),
                    RSSSource("Decrypt", " https://decrypt.co/feed"),
                    CryptoPanicSource(),
                    NewsApiSource()
                    ] 
    market_src = BinanceSource()

    # 2.5 Initialize Exchange Adapter
    exchange_adapter_instance: Optional[BaseExchangeAdapter] = None
    adapter_conf: ExchangeAdapterConfig = agent_full_config.agent_settings.exchange_adapter_config
    
    # The initial capital for the mock adapter can come from agent_settings,
    # or be overridden in adapter_conf.parameters if needed.
    # For real adapters, initial_capital from config is usually ignored as balances are fetched.
    mock_initial_portfolio = AgentPortfolio(cash_balance=agent_full_config.agent_settings.initial_capital.copy())

    if adapter_conf.type == "MockExchangeAdapter":
        try:
            print("I am here")
            # Pass agent's initial_capital to MockExchangeAdapter config if not specified in its own params
            mock_params = adapter_conf.parameters.copy()
            if "initial_capital" not in mock_params:
                 mock_params["initial_capital"] = agent_full_config.agent_settings.initial_capital.copy()

            if "market_data_source" not in mock_params:
                mock_params["market_data_source"] = market_src

            exchange_adapter_instance = MockExchangeAdapterWithRealtimeData(
                config=mock_params, # Pass its specific parameters
                initial_portfolio=mock_initial_portfolio # Can be None if mock_params["initial_capital"] is used
            )
            logger.info("MockExchangeAdapter initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize MockExchangeAdapter: {e}", exc_info=True)
            
    else:
        logger.error(f"Unknown or unsupported ExchangeAdapter type: {adapter_conf.type}")

    # 3. Create Agent Context (now includes exchange_adapter_instance)
    agent_context = AgentContext(
        sentiment_analyzer=sentiment_anlyzr,
        news_aggregator_sources=news_sources,
        market_data_source=market_src,
        exchange_adapter=exchange_adapter_instance, # Inject the adapter
        agent_config=agent_full_config.agent_settings.model_dump()
    )

    logger.info(f"Agent_full_config: {agent_full_config}")
    logger.info(f"Agent_context: {agent_context}")
    # 4. Initialize Trading Agent
    trading_agent = TradingAgent(config=agent_full_config, context=agent_context)

    # 5. Start the Agent (initialization of components is now inside agent.start or a separate call)
    try:
        await trading_agent.start() # This will call initialize_components internally
    except Exception as e:
        logger.error(f"Error starting the trading agent: {e}", exc_info=True)
    finally:
        await trading_agent.stop()

if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
