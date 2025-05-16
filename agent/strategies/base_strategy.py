# Crypto_Trading_Bot/agent/strategies/base_strategy.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging

from agent.agent_context import AgentContext # Adjust import if AgentContext is moved
from agent.trading_models import TradingSignal, AgentPortfolio

logger = logging.getLogger(__name__)

class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies.
    """
    def __init__(self, strategy_name: str, context: AgentContext, config: Dict[str, Any]):
        """
        Initializes the base strategy.

        Args:
            strategy_name: A unique name for this strategy instance.
            context: The AgentContext providing access to shared resources like data sources.
            config: Strategy-specific configuration parameters.
        """
        self.strategy_name = strategy_name
        self.context = context
        self.config = config
        self.is_initialized = False
        logger.info(f"Strategy '{self.strategy_name}' created with config: {self.config}")

    async def initialize(self) -> None:
        """
        Perform any asynchronous initialization tasks for the strategy.
        This method can be overridden by subclasses if needed.
        Examples: fetching historical data, pre-calculating indicators.
        """
        logger.info(f"Initializing strategy '{self.strategy_name}'...")
        # Subclasses can implement specific initialization logic here
        self.is_initialized = True
        logger.info(f"Strategy '{self.strategy_name}' initialized successfully.")

    @abstractmethod
    async def generate_signals(self, portfolio: AgentPortfolio) -> List[TradingSignal]:
        """
        The core logic of the strategy. Generates trading signals based on market data,
        news, sentiment, portfolio state, etc.

        Args:
            portfolio: The current state of the agent's portfolio.
            current_market_data: Optional dictionary containing current market data,
                                 e.g., {'BTC/USDT': {'ticker': Ticker, 'ohlcv': [OHLCV]}}

        Returns:
            A list of TradingSignal objects.
        """
        pass

    async def on_data(self, data_event: Any) -> None:
        """
        Optional: Called when new market data or other relevant event arrives.
        Not all strategies might use this event-driven approach.
        Some might rely on periodic calls to generate_signals.
        """
        logger.debug(f"Strategy '{self.strategy_name}' received data event: {data_event}")
        # Default implementation does nothing. Subclasses can override.
        pass
    
    async def on_order_update(self, executed_order: Any) -> None:
        """
        Optional: Called when an order related to this strategy is executed or updated.
        
        Args:
            executed_order: Information about the executed order (e.g., an ExecutedOrder model).
        """
        logger.info(f"Strategy '{self.strategy_name}' received order update: {executed_order}")
        # Default implementation does nothing. Subclasses can override.
        pass

    def get_status(self) -> Dict[str, Any]:
        """
        Returns the current status or internal state of the strategy.
        Useful for monitoring and debugging.
        """
        return {
            "strategy_name": self.strategy_name,
            "config": self.config,
            "is_initialized": self.is_initialized,
            # Subclasses can add more status information
        }

    async def shutdown(self) -> None:
        """
        Perform any cleanup tasks before the strategy is stopped.
        """
        logger.info(f"Shutting down strategy '{self.strategy_name}'...")
        # Subclasses can implement specific shutdown logic here
        logger.info(f"Strategy '{self.strategy_name}' shutdown complete.")