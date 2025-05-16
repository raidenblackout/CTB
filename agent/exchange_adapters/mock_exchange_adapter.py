# Crypto_Trading_Bot/agent/exchange_adapters/mock_exchange_adapter.py

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import random # For simulating price slippage or partial fills

from agent.exchange_adapters.base_exchange_adapter import (
    BaseExchangeAdapter, OrderRequest, ExchangeAdapterError,
    OrderPlacementError, InsufficientFundsError, OrderNotFoundError
)
from agent.trading_models import ExecutedOrder, OrderAction, OrderType, AgentPortfolio

logger = logging.getLogger(__name__)

class MockExchangeAdapter(BaseExchangeAdapter):
    """
    A mock exchange adapter for simulation and testing.
    Simulates order execution and manages a mock portfolio.
    """
    def __init__(self, config: Dict[str, Any], initial_portfolio: Optional[AgentPortfolio] = None):
        super().__init__(config, initial_portfolio)
        self.open_orders: Dict[str, ExecutedOrder] = {} # Stores orders that are not yet 'FILLED' or 'CANCELED'
        self.trade_history: List[ExecutedOrder] = []
        self.current_sim_prices: Dict[str, float] = config.get("initial_prices", {}) # e.g., {"BTC/USDT": 50000.0}
        self.slippage_factor: float = config.get("slippage_factor", 0.001) # 0.1% slippage
        self.commission_rate: float = config.get("commission_rate", 0.001) # 0.1% commission
        self.fill_probability: float = config.get("fill_probability", 1.0) # Chance an order gets filled

        if not self.portfolio: # Ensure portfolio is initialized
            self.portfolio = AgentPortfolio(cash_balance=config.get("initial_capital", {"USDT": 10000.0}))
        logger.info(f"MockExchangeAdapter initialized with portfolio: {self.portfolio.model_dump()}")
        logger.info(f"MockExchangeAdapter initial prices: {self.current_sim_prices}")

    async def initialize(self) -> None:
        logger.info("MockExchangeAdapter initialized (no external connections needed).")
        # In a real adapter, this might connect to WebSocket, fetch initial balances, etc.

    def _get_sim_price(self, symbol: str) -> float:
        """Gets the simulated current price for a symbol, with slight random variation."""
        base_price = self.current_sim_prices.get(symbol)
        if base_price is None:
            logger.warning(f"No simulated price set for {symbol}. Using default of 1.0 for calculations.")
            base_price = 1.0 # Fallback, but should be configured
        # Add a little noise to simulate market movement if desired
        return base_price * (1 + (random.random() - 0.5) * 0.0005) # Tiny fluctuation

    def update_price(self, symbol: str, price: float):
        """Allows external updates to the simulated price."""
        self.current_sim_prices[symbol] = price
        logger.debug(f"Mock price for {symbol} updated to {price}")

    async def get_current_price(self, symbol: str) -> Optional[float]:
        return self.current_sim_prices.get(symbol)

    async def create_order(self, order_request: OrderRequest) -> ExecutedOrder:
        logger.info(f"MockExchange: Received order request: {order_request.model_dump_json(indent=2)}")

        if random.random() > self.fill_probability:
            logger.warning(f"MockExchange: Order {order_request.request_id} for {order_request.symbol} did not fill due to probability.")
            # Could return a 'REJECTED' status or raise specific error
            executed_order = ExecutedOrder(
                order_id=order_request.client_order_id or f"mock_{uuid.uuid4().hex[:10]}",
                client_order_id=order_request.client_order_id,
                symbol=order_request.symbol,
                action=order_request.action,
                order_type=order_request.order_type,
                price=order_request.price or 0,
                quantity=order_request.quantity,
                timestamp=datetime.now(timezone.utc),
                status="REJECTED", # Or some other non-filled status
                metadata={"reason": "Simulated non-fill based on probability"}
            )
            # self.open_orders[executed_order.order_id] = executed_order # If it's pending rejection
            return executed_order


        base_currency, quote_currency = order_request.symbol.split('/')
        sim_price = self._get_sim_price(order_request.symbol)
        
        execution_price = sim_price
        if order_request.order_type == OrderType.LIMIT:
            execution_price = order_request.price # Assume limit order fills at exact price if conditions met
            # Basic limit order fill logic for mock:
            if order_request.action == OrderAction.BUY and sim_price > order_request.price:
                logger.info(f"MockExchange: BUY LIMIT for {order_request.symbol} not filled (sim_price {sim_price} > limit {order_request.price}). Placing as open.")
                # Create an open order
                pending_order = ExecutedOrder(
                    order_id=order_request.client_order_id or f"mock_open_{uuid.uuid4().hex[:10]}",
                    client_order_id=order_request.client_order_id,
                    symbol=order_request.symbol, action=order_request.action, order_type=order_request.order_type,
                    price=order_request.price, quantity=order_request.quantity,
                    timestamp=datetime.now(timezone.utc), status="OPEN"
                )
                self.open_orders[pending_order.order_id] = pending_order
                return pending_order # Return the open order
            elif order_request.action == OrderAction.SELL and sim_price < order_request.price:
                logger.info(f"MockExchange: SELL LIMIT for {order_request.symbol} not filled (sim_price {sim_price} < limit {order_request.price}). Placing as open.")
                pending_order = ExecutedOrder(
                    order_id=order_request.client_order_id or f"mock_open_{uuid.uuid4().hex[:10]}",
                    client_order_id=order_request.client_order_id,
                    symbol=order_request.symbol, action=order_request.action, order_type=order_request.order_type,
                    price=order_request.price, quantity=order_request.quantity,
                    timestamp=datetime.now(timezone.utc), status="OPEN"
                )
                self.open_orders[pending_order.order_id] = pending_order
                return pending_order # Return the open order
        elif order_request.order_type == OrderType.MARKET:
            # Apply slippage for market orders
            if order_request.action == OrderAction.BUY:
                execution_price = sim_price * (1 + self.slippage_factor)
            else: # SELL
                execution_price = sim_price * (1 - self.slippage_factor)
        
        quantity_to_trade = order_request.quantity
        cost_or_proceeds = quantity_to_trade * execution_price
        commission = cost_or_proceeds * self.commission_rate

        # Check funds
        if order_request.action == OrderAction.BUY:
            required_quote = cost_or_proceeds + (commission if quote_currency != base_currency else 0) # Commission typically in quote
            if self.portfolio.cash_balance.get(quote_currency, 0) < required_quote:
                logger.error(f"MockExchange: Insufficient funds for BUY. Need {required_quote} {quote_currency}, have {self.portfolio.cash_balance.get(quote_currency, 0)}")
                raise InsufficientFundsError(f"Need {required_quote} {quote_currency}, have {self.portfolio.cash_balance.get(quote_currency, 0)}")
            
            self.portfolio.update_cash(quote_currency, -cost_or_proceeds)
            self.portfolio.update_cash(quote_currency, -commission) # Assuming commission paid in quote
            self.portfolio.update_asset(base_currency, quantity_to_trade)
        
        elif order_request.action == OrderAction.SELL:
            if self.portfolio.asset_holdings.get(base_currency, 0) < quantity_to_trade:
                logger.error(f"MockExchange: Insufficient asset for SELL. Need {quantity_to_trade} {base_currency}, have {self.portfolio.asset_holdings.get(base_currency, 0)}")
                raise InsufficientFundsError(f"Need {quantity_to_trade} {base_currency}, have {self.portfolio.asset_holdings.get(base_currency, 0)}")

            self.portfolio.update_asset(base_currency, -quantity_to_trade)
            self.portfolio.update_cash(quote_currency, cost_or_proceeds)
            self.portfolio.update_cash(quote_currency, -commission) # Commission deducted from proceeds
            

        executed_order = ExecutedOrder(
            order_id=order_request.client_order_id or f"mock_{uuid.uuid4().hex[:10]}",
            client_order_id=order_request.client_order_id,
            symbol=order_request.symbol,
            action=order_request.action,
            order_type=order_request.order_type,
            price=execution_price, # Actual simulated execution price
            quantity=quantity_to_trade, # Assuming full fill for simplicity here
            timestamp=datetime.now(timezone.utc),
            fee=commission,
            fee_currency=quote_currency, # Assuming commission in quote currency
            status="FILLED",
            # cost=cost_or_proceeds, # This could be a useful addition to ExecutedOrder
            metadata={"simulated_market_price_at_trade": sim_price}
        )
        self.trade_history.append(executed_order)
        logger.info(f"MockExchange: Order FILLED: {executed_order.model_dump_json(indent=2)}")
        logger.info(f"MockExchange: Portfolio after trade: {self.portfolio.model_dump_json(indent=2)}")
        return executed_order

    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> bool:
        if order_id in self.open_orders:
            order_to_cancel = self.open_orders.pop(order_id)
            order_to_cancel.status = "CANCELED"
            order_to_cancel.timestamp = datetime.now(timezone.utc) # Update timestamp
            self.trade_history.append(order_to_cancel) # Move to history
            logger.info(f"MockExchange: Order {order_id} canceled.")
            return True
        logger.warning(f"MockExchange: Order {order_id} not found or not open for cancellation.")
        return False

    async def get_order_status(self, order_id: str, symbol: Optional[str] = None) -> Optional[ExecutedOrder]:
        if order_id in self.open_orders:
            return self.open_orders[order_id]
        for trade in self.trade_history:
            if trade.order_id == order_id:
                return trade
        return None

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[ExecutedOrder]:
        if symbol:
            return [order for order in self.open_orders.values() if order.symbol == symbol]
        return list(self.open_orders.values())

    async def get_account_balance(self) -> AgentPortfolio:
        logger.debug("MockExchange: Returning current mock portfolio.")
        # In a real exchange, this would fetch from the API and update self.portfolio
        self.portfolio.last_updated = datetime.now(timezone.utc)
        return self.portfolio

    async def shutdown(self) -> None:
        logger.info("MockExchangeAdapter shutdown (no specific actions needed).")
        self.open_orders.clear()