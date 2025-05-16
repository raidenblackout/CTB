# Crypto_Trading_Bot/agent/exchange_adapters/__init__.py

from .base_exchange_adapter import BaseExchangeAdapter, OrderRequest, ExchangeAdapterError, OrderPlacementError, InsufficientFundsError, OrderNotFoundError
from .mock_exchange_adapter import MockExchangeAdapter

# Placeholder for real adapters
# from .ccxt_exchange_adapter import CCXTExchangeAdapter

__all__ = [
    "BaseExchangeAdapter",
    "MockExchangeAdapter",
    # "CCXTExchangeAdapter",
    "OrderRequest",
    "ExchangeAdapterError",
    "OrderPlacementError",
    "InsufficientFundsError",
    "OrderNotFoundError"
]