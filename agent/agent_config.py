# Crypto_Trading_Bot/agent/agent_config.py

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import yaml
import os
import logging

logger = logging.getLogger(__name__)

class StrategyConfig(BaseModel):
    name: str = Field(..., description="Unique name for this strategy instance")
    module: str = Field(..., description="Python module path to the strategy class (e.g., agent.strategies.rule_based.MovingAverageCrossoverStrategy)")
    class_name: str = Field(..., description="Name of the strategy class")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Specific parameters for the strategy")

class ExchangeAdapterConfig(BaseModel):
    type: str = Field("MockExchangeAdapter", description="Type of exchange adapter (e.g., MockExchangeAdapter, CCXTExchangeAdapter)")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Specific parameters for the exchange adapter")
    # Example for Mock: {"initial_prices": {"BTC/USDT": 60000}, "commission_rate": 0.001}
    # Example for Real: {"exchange_id": "binance", "api_key_env": "BINANCE_API_KEY", "secret_key_env": "BINANCE_SECRET_KEY", "extra_params": {}}


class AgentSettings(BaseModel): # Add exchange_adapter_config
    portfolio_base_currency: str = Field("USDT", description="The primary currency for evaluating portfolio value and for trading.")
    initial_capital: Dict[str, float] = Field(default_factory=lambda: {"USDT": 10000.0}, description="Initial capital distribution, used if adapter doesn't fetch real balances.")
    trading_interval_seconds: int = Field(300, description="How often the agent attempts to generate and execute signals.")
    max_concurrent_strategies: int = Field(5, description="Maximum number of strategies to run concurrently.")
    
    exchange_adapter_config: ExchangeAdapterConfig = Field(default_factory=ExchangeAdapterConfig) # New field

    market_data_source_config: Optional[Dict[str, Any]] = Field(None, description="Configuration for the market data source client")
    ollama_client_config: Optional[Dict[str, Any]] = Field(None, description="Configuration for the Ollama client")
    sentiment_analyzer_config: Optional[Dict[str, Any]] = Field(None, description="Configuration for the Sentiment Analyzer")
    news_sources_config: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Configuration for news sources")


class FullAgentConfig(BaseModel):
    agent_settings: AgentSettings = Field(default_factory=AgentSettings)
    strategies: List[StrategyConfig] = Field(default_factory=list)


DEFAULT_CONFIG_FILE_PATH = "agent_config.yaml"

def load_agent_config(config_file_path: str = DEFAULT_CONFIG_FILE_PATH) -> FullAgentConfig:
    """
    Loads the agent configuration from a YAML file.
    If the file doesn't exist, returns a default configuration.
    """
    if os.path.exists(config_file_path):
        try:
            with open(config_file_path, 'r') as f:
                config_data = yaml.safe_load(f)
            logger.info(f"Loaded agent configuration from {config_file_path}")
            return FullAgentConfig(**config_data)
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML configuration file {config_file_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading configuration from {config_file_path}: {e}")
            raise
    else:
        logger.warning(f"Configuration file {config_file_path} not found. Using default configuration.")
        # Create a default configuration for demonstration
        default_config = FullAgentConfig(
            agent_settings=AgentSettings(
                portfolio_base_currency="USDT",
                initial_capital={"USDT": 10000.0},
                trading_interval_seconds=60,
                market_data_source_config={"type": "BinanceSource", "api_key": "YOUR_API_KEY", "secret_key": "YOUR_SECRET"}, # Example
                ollama_client_config={"host": "http://localhost:11434"}, # Example
                sentiment_analyzer_config={"model": "llama3-instruct", "mode": "ollama_direct"}, # Example
                news_sources_config=[ # Example
                    {"type": "RSSSource", "name": "CoinDesk RSS", "url": "https://www.coindesk.com/arc/outboundfeeds/rss/"},
                    {"type": "NewsApiSource", "api_key": "YOUR_NEWSAPI_KEY", "query": "cryptocurrency OR bitcoin OR ethereum"}
                ]
            ),
            strategies=[
                StrategyConfig(
                    name="MACrossover_BTC",
                    module="agent.strategies.rule_based.moving_average_crossover",
                    class_name="MovingAverageCrossoverStrategy",
                    parameters={
                        "symbol": "BTC/USDT",
                        "short_window": 10,
                        "long_window": 30,
                        "timeframe": "15m",
                        "trade_quantity_percentage": 0.25 # 25% of available USDT for a BTC buy
                    }
                ),
                StrategyConfig(
                    name="SentimentTrader_BTC_ETH",
                    module="agent.strategies.ai_based.sentiment_llm_strategy",
                    class_name="SentimentLLMStrategy",
                    parameters={
                        "target_symbols": ["BTC", "ETH"],
                        "news_fetch_limit": 5,
                        "sentiment_threshold_buy": 0.2,  # Adjusted for potential Ollama outputs
                        "sentiment_threshold_sell": -0.1, # Adjusted
                        "trade_quantity_percentage": 0.1, # 10% of USDT for a buy
                        "quote_currency": "USDT",
                        "news_max_age_hours": 12
                    }
                )
            ]
        )
        # Optionally, save the default config if it doesn't exist
        # save_agent_config(default_config, config_file_path)
        return default_config

def save_agent_config(config: FullAgentConfig, config_file_path: str = DEFAULT_CONFIG_FILE_PATH) -> None:
    """
    Saves the agent configuration to a YAML file.
    """
    try:
        with open(config_file_path, 'w') as f:
            yaml.dump(config.model_dump(mode='python'), f, indent=2, sort_keys=False)
        logger.info(f"Agent configuration saved to {config_file_path}")
    except Exception as e:
        logger.error(f"Error saving configuration to {config_file_path}: {e}")
