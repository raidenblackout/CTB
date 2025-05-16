# Crypto_Trading_Bot/agent/__init__.py
"""
The Trading Agent module for the Crypto Trading Bot.

This module contains the core logic for defining trading strategies,
managing portfolio, and executing trades.
"""

from .agent_context import AgentContext
from .trading_agent import TradingAgent
from .trading_models import TradingSignal, OrderAction, OrderType, AgentPortfolio
from .agent_config import load_agent_config, FullAgentConfig, StrategyConfig

__all__ = [
    "AgentContext",
    "TradingAgent",
    "TradingSignal",
    "OrderAction",
    "OrderType",
    "AgentPortfolio",
    "load_agent_config",
    "FullAgentConfig",
    "StrategyConfig",
    # Expose strategy base and concrete strategy classes if needed at this level
    "BaseStrategy" 
]

# To make BaseStrategy easily accessible (it's in strategies sub-package)
try:
    from .strategies.base_strategy import BaseStrategy
except ImportError:
    # Handle case where it might not be immediately resolvable or for linters
    pass 