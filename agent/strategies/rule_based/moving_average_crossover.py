# Crypto_Trading_Bot/agent/strategies/rule_based/moving_average_crossover.py

import logging
from typing import List, Dict, Any, Optional
import pandas as pd # For TA calculations

from agent.strategies.base_strategy import BaseStrategy
from agent.agent_context import AgentContext
from agent.trading_models import TradingSignal, OrderAction, AgentPortfolio
# Assuming OHLCV model is available from market_data_models
from crypto_market_exchange_manager.market_data_models.models import OHLCV

logger = logging.getLogger(__name__)

class MovingAverageCrossoverStrategy(BaseStrategy):
    """
    A strategy that generates BUY/SELL signals based on moving average crossovers.
    """
    def __init__(self, strategy_name: str, context: AgentContext, config: Dict[str, Any]):
        super().__init__(strategy_name, context, config)
        
        self.symbol: str = self.config.get("symbol", "BTC/USDT")
        self.short_window: int = self.config.get("short_window", 20)
        self.long_window: int = self.config.get("long_window", 50)
        self.timeframe: str = self.config.get("timeframe", "1h")
        self.trade_quantity_percentage: float = self.config.get("trade_quantity_percentage", 0.1) # 10% of available quote currency

        if self.short_window >= self.long_window:
            raise ValueError("Short window must be smaller than long window for MA Crossover.")
        
        self.data: pd.DataFrame = pd.DataFrame()
        self.position_active: bool = False # True if we have an open long position

    async def _fetch_and_prepare_data(self) -> bool:
        """
        Fetches historical OHLCV data and calculates moving averages.
        """
        if not self.context.market_data_source:
            logger.error(f"[{self.strategy_name}] Market data source not available in context.")
            return False

        try:
            # Fetch enough data for the longest window + a bit more for stability
            limit = self.long_window + 50 
            ohlcv_data: List[OHLCV] = self.context.market_data_source.fetch_ohlcv(
                symbol=self.symbol,
                timeframe=self.timeframe,
                limit=limit
            )

            if not ohlcv_data or len(ohlcv_data) < self.long_window:
                logger.warning(f"[{self.strategy_name}] Not enough OHLCV data for {self.symbol}. Need {self.long_window}, got {len(ohlcv_data)}.")
                return False

            # Convert to DataFrame
            df = pd.DataFrame([{"timestamp": o.timestamp, "open": o.open, "high": o.high, 
                                "low": o.low, "close": o.close, "volume": o.volume} for o in ohlcv_data])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.set_index('timestamp')
            
            df[f'sma_short'] = df['close'].rolling(window=self.short_window).mean()
            df[f'sma_long'] = df['close'].rolling(window=self.long_window).mean()
            
            self.data = df.dropna() # Remove rows with NaN from rolling mean calculation
            return True
        except Exception as e:
            logger.error(f"[{self.strategy_name}] Error fetching or preparing data for {self.symbol}: {e}")
            return False

    async def initialize(self) -> None:
        await super().initialize()
        logger.info(f"[{self.strategy_name}] Initializing MovingAverageCrossoverStrategy for {self.symbol} "
                    f"with short_window={self.short_window}, long_window={self.long_window}, timeframe={self.timeframe}.")
        await self._fetch_and_prepare_data()
        # Initialize position_active based on portfolio if necessary
        # For simplicity, we assume starting flat. A real bot would check current holdings.

    async def generate_signals(self, portfolio: AgentPortfolio) -> List[TradingSignal]:
        signals: List[TradingSignal] = []

        if not await self._fetch_and_prepare_data() or self.data.empty:
            logger.warning(f"[{self.strategy_name}] No data available to generate signals for {self.symbol}.")
            return signals

        latest_data = self.data.iloc[-1]
        previous_data = self.data.iloc[-2] if len(self.data) > 1 else latest_data

        sma_short = latest_data[f'sma_short']
        sma_long = latest_data[f'sma_long']
        prev_sma_short = previous_data[f'sma_short']
        prev_sma_long = previous_data[f'sma_long']

        current_price = latest_data['close']
        logger.info(f"[{self.strategy_name}] {self.symbol} - Current Close: {current_price:.2f}, "
                    f"SMA({self.short_window}): {sma_short:.2f}, SMA({self.long_window}): {sma_long:.2f}")

        # Quote currency (e.g., USDT in BTC/USDT)
        quote_currency = self.symbol.split('/')[-1]
        base_currency = self.symbol.split('/')[0]

        # Golden Cross: Short MA crosses above Long MA - BUY signal
        if prev_sma_short <= prev_sma_long and sma_short > sma_long:
            if not self.position_active: # Only buy if not already in a position
                # Check if we have enough quote currency to buy
                if portfolio.cash_balance.get(quote_currency, 0) > 0:
                    signals.append(TradingSignal(
                        symbol=self.symbol,
                        action=OrderAction.BUY,
                        confidence=0.8, # Example confidence
                        quantity_percentage=self.trade_quantity_percentage,
                        price=current_price, # Could be market order, or limit at current_price
                        strategy_name=self.strategy_name,
                        metadata={"reason": f"Golden Cross: SMA({self.short_window}) crossed above SMA({self.long_window})",
                                  "sma_short": sma_short, "sma_long": sma_long}
                    ))
                    self.position_active = True # Assume buy will be successful for this simplified logic
                    logger.info(f"[{self.strategy_name}] BUY signal generated for {self.symbol} due to Golden Cross.")
                else:
                    logger.warning(f"[{self.strategy_name}] Golden Cross detected for {self.symbol}, but no {quote_currency} balance to buy.")
            else:
                logger.info(f"[{self.strategy_name}] Golden Cross detected for {self.symbol}, but already in an active position.")

        # Death Cross: Short MA crosses below Long MA - SELL signal
        elif prev_sma_short >= prev_sma_long and sma_short < sma_long:
            if self.position_active: # Only sell if in a position (i.e., holding the base_currency)
                # Check if we hold the base currency
                if portfolio.asset_holdings.get(base_currency, 0) > 0:
                    signals.append(TradingSignal(
                        symbol=self.symbol,
                        action=OrderAction.SELL,
                        confidence=0.8, # Example confidence
                        # Sell all of the asset held by this strategy (or a percentage of it)
                        # For simplicity, selling based on the initial buy percentage logic
                        quantity_percentage=1.0, # Sell 100% of what this strategy controls.
                                                # More complex: track actual holdings for this strategy.
                        price=current_price,
                        strategy_name=self.strategy_name,
                        metadata={"reason": f"Death Cross: SMA({self.short_window}) crossed below SMA({self.long_window})",
                                  "sma_short": sma_short, "sma_long": sma_long}
                    ))
                    self.position_active = False # Assume sell will be successful
                    logger.info(f"[{self.strategy_name}] SELL signal generated for {self.symbol} due to Death Cross.")
                else:
                     logger.warning(f"[{self.strategy_name}] Death Cross detected for {self.symbol}, but no {base_currency} to sell. Position state might be inconsistent.")
                     self.position_active = False # Reset state if no asset
            else:
                logger.info(f"[{self.strategy_name}] Death Cross detected for {self.symbol}, but not in an active position.")
        
        else: # No crossover, HOLD
            signals.append(TradingSignal(
                symbol=self.symbol,
                action=OrderAction.HOLD,
                confidence=0.5,
                strategy_name=self.strategy_name,
                metadata={"reason": "No crossover event."}
            ))
            logger.info(f"[{self.strategy_name}] HOLD signal for {self.symbol}. No crossover.")

        return signals

    async def on_order_update(self, executed_order: Any) -> None:
        """
        Update position_active based on actual executed orders.
        This is a simplified version. A real system would need more robust state management.
        """
        await super().on_order_update(executed_order)
        # Assuming executed_order is an ExecutedOrder model from trading_models.py
        if executed_order.symbol == self.symbol and executed_order.status == "FILLED":
            if executed_order.action == OrderAction.BUY:
                self.position_active = True
                logger.info(f"[{self.strategy_name}] Position for {self.symbol} became active after BUY order {executed_order.order_id}.")
            elif executed_order.action == OrderAction.SELL:
                self.position_active = False
                logger.info(f"[{self.strategy_name}] Position for {self.symbol} became inactive after SELL order {executed_order.order_id}.")

    def get_status(self) -> Dict[str, Any]:
        status = super().get_status()
        status.update({
            "symbol": self.symbol,
            "short_window": self.short_window,
            "long_window": self.long_window,
            "timeframe": self.timeframe,
            "position_active": self.position_active,
            "last_data_rows": len(self.data),
            "last_sma_short": self.data[f'sma_short'].iloc[-1] if not self.data.empty else None,
            "last_sma_long": self.data[f'sma_long'].iloc[-1] if not self.data.empty else None,
        })
        return status

# Create __init__.py for rule_based folder
# Crypto_Trading_Bot/agent/strategies/rule_based/__init__.py
"""
Rule-based trading strategies.
"""
from .moving_average_crossover import MovingAverageCrossoverStrategy

# __all__ can be used to specify what gets imported with 'from . import *'
__all__ = [
    "MovingAverageCrossoverStrategy"
]