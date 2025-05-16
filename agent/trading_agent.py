# Crypto_Trading_Bot/agent/trading_agent.py
import asyncio
import importlib
import logging
from typing import Any, Dict, List, Optional, Type

from agent.agent_context import AgentContext
from agent.agent_config import FullAgentConfig # StrategyConfig removed as it's part of FullAgentConfig
from agent.exchange_adapters.mock_exchange_adapter import MockExchangeAdapter
from agent.strategies.base_strategy import BaseStrategy
from agent.trading_models import TradingSignal, OrderAction, AgentPortfolio, ExecutedOrder, OrderType
from agent.exchange_adapters.base_exchange_adapter import OrderRequest, ExchangeAdapterError, InsufficientFundsError, OrderPlacementError

logger = logging.getLogger(__name__)

class TradingAgent:
    def __init__(self, config: FullAgentConfig, context: AgentContext):
        self.config: FullAgentConfig = config
        self.context: AgentContext = context
        self.strategies: List[BaseStrategy] = []
        # Portfolio is now primarily managed/fetched by the exchange adapter.
        # The agent can keep a reference or rely on the adapter's state.
        # For mock, it's initialized in the adapter. For real, it's fetched.
        self.portfolio: AgentPortfolio = AgentPortfolio( # Initial state, will be updated by adapter
             cash_balance=self.config.agent_settings.initial_capital.copy()
        ) 
        self.is_running: bool = False
        self._load_strategies()

        if not self.context.exchange_adapter:
            logger.error("TradingAgent initialized without an ExchangeAdapter in context. Trading will not function.")
            # Consider raising an error or preventing start if no adapter
            # raise ValueError("ExchangeAdapter is required in AgentContext for TradingAgent.")


    def _load_strategies(self):
        """
        Loads and initializes strategies based on the configuration.
        """
        self.strategies = []
        for strat_conf in self.config.strategies:
            try:
                module_path, class_name = strat_conf.module, strat_conf.class_name
                module = importlib.import_module(module_path)
                StrategyClass: Type[BaseStrategy] = getattr(module, class_name)
                
                strategy_instance = StrategyClass(
                    strategy_name=strat_conf.name,
                    context=self.context,
                    config=strat_conf.parameters
                )
                self.strategies.append(strategy_instance)
                logger.info(f"Successfully loaded strategy: {strat_conf.name} ({class_name})")
            except ImportError as e:
                logger.error(f"Failed to import module for strategy {strat_conf.name}: {module_path}. Error: {e}")
            except AttributeError as e:
                logger.error(f"Failed to find class {class_name} in module {module_path} for strategy {strat_conf.name}. Error: {e}")
            except Exception as e:
                logger.error(f"Failed to initialize strategy {strat_conf.name}. Error: {e}")
        
        if not self.strategies:
            logger.warning("No strategies were loaded. The agent might not perform any actions.")

    async def initialize_components(self):
        """Initializes strategies and the exchange adapter."""
        logger.info("Initializing Trading Agent components...")
        
        # Initialize Exchange Adapter first (might fetch portfolio)
        if self.context.exchange_adapter:
            try:
                await self.context.exchange_adapter.initialize()
                logger.info("Exchange adapter initialized successfully.")
                # Update agent's portfolio view after adapter initialization
                self.portfolio = await self.context.exchange_adapter.get_account_balance()
                logger.info(f"Initial portfolio from adapter: {self.portfolio.model_dump_json(indent=2)}")
            except Exception as e:
                logger.error(f"Failed to initialize exchange adapter: {e}", exc_info=True)
                # Depending on severity, you might want to stop the agent
                # For now, we'll log and continue, but trading will fail.
        else:
            logger.warning("No exchange adapter to initialize.")


        logger.info("Initializing all loaded strategies...")
        initialization_tasks = [strategy.initialize() for strategy in self.strategies]
        results = await asyncio.gather(*initialization_tasks, return_exceptions=True)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to initialize strategy '{self.strategies[i].strategy_name}': {result}")
        logger.info("Strategies initialization attempt complete.")


    async def _process_signals(self, signals: List[TradingSignal]):
        if not signals:
            return
        if not self.context.exchange_adapter:
            logger.error("No exchange adapter available. Cannot process signals.")
            return

        for signal in signals:
            logger.info(f"Processing signal: {signal.strategy_name} - {signal.action} {signal.symbol} @ {signal.price if signal.price else 'Market'}")
            
            if signal.action == OrderAction.HOLD:
                logger.info(f"Signal is HOLD for {signal.symbol} from {signal.strategy_name}. No action taken.")
                continue

            # --- Convert TradingSignal to OrderRequest ---
            # This section needs careful mapping of signal intent to order parameters
            
            base_currency, quote_currency = signal.symbol.split('/')
            
            # Fetch current portfolio state from adapter to make decisions
            # This is crucial for real exchanges to have up-to-date balances
            try:
                current_portfolio = await self.context.exchange_adapter.get_account_balance()
                self.portfolio = current_portfolio # Update agent's view
            except Exception as e:
                logger.error(f"Failed to fetch account balance before processing signal for {signal.symbol}: {e}. Skipping signal.")
                continue

            available_quote_balance = current_portfolio.cash_balance.get(quote_currency, 0.0)
            available_base_balance = current_portfolio.asset_holdings.get(base_currency, 0.0)

            # Determine quantity for the order
            order_quantity_base: Optional[float] = None
            target_price: Optional[float] = signal.price # Use signal's price for LIMIT, or for market estimation

            if signal.action == OrderAction.BUY:
                if signal.quantity_absolute:
                    order_quantity_base = signal.quantity_absolute
                elif signal.quantity_percentage:
                    if not target_price: # For market orders, need a price to estimate quantity
                        # Fetch current price from market data source OR exchange adapter
                        # For simplicity, let's try adapter first
                        fetched_price = self.context.exchange_adapter.get_current_price(signal.symbol)
                        if not fetched_price and self.context.market_data_source: # Fallback to market data source
                            try:
                                ticker = self.context.market_data_source.fetch_ticker(signal.symbol)
                                fetched_price = ticker.last if ticker else None
                            except Exception as e_mds:
                                logger.warning(f"Could not fetch ticker via market_data_source for {signal.symbol}: {e_mds}")
                        
                        if not fetched_price:
                            logger.error(f"Cannot determine price for market BUY quantity calculation for {signal.symbol}. Skipping signal.")
                            continue
                        target_price = fetched_price # Use this for calculation
                    
                    spend_amount_quote = available_quote_balance * signal.quantity_percentage
                    if target_price > 0: # Ensure price is positive
                         order_quantity_base = spend_amount_quote / target_price
                    else:
                        logger.error(f"Invalid target price ({target_price}) for BUY quantity calculation {signal.symbol}. Skipping.")
                        continue
                else:
                    logger.warning(f"BUY signal for {signal.symbol} from {signal.strategy_name} has insufficient quantity information.")
                    continue
            
            elif signal.action == OrderAction.SELL:
                if signal.quantity_absolute:
                    order_quantity_base = signal.quantity_absolute
                elif signal.quantity_percentage: # Percentage of available base asset to sell
                    order_quantity_base = available_base_balance * signal.quantity_percentage
                else:
                    logger.warning(f"SELL signal for {signal.symbol} from {signal.strategy_name} has insufficient quantity information.")
                    continue
            
            if order_quantity_base is None or order_quantity_base <= 1e-9: # Check for valid quantity (e.g. min trade size)
                logger.warning(f"Invalid or zero order quantity ({order_quantity_base}) calculated for {signal.symbol} from {signal.strategy_name}. Skipping.")
                continue

            # Determine OrderType: For now, assume market if price is None on signal, else limit.
            # This logic can be refined based on signal properties.
            order_type_to_place = OrderType.MARKET
            if signal.price is not None: # If strategy specified a price, assume it's a limit order.
                order_type_to_place = OrderType.LIMIT
                # For LIMIT BUY, target_price is signal.price. For LIMIT SELL, target_price is signal.price.
            
            order_req = OrderRequest(
                symbol=signal.symbol,
                action=signal.action,
                order_type=order_type_to_place,
                quantity=order_quantity_base,
                price=target_price if order_type_to_place == OrderType.LIMIT else None, # Only set price for LIMIT
                strategy_name=signal.strategy_name,
                # client_order_id can be generated here or by strategy if needed
            )

            logger.info(f"Attempting to place order: {order_req.model_dump_json(indent=2)}")
            try:
                executed_order: ExecutedOrder = await self.context.exchange_adapter.create_order(order_req)
                logger.info(f"Order execution result for {signal.strategy_name} ({signal.symbol}): {executed_order.status}, ID: {executed_order.order_id}")

                # Update agent's portfolio view based on the adapter's state AFTER the trade
                # This is important as the adapter is the source of truth for balances.
                self.portfolio = await self.context.exchange_adapter.get_account_balance()
                logger.info(f"Portfolio after order attempt for {signal.symbol}: {self.portfolio.model_dump_json(indent=2)}")

                # Notify the originating strategy about the executed/attempted order
                for strat in self.strategies:
                    if strat.strategy_name == signal.strategy_name:
                        await strat.on_order_update(executed_order) # Pass the full ExecutedOrder
                        break
            
            except InsufficientFundsError as e:
                logger.error(f"Order placement failed for {signal.strategy_name} ({signal.symbol}): Insufficient funds. {e}")
            except OrderPlacementError as e:
                logger.error(f"Order placement failed for {signal.strategy_name} ({signal.symbol}): {e}")
            except ExchangeAdapterError as e:
                logger.error(f"Exchange adapter error for {signal.strategy_name} ({signal.symbol}): {e}")
            except Exception as e:
                logger.error(f"Unexpected error during order placement for {signal.strategy_name} ({signal.symbol}): {e}", exc_info=True)

    async def _run_cycle(self):
        logger.info("Starting new trading cycle...")
        
        # Update market prices for MockExchangeAdapter if it's being used
        # This is a bit of a hack; ideally, mock prices are updated by a separate simulator process or from market data
        if self.context.exchange_adapter and isinstance(self.context.exchange_adapter, MockExchangeAdapter):
            if self.context.market_data_source:
                # Example: update mock prices for symbols strategies might be interested in.
                # This needs to be more robust, e.g. get all symbols from strategy configs.
                symbols_to_update = set()
                for strat_cfg in self.config.strategies:
                    # This is a naive way to get symbols, strategies might handle various symbols.
                    # A better way would be for strategies to declare symbols they watch.
                    sym = strat_cfg.parameters.get("symbol") # For MA Crossover
                    if sym: symbols_to_update.add(sym)
                    target_syms = strat_cfg.parameters.get("target_symbols") # For Sentiment Strategy
                    quote_curr = strat_cfg.parameters.get("quote_currency", "USDT")
                    if target_syms:
                        for ts in target_syms: symbols_to_update.add(f"{ts}/{quote_curr}")
                
                for sym in list(symbols_to_update): # list() to avoid issues if set changes
                    try:
                        ticker = self.context.market_data_source.fetch_ticker(sym)
                        if ticker and ticker.last:
                            self.context.exchange_adapter.update_price(sym, ticker.last)
                    except Exception as e:
                        logger.warning(f"Could not fetch/update mock price for {sym}: {e}")


        current_market_snapshot = None # Strategies will use context.market_data_source directly

        all_signals: List[TradingSignal] = []
        # Fetch current portfolio state once per cycle for strategies
        try:
            # Portfolio state for strategies to use in signal generation
            portfolio_for_strategies = await self.context.exchange_adapter.get_account_balance() if self.context.exchange_adapter else self.portfolio
        except Exception as e:
            logger.error(f"Failed to get account balance for strategies: {e}. Using last known portfolio state.")
            portfolio_for_strategies = self.portfolio


        for strategy in self.strategies:
            # ... (signal generation logic remains the same, passing portfolio_for_strategies) ...
            try:
                if not strategy.is_initialized:
                    logger.warning(f"Strategy {strategy.strategy_name} is not initialized, skipping signal generation.")
                    continue
                
                logger.debug(f"Generating signals for strategy: {strategy.strategy_name}")
                strategy_signals = await strategy.generate_signals(
                    portfolio=portfolio_for_strategies # Pass the fetched portfolio
                )
                if strategy_signals:
                    all_signals.extend(strategy_signals)
                logger.debug(f"Strategy {strategy.strategy_name} generated {len(strategy_signals)} signals.")
            except Exception as e:
                logger.error(f"Error generating signals from strategy {strategy.strategy_name}: {e}", exc_info=True)

        if all_signals:
            logger.info(f"Total signals generated in this cycle: {len(all_signals)}")
            await self._process_signals(all_signals)
        else:
            logger.info("No trading signals generated in this cycle.")

        final_portfolio_state = await self.context.exchange_adapter.get_account_balance() if self.context.exchange_adapter else self.portfolio
        logger.info(f"End of trading cycle. Current Portfolio: {final_portfolio_state.model_dump_json(indent=2)}")


    async def start(self):
        if not self.strategies:
            logger.error("No strategies loaded. Agent cannot start.")
            return
        if not self.context.exchange_adapter:
            logger.error("No ExchangeAdapter configured. Agent cannot start trading operations.")
            # Depending on requirements, you might allow starting without an adapter for data collection only.
            # For now, we assume trading is a core function.
            return

        await self.initialize_components() # Initializes strategies AND exchange adapter

        self.is_running = True
        logger.info(f"Trading Agent started. Trading interval: {self.config.agent_settings.trading_interval_seconds} seconds.")
        # Initial portfolio log is now part of initialize_components

        try:
            while self.is_running:
                await self._run_cycle()
                await asyncio.sleep(self.config.agent_settings.trading_interval_seconds)
        # ... (exception handling and stop logic remains similar) ...
        except asyncio.CancelledError:
            logger.info("Trading agent task cancelled.")
        except Exception as e:
            logger.error(f"Critical error in Trading Agent main loop: {e}", exc_info=True)
        finally:
            await self.stop()


    async def stop(self):
        self.is_running = False
        logger.info("Stopping Trading Agent...")
        
        strategy_shutdown_tasks = [strategy.shutdown() for strategy in self.strategies]
        await asyncio.gather(*strategy_shutdown_tasks, return_exceptions=True)
        logger.info("All strategies shut down.")

        if self.context.exchange_adapter:
            try:
                await self.context.exchange_adapter.shutdown()
                logger.info("Exchange adapter shut down successfully.")
            except Exception as e:
                logger.error(f"Error shutting down exchange adapter: {e}")
        
        logger.info("Trading Agent stopped.")
        # Log final portfolio state if possible
        try:
            if self.context.exchange_adapter:
                 final_portfolio = await self.context.exchange_adapter.get_account_balance()
                 logger.info(f"Final Portfolio state: {final_portfolio.model_dump_json(indent=2)}")
            else:
                 logger.info(f"Final Portfolio state (local view): {self.portfolio.model_dump_json(indent=2)}")
        except Exception as e:
            logger.error(f"Could not fetch final portfolio state: {e}")


    def get_status(self) -> Dict[str, Any]:
        # Fetch portfolio from adapter for current status
        portfolio_status = self.portfolio.model_dump() # Default to last known
        if self.context.exchange_adapter and self.is_running : # Only try to fetch if running and adapter exists
            # This should ideally be async or handled carefully in a sync method
            # For simplicity, not making get_status async now. Could cache last fetched.
            # portfolio_status = asyncio.run(self.context.exchange_adapter.get_account_balance()).model_dump() # Careful with asyncio.run here
            logger.warning("get_status portfolio fetch from adapter is simplified; consider async or cached value.")


        return {
            "is_running": self.is_running,
            "portfolio": portfolio_status,
            "agent_settings": self.config.agent_settings.model_dump(),
            "exchange_adapter_type": self.context.exchange_adapter.__class__.__name__ if self.context.exchange_adapter else "None",
            "strategies": [strat.get_status() for strat in self.strategies]
        }