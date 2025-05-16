# crypto_market_data_fetcher/utils/market_helpers.py
import logging
from typing import List, Any, Dict, Optional
import ccxt # For type hinting if used, or just for general knowledge

def setup_market_logging(level=logging.INFO):
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(module)s.%(funcName)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger("MarketDataFetcher")

logger = setup_market_logging()

def format_symbol_for_exchange(symbol: str, exchange_name: str) -> str:
    """Converts 'BTC/USDT' to exchange-specific format if needed."""
    # Binance uses 'BTCUSDT' for spot, but CCXT handles this.
    # For direct API calls, you might need 'BTCUSDT'.
    # This function is a placeholder for more complex transformations if needed.
    if exchange_name.lower() == "binance_direct_api": # Example
        return symbol.replace("/", "")
    return symbol # CCXT generally handles standard 'BASE/QUOTE' format

def ccxt_ohlcv_to_pydantic(ccxt_ohlcv: List[List[Any]], symbol: str, timeframe: str) -> List["OHLCV"]: # type: ignore
    """Converts CCXT OHLCV list to a list of Pydantic OHLCV models."""
    from ..market_data_models.models import OHLCV # Local import to avoid circular dependency
    ohlcv_list = []
    for candle in ccxt_ohlcv:
        try:
            ohlcv_list.append(
                OHLCV(
                    timestamp=candle[0], # CCXT returns timestamp in ms
                    open=float(candle[1]),
                    high=float(candle[2]),
                    low=float(candle[3]),
                    close=float(candle[4]),
                    volume=float(candle[5]),
                    symbol=symbol,
                    timeframe=timeframe
                )
            )
        except Exception as e:
            logger.error(f"Error converting CCXT candle to Pydantic OHLCV for {symbol} @ {timeframe}: {candle} - Error: {e}")
    return ohlcv_list

def ccxt_ticker_to_pydantic(ccxt_ticker: Dict[str, Any]) -> Optional["Ticker"]: # type: ignore
    """Converts a CCXT ticker dictionary to a Pydantic Ticker model."""
    from ..market_data_models.models import Ticker # Local import
    if not ccxt_ticker:
        return None
    try:
        return Ticker(
            symbol=ccxt_ticker.get('symbol'),
            timestamp=ccxt_ticker.get('timestamp') or ccxt_ticker.get('datetime'), # CCXT uses timestamp or datetime
            last=ccxt_ticker.get('last'),
            open=ccxt_ticker.get('open'),
            high=ccxt_ticker.get('high'),
            low=ccxt_ticker.get('low'),
            close=ccxt_ticker.get('close'),
            bid=ccxt_ticker.get('bid'),
            ask=ccxt_ticker.get('ask'),
            volume=ccxt_ticker.get('baseVolume'), # CCXT uses baseVolume
            quoteVolume=ccxt_ticker.get('quoteVolume'),
            vwap=ccxt_ticker.get('vwap'),
            change=ccxt_ticker.get('change'),
            percentage=ccxt_ticker.get('percentage'),
            average=ccxt_ticker.get('average'),
            info=ccxt_ticker.get('info', {})
        )
    except Exception as e:
        logger.error(f"Error converting CCXT ticker to Pydantic Ticker for {ccxt_ticker.get('symbol')}: {e} - Data: {ccxt_ticker}")
        return None

def ccxt_order_book_to_pydantic(ccxt_ob: Dict[str, Any]) -> Optional["OrderBook"]: # type: ignore
    """Converts CCXT order book to Pydantic OrderBook model."""
    from ..market_data_models.models import OrderBook, OrderBookEntry # Local import
    if not ccxt_ob:
        return None
    try:
        bids = [OrderBookEntry(price=float(bid[0]), amount=float(bid[1])) for bid in ccxt_ob.get('bids', [])]
        asks = [OrderBookEntry(price=float(ask[0]), amount=float(ask[1])) for ask in ccxt_ob.get('asks', [])]
        return OrderBook(
            symbol=ccxt_ob.get('symbol'),
            timestamp=ccxt_ob.get('timestamp') or ccxt_ob.get('datetime'),
            bids=bids,
            asks=asks,
            nonce=ccxt_ob.get('nonce'),
            info=ccxt_ob.get('info', {})
        )
    except Exception as e:
        logger.error(f"Error converting CCXT order book to Pydantic for {ccxt_ob.get('symbol')}: {e} - Data: {ccxt_ob}")
        return None

def ccxt_trades_to_pydantic(ccxt_trades: List[Dict[str, Any]]) -> List["Trade"]: # type: ignore
    """Converts a list of CCXT trade dictionaries to Pydantic Trade models."""
    from ..market_data_models.models import Trade # Local import
    trades_list = []
    if not ccxt_trades:
        return trades_list
    for trade_data in ccxt_trades:
        try:
            trades_list.append(
                Trade(
                    id=str(trade_data.get('id')),
                    timestamp=trade_data.get('timestamp') or trade_data.get('datetime'),
                    symbol=trade_data.get('symbol'),
                    side=trade_data.get('side'),
                    price=float(trade_data.get('price')),
                    amount=float(trade_data.get('amount')),
                    cost=trade_data.get('cost'),
                    takerOrMaker=trade_data.get('takerOrMaker'),
                    fee=trade_data.get('fee'),
                    info=trade_data.get('info', {})
                )
            )
        except Exception as e:
            logger.error(f"Error converting CCXT trade to Pydantic for {trade_data.get('symbol')}: {e} - Data: {trade_data}")
    return trades_list