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
from crypto_market_exchange_manager.data_sources.base_market_source import BaseMarketDataSource

logger = logging.getLogger(__name__)

class MockExchangeAdapterWithRealtimeData(BaseExchangeAdapter):
    """
    A mock exchange adapter that uses a BaseMarketDataSource for real-time prices.
    Simulates order execution and manages a mock portfolio.
    """
    def __init__(
        self,
        config: Dict[str, Any],
        initial_portfolio: Optional[AgentPortfolio] = None
    ):
        super().__init__(config, initial_portfolio)
        self.market_data_source = config.get("market_data_source")
        
        self.open_orders: Dict[str, ExecutedOrder] = {}
        self.trade_history: List[ExecutedOrder] = []
        self.slippage_factor: float = config.get("slippage_factor", 0.001)
        self.commission_rate: float = config.get("commission_rate", 0.001)
        self.fill_probability: float = config.get("fill_probability", 1.0)

        if not isinstance(self.market_data_source, BaseMarketDataSource):
            raise ValueError("market_data_source must be an instance of BaseMarketDataSource.")
        
        if not self.portfolio:
            self.portfolio = AgentPortfolio(cash_balance=config.get("initial_capital", {"USDT": 10000.0}))
        logger.info(f"MockExchangeAdapterWithRealtimeData initialized with portfolio: {self.portfolio.model_dump()}")

    async def initialize(self) -> None:
        logger.info("MockExchangeAdapterWithRealtimeData initialized (no external connections needed).")

    async def get_current_price(self, symbol: str) -> Optional[float]:
        # Use the real-time price from the market data source
        logger.info(f"Fetching real-time price for {symbol} from market data source.")
        price = self.market_data_source.get_current_price(symbol)
        if price is None:
            logger.warning(f"No real-time price available for {symbol}. Using fallback of 1.0.")
            return 1.0
        return price

    async def create_order(self, order_request: OrderRequest) -> ExecutedOrder:
        logger.info(f"MockExchange (Realtime): Received order request: {order_request.model_dump_json(indent=2)}")

        if random.random() > self.fill_probability:
            logger.warning(f"MockExchange: Order {order_request.request_id} for {order_request.symbol} did not fill due to probability.")
            executed_order = ExecutedOrder(
                order_id=order_request.client_order_id or f"mock_{uuid.uuid4().hex[:10]}",
                client_order_id=order_request.client_order_id,
                symbol=order_request.symbol,
                action=order_request.action,
                order_type=order_request.order_type,
                price=order_request.price or 0,
                quantity=order_request.quantity,
                timestamp=datetime.now(timezone.utc),
                status="REJECTED",
                metadata={"reason": "Simulated non-fill based on probability"}
            )
            return executed_order

        base_currency, quote_currency = order_request.symbol.split('/')
        sim_price = await self.get_current_price(order_request.symbol)
        logger.info(f"MockExchange: Simulated market price for {order_request.symbol} is {sim_price}")
        execution_price = sim_price
        if order_request.order_type == OrderType.LIMIT:
            execution_price = order_request.price
            if order_request.action == OrderAction.BUY and sim_price > order_request.price:
                logger.info(f"MockExchange: BUY LIMIT for {order_request.symbol} not filled (sim_price {sim_price} > limit {order_request.price}). Placing as open.")
                pending_order = ExecutedOrder(
                    order_id=order_request.client_order_id or f"mock_open_{uuid.uuid4().hex[:10]}",
                    client_order_id=order_request.client_order_id,
                    symbol=order_request.symbol, action=order_request.action, order_type=order_request.order_type,
                    price=order_request.price, quantity=order_request.quantity,
                    timestamp=datetime.now(timezone.utc), status="OPEN"
                )
                self.open_orders[pending_order.order_id] = pending_order
                return pending_order
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
                return pending_order
        elif order_request.order_type == OrderType.MARKET:
            if order_request.action == OrderAction.BUY:
                execution_price = sim_price * (1 + self.slippage_factor)
            else:
                execution_price = sim_price * (1 - self.slippage_factor)

        quantity_to_trade = order_request.quantity
        cost_or_proceeds = quantity_to_trade * execution_price
        commission = cost_or_proceeds * self.commission_rate

        if order_request.action == OrderAction.BUY:
            required_quote = cost_or_proceeds + (commission if quote_currency != base_currency else 0)
            if self.portfolio.cash_balance.get(quote_currency, 0) < required_quote:
                logger.error(f"MockExchange: Insufficient funds for BUY. Need {required_quote} {quote_currency}, have {self.portfolio.cash_balance.get(quote_currency, 0)}")
                raise InsufficientFundsError(f"Need {required_quote} {quote_currency}, have {self.portfolio.cash_balance.get(quote_currency, 0)}")
            self.portfolio.update_cash(quote_currency, -cost_or_proceeds)
            self.portfolio.update_cash(quote_currency, -commission)
            self.portfolio.update_asset(base_currency, quantity_to_trade)
        elif order_request.action == OrderAction.SELL:
            if self.portfolio.asset_holdings.get(base_currency, 0) < quantity_to_trade:
                logger.error(f"MockExchange: Insufficient asset for SELL. Need {quantity_to_trade} {base_currency}, have {self.portfolio.asset_holdings.get(base_currency, 0)}")
                raise InsufficientFundsError(f"Need {quantity_to_trade} {base_currency}, have {self.portfolio.asset_holdings.get(base_currency, 0)}")
            self.portfolio.update_asset(base_currency, -quantity_to_trade)
            self.portfolio.update_cash(quote_currency, cost_or_proceeds)
            self.portfolio.update_cash(quote_currency, -commission)

        asset_price_dictionary = {}
        for asset in self.portfolio.asset_holdings:
            asset_price_dictionary[asset] = await self.get_current_price(f"{asset}/USDT")
        self.portfolio.calculate_total_value(asset_price_dictionary)

        executed_order = ExecutedOrder(
            order_id=order_request.client_order_id or f"mock_{uuid.uuid4().hex[:10]}",
            client_order_id=order_request.client_order_id,
            symbol=order_request.symbol,
            action=order_request.action,
            order_type=order_request.order_type,
            price=execution_price,
            quantity=quantity_to_trade,
            timestamp=datetime.now(timezone.utc),
            fee=commission,
            fee_currency=quote_currency,
            status="FILLED",
            metadata={"simulated_market_price_at_trade": sim_price}
        )
        self.trade_history.append(executed_order)
        logger.info(f"MockExchange (Realtime): Order FILLED: {executed_order.model_dump_json(indent=2)}")
        logger.info(f"MockExchange (Realtime): Portfolio after trade: {self.portfolio.model_dump_json(indent=2)}")
        return executed_order

    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> bool:
        if order_id in self.open_orders:
            order_to_cancel = self.open_orders.pop(order_id)
            order_to_cancel.status = "CANCELED"
            order_to_cancel.timestamp = datetime.now(timezone.utc)
            self.trade_history.append(order_to_cancel)
            logger.info(f"MockExchange (Realtime): Order {order_id} canceled.")
            return True
        logger.warning(f"MockExchange (Realtime): Order {order_id} not found or not open for cancellation.")
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
        logger.debug("MockExchange (Realtime): Returning current mock portfolio.")
        self.portfolio.last_updated = datetime.now(timezone.utc)
        return self.portfolio

    async def shutdown(self) -> None:
        logger.info("MockExchangeAdapterWithRealtimeData shutdown (no specific actions needed).")
        self.open_orders.clear()
   