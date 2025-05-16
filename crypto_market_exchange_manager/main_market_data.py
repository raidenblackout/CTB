# crypto_market_data_fetcher/main_market_data.py
# Ensure this script is run in a way that Python can find the package
# e.g., from the parent directory: python -m crypto_market_data_fetcher.main_market_data
# or if inside the package: python main_market_data.py (after adjusting imports)

# For running as `python -m crypto_market_data_fetcher.main_market_data`
from .data_sources.binance_source import BinanceSource
from . import config_market # Import the market-specific config
from .utils.market_helpers import logger # Use the shared logger

# If running `python main_market_data.py` from within the package directory,
# you might need to change imports to be direct if PYTHONPATH is set up,
# or keep them relative if the execution context allows.
# For simplicity with `-m` execution, the relative imports above are preferred.

def run_fetches():
    logger.info("Starting Market Data Fetcher Example...")

    # Initialize Binance source
    # API keys can be passed here or will be picked from config_market.py / .env
    binance = BinanceSource()
    binance.check_exchange_capabilities() # Good to see what's available

    target_symbol = "BTC/USDT"
    alt_symbol = "ETH/USDT"

    # --- Fetch OHLCV ---
    logger.info(f"\n--- Fetching OHLCV for {target_symbol} ({config_market.DEFAULT_TIMEFRAME}) ---")
    ohlcv_data = binance.fetch_ohlcv(
        symbol=target_symbol,
        timeframe=config_market.DEFAULT_TIMEFRAME,
        limit=5 # Fetch only 5 candles for brevity
    )
    if ohlcv_data:
        logger.info(f"Fetched {len(ohlcv_data)} candles for {target_symbol}.")
        for candle in ohlcv_data: # Print first 2
            logger.info(f"  {candle.timestamp} O:{candle.open} H:{candle.high} L:{candle.low} C:{candle.close} V:{candle.volume}")
    else:
        logger.warning(f"No OHLCV data returned for {target_symbol}.")

    # --- Fetch Ticker ---
    logger.info(f"\n--- Fetching Ticker for {alt_symbol} ---")
    ticker_data = binance.fetch_ticker(symbol=alt_symbol)
    if ticker_data:
        logger.info(f"Ticker for {alt_symbol}: Last Price: {ticker_data.last}, Bid: {ticker_data.bid}, Ask: {ticker_data.ask}")
        logger.debug(f"Full Ticker data: {ticker_data.model_dump_json(indent=2)}") # Pydantic v2
        # For Pydantic v1: logger.debug(f"Full Ticker data: {ticker_data.json(indent=2)}")
    else:
        logger.warning(f"No Ticker data returned for {alt_symbol}.")

    # --- Fetch Multiple Tickers ---
    logger.info(f"\n--- Fetching Multiple Tickers ---")
    symbols_to_fetch = ["BTC/USDT", "ETH/USDT", "LTC/USDT"] # LTC/USDT might not exist or have low volume
    multiple_tickers = binance.fetch_tickers(symbols=symbols_to_fetch)
    if multiple_tickers:
        logger.info(f"Fetched {len(multiple_tickers)} tickers.")
        for sym, tick_data in multiple_tickers.items():
            logger.info(f"  {sym}: Last Price: {tick_data.last}")
    else:
        logger.warning("No data returned from fetch_tickers.")


    # --- Fetch Order Book ---
    logger.info(f"\n--- Fetching Order Book for {target_symbol} ---")
    order_book_data = binance.fetch_order_book(symbol=target_symbol, limit=5) # Top 5 bids/asks
    if order_book_data:
        logger.info(f"Order Book for {target_symbol} (Top 2 bids/asks):")
        logger.info(f"  Bids:")
        for bid in order_book_data.bids[:2]:
            logger.info(f"    Price: {bid.price}, Amount: {bid.amount}")
        logger.info(f"  Asks:")
        for ask in order_book_data.asks[:2]:
            logger.info(f"    Price: {ask.price}, Amount: {ask.amount}")
        logger.debug(f"Full Order Book data: {order_book_data.model_dump_json(indent=2)}") # Pydantic v2
    else:
        logger.warning(f"No Order Book data returned for {target_symbol}.")


    # --- Fetch Trades ---
    logger.info(f"\n--- Fetching Recent Trades for {alt_symbol} ---")
    trades_data = binance.fetch_trades(symbol=alt_symbol, limit=3) # Last 3 trades
    if trades_data:
        logger.info(f"Fetched {len(trades_data)} recent trades for {alt_symbol}:")
        for trade in trades_data:
            logger.info(f"  ID: {trade.id}, Time: {trade.timestamp}, Side: {trade.side}, Price: {trade.price}, Amount: {trade.amount}")
    else:
        logger.warning(f"No trades data returned for {alt_symbol}.")


    logger.info("\nMarket Data Fetcher Example Finished.")

if __name__ == "__main__":
    # This structure assumes you might run this script directly
    # For package execution (`python -m ...`), Python handles the path.
    # If running directly and imports fail, you might need to adjust sys.path or how you run it.
    run_fetches()