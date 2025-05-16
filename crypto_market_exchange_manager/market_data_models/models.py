# crypto_market_data_fetcher/market_data_models/models.py
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime

class OHLCV(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    symbol: str # e.g., BTC/USDT
    timeframe: str # e.g., 1h

    @validator('timestamp', pre=True)
    def convert_timestamp_to_datetime(cls, value):
        if isinstance(value, (int, float)): # Assuming timestamp in milliseconds
            return datetime.utcfromtimestamp(value / 1000)
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        return value # Already a datetime object

class Ticker(BaseModel):
    symbol: str  # e.g., BTC/USDT
    timestamp: datetime # When the ticker data was fetched/generated
    last: float      # Last traded price
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None # Same as last if not specified
    bid: Optional[float] = None  # Best bid price
    ask: Optional[float] = None  # Best ask price
    volume: Optional[float] = None # Trading volume in base currency
    quoteVolume: Optional[float] = None # Trading volume in quote currency
    vwap: Optional[float] = None # Volume Weighted Average Price
    change: Optional[float] = None # Absolute price change in 24h
    percentage: Optional[float] = None # Percentage price change in 24h
    average: Optional[float] = None # Average price in 24h
    info: Dict[str, Any] = Field(default_factory=dict) # Raw exchange response

    @validator('timestamp', pre=True)
    def convert_ticker_timestamp(cls, value):
        if isinstance(value, (int, float)):
            return datetime.utcfromtimestamp(value / 1000)
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        return value

class OrderBookEntry(BaseModel):
    price: float
    amount: float # Amount in base currency

class OrderBook(BaseModel):
    symbol: str
    timestamp: Optional[datetime] = None # When the order book was fetched/generated 
    bids: List[OrderBookEntry] # Highest bids first
    asks: List[OrderBookEntry] # Lowest asks first
    nonce: Optional[int] = None # Optional sequence number
    info: Dict[str, Any] = Field(default_factory=dict) # Raw exchange response

    @validator('timestamp', pre=True)
    def convert_orderbook_timestamp(cls, value):
        if isinstance(value, (int, float)):
            return datetime.utcfromtimestamp(value / 1000)
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        return value

class Trade(BaseModel):
    id: str
    timestamp: datetime
    symbol: str
    side: str # 'buy' or 'sell'
    price: float
    amount: float # Amount in base currency
    cost: Optional[float] = None # Amount in quote currency (price * amount)
    takerOrMaker: Optional[str] = None # 'taker' or 'maker'
    fee: Optional[Dict[str, Any]] = None
    info: Dict[str, Any] = Field(default_factory=dict)

    @validator('timestamp', pre=True)
    def convert_trade_timestamp(cls, value):
        if isinstance(value, (int, float)):
            return datetime.utcfromtimestamp(value / 1000)
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        return value