# crypto_market_data_fetcher/data_sources/binance_source.py
import ccxt
from typing import List, Optional, Dict, Any
from .base_market_source import BaseMarketDataSource
# Use .. for relative imports if running main_market_data.py as part of a package
from ..market_data_models.models import OHLCV, Ticker, OrderBook, Trade
from ..utils.market_helpers import (
    logger,
    ccxt_ohlcv_to_pydantic,
    ccxt_ticker_to_pydantic,
    ccxt_order_book_to_pydantic,
    ccxt_trades_to_pydantic
)
from .. import config_market # Import the market-specific config

class BinanceSource(BaseMarketDataSource):
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        super().__init__(exchange_name="binance")
        self.api_key = api_key or config_market.BINANCE_API_KEY
        self.api_secret = api_secret or config_market.BINANCE_API_SECRET
        self.client: ccxt.binance = self._init_client() # type: ignore

    def _init_client(self) -> ccxt.binance: # type: ignore
        """Initializes the CCXT Binance client."""
        try:
            exchange_params = {
                'apiKey': self.api_key,
                'secret': self.api_secret,
                'enableRateLimit': False, # Recommended by CCXT
                'options': {
                    'adjustForTimeDifference': True, # Adjusts for clock skew
                    #'defaultType': 'spot', # Or 'future', 'margin'
                }
            }
            # Remove None values for apiKey and secret if not provided
            if not exchange_params['apiKey']: del exchange_params['apiKey']
            if not exchange_params['secret']: del exchange_params['secret']

            client = ccxt.binance()
            # client.set_sandbox_mode(True) # For testing with Binance testnet
            self.logger.info("CCXT Binance client initialized successfully.")
            return client
        except Exception as e:
            self.logger.error(f"Failed to initialize CCXT Binance client: {e}")
            raise # Re-raise the exception to halt if client initialization fails

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = config_market.DEFAULT_TIMEFRAME,
        since: Optional[int] = None,
        limit: Optional[int] = config_market.DEFAULT_OHLCV_LIMIT,
        params: Optional[Dict[str, Any]] = None
    ) -> List[OHLCV]:
        self.logger.debug(f"Fetching OHLCV for {symbol} on timeframe {timeframe} with limit {limit}")
        try:
            if not self.client.has['fetchOHLCV']:
                self.logger.warning(f"Binance client does not support fetchOHLCV.")
                return []
            parameters = {
                'symbol': symbol,
                'timeframe': timeframe,
                'since': since,
                'limit': limit,
                'params': params
            }

            if not since:
                parameters.pop('since')
            if not limit:
                parameters.pop('limit')
            if not params:
                parameters.pop('params')
             
            # CCXT expects symbol in 'BASE/QUOTE' format
            raw_ohlcv = self.client.fetch_ohlcv(**parameters)
            return ccxt_ohlcv_to_pydantic(raw_ohlcv, symbol, timeframe)
        except ccxt.NetworkError as e:
            self.logger.error(f"CCXT NetworkError fetching OHLCV for {symbol}: {e}")
        except ccxt.ExchangeError as e:
            self.logger.error(f"CCXT ExchangeError fetching OHLCV for {symbol}: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error fetching OHLCV for {symbol}: {e}", exc_info=True)
        return []

    def fetch_ticker(self, symbol: str, params: Optional[Dict[str, Any]] = None) -> Optional[Ticker]:
        self.logger.debug(f"Fetching ticker for {symbol}")
        try:
            if not self.client.has['fetchTicker']:
                self.logger.warning(f"Binance client does not support fetchTicker.")
                return None
            parameters = {
                'symbol': symbol,
                'params': params
            }
            if not params:
                parameters.pop('params')

            raw_ticker = self.client.fetch_ticker(**parameters)
            return ccxt_ticker_to_pydantic(raw_ticker)
        except Exception as e:
            self.logger.error(f"Error fetching ticker for {symbol}: {e}", exc_info=True)
        return None

    def fetch_tickers(self, symbols: Optional[List[str]] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Ticker]:
        self.logger.debug(f"Fetching tickers for {symbols if symbols else 'all available'}")
        tickers_dict: Dict[str, Ticker] = {}
        try:
            if not self.client.has['fetchTickers']:
                self.logger.warning(f"Binance client does not support fetchTickers.")
                return tickers_dict
            parameters = {
                'symbols': symbols,
                'params': params
            }
            if not symbols:
                parameters.pop('symbols')
            if not params:
                parameters.pop('params')
            raw_tickers = self.client.fetch_tickers(**parameters) # symbols can be None for all
            for symbol_key, raw_ticker_data in raw_tickers.items():
                pydantic_ticker = ccxt_ticker_to_pydantic(raw_ticker_data)
                if pydantic_ticker:
                    tickers_dict[symbol_key] = pydantic_ticker
            return tickers_dict
        except Exception as e:
            self.logger.error(f"Error fetching tickers for {symbols}: {e}", exc_info=True)
        return tickers_dict

    def fetch_order_book(self, symbol: str, limit: Optional[int] = config_market.DEFAULT_ORDER_BOOK_LIMIT, params: Optional[Dict[str, Any]] = None) -> Optional[OrderBook]:
        self.logger.debug(f"Fetching order book for {symbol} with limit {limit}")
        try:
            if not self.client.has['fetchOrderBook']:
                self.logger.warning(f"Binance client does not support fetchOrderBook.")
                return None
            parameters = {
                'symbol': symbol,
                'limit': limit,
                'params': params
            }
            if not limit:
                parameters.pop('limit')
            if not params:
                parameters.pop('params')
            
            raw_ob = self.client.fetch_order_book(**parameters)
            return ccxt_order_book_to_pydantic(raw_ob)
        except Exception as e:
            self.logger.error(f"Error fetching order book for {symbol}: {e}", exc_info=True)
        return None

    def fetch_trades(self, symbol: str, since: Optional[int] = None, limit: Optional[int] = 25, params: Optional[Dict[str, Any]] = None) -> List[Trade]:
        self.logger.debug(f"Fetching trades for {symbol} with limit {limit}")
        try:
            if not self.client.has['fetchTrades']:
                self.logger.warning(f"Binance client does not support fetchTrades.")
                return []
            parameters = {
                'symbol': symbol,
                'since': since,
                'limit': limit,
                'params': params
            }

            if not since:
                parameters.pop('since')
            if not limit:
                parameters.pop('limit')
            if not params:
                parameters.pop('params')
            
            raw_trades = self.client.fetch_trades(**parameters)
            return ccxt_trades_to_pydantic(raw_trades)
        except Exception as e:
            self.logger.error(f"Error fetching trades for {symbol}: {e}", exc_info=True)
        return []