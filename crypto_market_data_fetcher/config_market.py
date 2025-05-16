# crypto_market_data_fetcher/config_market.py
import os
from dotenv import load_dotenv

load_dotenv()

# Binance API Credentials (Optional, for higher rate limits or private endpoints)
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET")

# Target symbols for fetching data (format: BASE/QUOTE, e.g., BTC/USDT)
DEFAULT_SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]

# Default timeframes/intervals for OHLCV data
# Binance examples: '1m', '5m', '15m', '1h', '4h', '1d', '1w', '1M'
DEFAULT_TIMEFRAME = "1h"
DEFAULT_OHLCV_LIMIT = 100 # Default number of candles to fetch

# Order book depth
DEFAULT_ORDER_BOOK_LIMIT = 20 # Number of bids and asks

# Request timeout
REQUEST_TIMEOUT = 20 # Seconds

# Default exchange to use
DEFAULT_EXCHANGE = "binance" # Can be 'binance', 'coingecko', etc. later