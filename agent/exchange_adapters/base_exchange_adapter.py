# Crypto_Trading_Bot/agent/exchange_adapters/base_exchange_adapter.py

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from agent.trading_models import OrderAction, OrderType, ExecutedOrder, AgentPortfolio
# Re-import or ensure these are accessible
from pydantic import BaseModel, Field
import uuid # for request_id

class OrderRequest(BaseModel): # Defined in trading_models.py; ensure it's imported
    """
    Represents a request to place an order.
    This will be passed to the exchange adapter.
    """
    request_id: str = Field(default_factory=lambda: f"req_{datetime.utcnow().timestamp()}_{uuid.uuid4().hex[:8]}", description="Unique request ID for tracking")
    symbol: str
    action: OrderAction # BUY or SELL
    order_type: OrderType # MARKET, LIMIT
    quantity: float # Amount of base currency to buy/sell
    price: Optional[float] = None # Required for LIMIT orders
    client_order_id: Optional[str] = None # Custom order ID for the exchange
    strategy_name: Optional[str] = None # Strategy originating the order
    # Add other relevant fields like time_in_force, stop_price, etc. if needed

    class Config:
        use_enum_values = True


class BaseExchangeAdapter(ABC):
    """
    Abstract Base Class for an exchange adapter.
    Defines the interface for interacting with an exchange (real or mock).
    """

    def __init__(self, config: Dict[str, Any], initial_portfolio: Optional[AgentPortfolio] = None):
        self.config = config
        self.portfolio = initial_portfolio if initial_portfolio else AgentPortfolio()
        # For real exchanges, portfolio might be fetched or managed differently

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the adapter (e.g., connect to exchange, fetch initial state)."""
        pass

    @abstractmethod
    async def create_order(self, order_request: OrderRequest) -> ExecutedOrder:
        """
        Places an order on the exchange.

        Args:
            order_request: An OrderRequest object detailing the order.

        Returns:
            An ExecutedOrder object representing the outcome.
            Should raise an exception (e.g., OrderPlacementError, InsufficientFundsError) on failure.
        """
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> bool:
        """
        Cancels an open order.

        Args:
            order_id: The ID of the order to cancel.
            symbol: The trading symbol (required by some exchanges).

        Returns:
            True if cancellation was successful/accepted, False otherwise.
        """
        pass

    @abstractmethod
    async def get_order_status(self, order_id: str, symbol: Optional[str] = None) -> Optional[ExecutedOrder]:
        """
        Fetches the status of a specific order.

        Args:
            order_id: The ID of the order.
            symbol: The trading symbol.

        Returns:
            An ExecutedOrder object if found, None otherwise.
        """
        pass

    @abstractmethod
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[ExecutedOrder]:
        """
        Fetches all open orders, optionally filtered by symbol.
        """
        pass

    @abstractmethod
    async def get_account_balance(self) -> AgentPortfolio:
        """
        Fetches the current account balance from the exchange.
        This method should update self.portfolio.
        """
        pass
    
    @abstractmethod
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Fetches the current market price for a symbol.
        Useful for market order estimations or pre-trade checks.
        """
        pass

    async def shutdown(self) -> None:
        """Perform cleanup tasks (e.g., close connections)."""
        pass

# Custom exceptions (optional, but good practice)
class ExchangeAdapterError(Exception):
    """Base exception for exchange adapter errors."""
    pass

class OrderPlacementError(ExchangeAdapterError):
    """Error during order placement."""
    pass

class InsufficientFundsError(OrderPlacementError):
    """Insufficient funds for the order."""
    pass

class OrderNotFoundError(ExchangeAdapterError):
    """Order not found on the exchange."""
    pass