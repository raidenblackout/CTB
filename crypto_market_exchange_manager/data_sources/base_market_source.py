# crypto_market_data_fetcher/data_sources/base_market_source.py
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from ..market_data_models.models import OHLCV, Ticker, OrderBook, Trade # Use .. for relative if running as package
from ..utils.market_helpers import logger # Use .. for relative if running as package

class BaseMarketDataSource(ABC):
    def __init__(self, exchange_name: str):
        self.exchange_name = exchange_name
        self.logger = logger # Use shared logger

    @abstractmethod
    def _init_client(self) -> Any:
        """Initializes and returns the exchange-specific API client."""
        pass

    @abstractmethod
    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        since: Optional[int] = None, # Timestamp in ms
        limit: Optional[int] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> List[OHLCV]:
        """Fetches OHLCV (candlestick) data."""
        pass

    @abstractmethod
    def fetch_ticker(self, symbol: str, params: Optional[Dict[str, Any]] = None) -> Optional[Ticker]:
        """Fetches ticker information for a symbol."""
        pass

    @abstractmethod
    def fetch_tickers(self, symbols: Optional[List[str]] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Ticker]:
        """Fetches ticker information for multiple symbols."""
        pass

    @abstractmethod
    def fetch_order_book(self, symbol: str, limit: Optional[int] = None, params: Optional[Dict[str, Any]] = None) -> Optional[OrderBook]:
        """Fetches the order book for a symbol."""
        pass

    @abstractmethod
    def fetch_trades(self, symbol: str, since: Optional[int] = None, limit: Optional[int] = None, params: Optional[Dict[str, Any]] = None) -> List[Trade]:
        """Fetches recent public trades for a symbol."""
        pass

    def check_exchange_capabilities(self):
        """Logs capabilities of the exchange client."""
        if hasattr(self.client, 'has'):
            self.logger.info(f"Capabilities for {self.exchange_name}:")
            self.logger.info(f"  Fetch OHLCV: {self.client.has.get('fetchOHLCV')}")
            self.logger.info(f"  Fetch Ticker: {self.client.has.get('fetchTicker')}")
            self.logger.info(f"  Fetch Tickers: {self.client.has.get('fetchTickers')}")
            self.logger.info(f"  Fetch Order Book: {self.client.has.get('fetchOrderBook')}")
            self.logger.info(f"  Fetch Trades: {self.client.has.get('fetchTrades')}")
        else:
            self.logger.warning(f"Cannot determine capabilities for {self.exchange_name} client (no 'has' attribute).")

    @abstractmethod
    def place_order(self, symbol: str, order_type: str, side: str, amount: float, price: Optional[float] = None) -> Dict[str, Any]:
        """Places an order on the exchange."""
        pass

    @abstractmethod
    def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> bool:
        """Cancels an open order."""
        pass

    @abstractmethod
    def get_order_status(self, order_id: str, symbol: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Fetches the status of a specific order."""
        pass

    @abstractmethod
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetches all open orders, optionally filtered by symbol."""
        pass

    @abstractmethod
    def get_account_balance(self) -> Dict[str, float]:
        """Fetches the current account balance from the exchange."""
        pass

    @abstractmethod
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Fetches the current price for a symbol."""
        pass

    @abstractmethod
    def get_historical_data(self, symbol: str, timeframe: str, since: Optional[int] = None, limit: Optional[int] = None) -> List[OHLCV]:
        """Fetches historical data for a symbol."""
        pass

    @abstractmethod
    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetches detailed information about a specific symbol."""
        pass

    @abstractmethod
    def get_all_symbols(self) -> List[str]:
        """Fetches all available trading symbols on the exchange."""
        pass