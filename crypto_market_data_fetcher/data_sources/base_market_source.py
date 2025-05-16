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