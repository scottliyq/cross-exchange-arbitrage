"""Main arbitrage trading bot for GRVT and Aster exchanges."""
import asyncio
import signal
import logging
import os
import sys
import time
import traceback
import aiohttp
from decimal import Decimal
from typing import Tuple, Dict, Any

from .data_logger import DataLogger
from .order_book_manager import OrderBookManager
from .websocket_manager import WebSocketManagerWrapper
from .order_manager import OrderManager
from .position_tracker import PositionTracker

from exchanges.grvt import GrvtClient
from exchanges.aster import AsterClient
from helpers.pushover_bot import PushoverBot


class Config:
    """Simple config class to wrap configuration dictionary."""
    def __init__(self, config_dict):
        for key, value in config_dict.items():
            setattr(self, key, value)


class GrvtArb:
    """Arbitrage trading bot: makes post-only orders on GRVT, and market orders on Aster."""

    def __init__(self, ticker: str, order_quantity: Decimal,
                 fill_timeout: int = 5, max_position: Decimal = Decimal('0'),
                 long_grvt_threshold: Decimal = Decimal('10'),
                 short_grvt_threshold: Decimal = Decimal('10'),
                 z_score_multiplier: float = 1.5):
        """Initialize the arbitrage trading bot."""
        self.ticker = ticker
        self.order_quantity = order_quantity
        self.fill_timeout = fill_timeout
        self.max_position = max_position
        self.stop_flag = False
        self._cleanup_done = False

        # Static thresholds (used as minimum values)
        self.min_long_grvt_threshold = long_grvt_threshold
        self.min_short_grvt_threshold = short_grvt_threshold
        
        # Dynamic thresholds (updated by threshold calculation coroutine)
        self.long_grvt_threshold = long_grvt_threshold
        self.short_grvt_threshold = short_grvt_threshold

        # Spread statistics tracking - separate histories for long and short
        self.long_spread_history = []  # Store historical long spreads (Aster bid - GRVT bid)
        self.short_spread_history = []  # Store historical short spreads (GRVT ask - Aster ask)
        self.spread_window_size = 100  # Number of spreads to keep for MA/STD calculation
        
        # self.z_score_multiplier = 1.5  # 激进：更多交易机会
        # self.z_score_multiplier = 2.0  # 中性：平衡（当前默认）
        # self.z_score_multiplier = 2.5  # 保守：只捕捉大机会
        # Dynamic threshold calculation parameters
        self.z_score_multiplier = z_score_multiplier  # Z-score threshold for dynamic calculation
        self.threshold_update_interval = 5.0  # Update thresholds every N seconds
        self.min_samples_for_dynamic = 50  # Minimum samples before using dynamic thresholds
        self.threshold_calculation_task = None  # Task for threshold calculation coroutine

        # Setup logger
        self._setup_logger()
        
        # Pushover bot for notifications
        self.pushover_bot = PushoverBot(logger=self.logger)

        # Initialize modules
        self.data_logger = DataLogger(exchange="grvt", ticker=ticker, logger=self.logger)
        self.order_book_manager = OrderBookManager(self.logger)
        self.ws_manager = WebSocketManagerWrapper(self.order_book_manager, self.logger)
        self.order_manager = OrderManager(self.order_book_manager, self.logger)

        # Initialize clients (will be set later)
        self.grvt_client = None
        self.aster_client = None

        # Contract/market info (will be set during initialization)
        self.grvt_contract_id = None
        self.grvt_tick_size = None
        self.aster_contract_id = None
        self.aster_tick_size = None

        # Position tracker (will be initialized after clients)
        self.position_tracker = None

        # Setup callbacks
        self._setup_callbacks()

    def _setup_logger(self):
        """Setup logging configuration."""
        os.makedirs("logs", exist_ok=True)
        self.log_filename = f"logs/grvt_{self.ticker}_log.txt"

        self.logger = logging.getLogger(f"arbitrage_bot_{self.ticker}")
        self.logger.setLevel(logging.INFO)
        self.logger.handlers.clear()

        # Disable verbose logging from external libraries
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
        logging.getLogger('websockets').setLevel(logging.WARNING)
        logging.getLogger('aiohttp').setLevel(logging.WARNING)
        
        # Suppress GRVT SDK WebSocket connection errors (we handle reconnection ourselves)
        logging.getLogger('pysdk.grvt_ccxt_logging_selector').setLevel(logging.CRITICAL)
        logging.getLogger('pysdk.grvt_ccxt_ws').setLevel(logging.WARNING)

        # Create file handler
        file_handler = logging.FileHandler(self.log_filename)
        file_handler.setLevel(logging.INFO)

        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)

        # Create formatters with timestamp and line number
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%H:%M:%S'
        )

        file_handler.setFormatter(file_formatter)
        console_handler.setFormatter(console_formatter)

        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        self.logger.propagate = False

    def _setup_callbacks(self):
        """Setup callback functions for order updates."""
        self.ws_manager.set_callbacks(
            on_grvt_order_update=self._handle_grvt_order_update
        )
        self.order_manager.set_callbacks(
            on_order_filled=self._handle_aster_order_filled
        )

    def update_spread_statistics(self, long_spread: Decimal = None, short_spread: Decimal = None):
        """Update spread history with new spread value.
        
        Only positive spreads (arbitrage opportunities) are recorded for statistical analysis.
        This ensures thresholds are calculated based on actual profitable spread patterns.
        
        Args:
            long_spread: Spread for long GRVT (Aster bid - GRVT bid)
            short_spread: Spread for short GRVT (GRVT ask - Aster ask)
        """
        # Update long spread history - only record positive spreads
        if long_spread is not None and long_spread > 0:
            self.long_spread_history.append(float(long_spread))
            # Keep only the most recent spreads within window size
            if len(self.long_spread_history) > self.spread_window_size:
                self.long_spread_history.pop(0)
        
        # Update short spread history - only record positive spreads
        if short_spread is not None and short_spread > 0:
            self.short_spread_history.append(float(short_spread))
            # Keep only the most recent spreads within window size
            if len(self.short_spread_history) > self.spread_window_size:
                self.short_spread_history.pop(0)

    def get_spread_statistics(self, spread_history: list, window: int = None) -> Dict[str, float]:
        """Get comprehensive spread statistics for a given spread history.
        
        Args:
            spread_history: List of spread values to calculate statistics from
            window: Number of recent spreads to include. If None, uses all available spreads.
        
        Returns:
            Dictionary containing:
                - 'moving_average': Moving average of spread
                - 'rolling_std': Rolling standard deviation
                - 'count': Number of spreads in calculation
                - 'min': Minimum spread in window
                - 'max': Maximum spread in window
        """
        if not spread_history:
            return {
                'moving_average': 0.0,
                'rolling_std': 0.0,
                'count': 0,
                'min': 0.0,
                'max': 0.0
            }
        
        # Use specified window or all available data
        if window is None:
            window = len(spread_history)
        
        recent_spreads = spread_history[-min(window, len(spread_history)):]
        
        if not recent_spreads:
            return {
                'moving_average': 0.0,
                'rolling_std': 0.0,
                'count': 0,
                'min': 0.0,
                'max': 0.0
            }
        
        # Calculate mean
        mean = sum(recent_spreads) / len(recent_spreads)
        
        # Calculate standard deviation
        if len(recent_spreads) >= 2:
            variance = sum((x - mean) ** 2 for x in recent_spreads) / len(recent_spreads)
            std = variance ** 0.5
        else:
            std = 0.0
        
        return {
            'moving_average': mean,
            'rolling_std': std,
            'count': len(recent_spreads),
            'min': min(recent_spreads),
            'max': max(recent_spreads)
        }

    def calculate_dynamic_threshold(self, spread_history: list, min_threshold: float) -> float:
        """Calculate dynamic threshold based on Z-score method.
        
        Args:
            spread_history: List of spread values to calculate threshold from
            min_threshold: Minimum threshold value (from config)
        
        Returns:
            Dynamic threshold = max(min_threshold, MA + z_score_multiplier * STD)
            Always returns a positive value.
        """
        if len(spread_history) < self.min_samples_for_dynamic:
            # Not enough data, use minimum threshold
            return min_threshold
        
        stats = self.get_spread_statistics(spread_history)
        
        # Calculate dynamic threshold using Z-score method
        statistical_threshold = stats['moving_average'] + self.z_score_multiplier * stats['rolling_std']
        
        # Ensure threshold is always positive
        # Use the maximum of min_threshold and statistical_threshold
        dynamic_threshold = max(min_threshold, statistical_threshold, 0.1)
        
        return dynamic_threshold

    async def _threshold_calculation_loop(self):
        """Independent coroutine for calculating dynamic thresholds and logging spread statistics."""
        self.logger.info(f"📊 Starting dynamic threshold calculation coroutine (update interval: {self.threshold_update_interval}s)")
        
        while not self.stop_flag:
            try:
                # Get long spread statistics
                long_stats = self.get_spread_statistics(self.long_spread_history)
                
                # Log long spread statistics to CSV if we have data
                if long_stats['count'] > 0:
                    recent_long_spread = self.long_spread_history[-1] if self.long_spread_history else 0.0
                    
                    self.data_logger.log_spread_stats_to_csv(
                        spread=recent_long_spread,
                        spread_type='long',
                        moving_average=long_stats['moving_average'],
                        rolling_std=long_stats['rolling_std'],
                        count=long_stats['count'],
                        min_spread=long_stats['min'],
                        max_spread=long_stats['max']
                    )
                    
                    self.logger.debug(
                        f"📊 LONG spread stats logged: count={long_stats['count']}, "
                        f"MA={long_stats['moving_average']:.2f}, STD={long_stats['rolling_std']:.2f}")
                else:
                    self.logger.debug(f"⏳ Waiting for LONG spread data (history size: {len(self.long_spread_history)})")
                
                # Get short spread statistics
                short_stats = self.get_spread_statistics(self.short_spread_history)
                
                # Log short spread statistics to CSV if we have data
                if short_stats['count'] > 0:
                    recent_short_spread = self.short_spread_history[-1] if self.short_spread_history else 0.0
                    
                    self.data_logger.log_spread_stats_to_csv(
                        spread=recent_short_spread,
                        spread_type='short',
                        moving_average=short_stats['moving_average'],
                        rolling_std=short_stats['rolling_std'],
                        count=short_stats['count'],
                        min_spread=short_stats['min'],
                        max_spread=short_stats['max']
                    )
                    
                    self.logger.debug(
                        f"📊 SHORT spread stats logged: count={short_stats['count']}, "
                        f"MA={short_stats['moving_average']:.2f}, STD={short_stats['rolling_std']:.2f}")
                else:
                    self.logger.debug(f"⏳ Waiting for SHORT spread data (history size: {len(self.short_spread_history)})")
                
                await asyncio.sleep(self.threshold_update_interval)
                
                if self.stop_flag:
                    break
                
                # Calculate dynamic thresholds using respective spread histories
                new_long_threshold = self.calculate_dynamic_threshold(
                    self.long_spread_history, float(self.min_long_grvt_threshold))
                new_short_threshold = self.calculate_dynamic_threshold(
                    self.short_spread_history, float(self.min_short_grvt_threshold))
                
                # Update thresholds if they changed significantly
                if abs(new_long_threshold - float(self.long_grvt_threshold)) > 0.1:
                    old_value = self.long_grvt_threshold
                    self.long_grvt_threshold = Decimal(str(new_long_threshold))
                    self.logger.info(
                        f"📈 Dynamic LONG threshold updated: {old_value:.2f} → {new_long_threshold:.2f} "
                        f"(samples: {len(self.long_spread_history)})")
                
                if abs(new_short_threshold - float(self.short_grvt_threshold)) > 0.1:
                    old_value = self.short_grvt_threshold
                    self.short_grvt_threshold = Decimal(str(new_short_threshold))
                    self.logger.info(
                        f"📉 Dynamic SHORT threshold updated: {old_value:.2f} → {new_short_threshold:.2f} "
                        f"(samples: {len(self.short_spread_history)})")
                
            except asyncio.CancelledError:
                self.logger.info("🔌 Threshold calculation coroutine cancelled")
                break
            except Exception as e:
                if not self.stop_flag:
                    self.logger.error(f"⚠️ Error in threshold calculation loop: {e}")
                    self.logger.error(traceback.format_exc())
                await asyncio.sleep(self.threshold_update_interval)

    def start_threshold_calculation(self):
        """Start the threshold calculation coroutine."""
        if self.threshold_calculation_task is None or self.threshold_calculation_task.done():
            self.threshold_calculation_task = asyncio.create_task(self._threshold_calculation_loop())
            self.logger.info("✅ Threshold calculation coroutine started")

    def _handle_aster_order_filled(self, order_data: dict):
        """Handle Aster order fill."""
        try:
            side = order_data.get("side", "") 
            filled_amount = order_data.get("filled_base_amount", 0)
            avg_price = order_data.get("avg_filled_price", 0)
            
            if side == "SHORT":
                order_type = "OPEN"
                if self.position_tracker:
                    self.position_tracker.update_aster_position(-Decimal(filled_amount))
            else:
                order_type = "CLOSE"
                if self.position_tracker:
                    self.position_tracker.update_aster_position(Decimal(filled_amount))

            order_id = order_data.get("order_id", "")
            self.logger.info(
                f"[{order_id}] [{order_type}] [Aster] [FILLED]: "
                f"{filled_amount} @ {avg_price}")

            # Log trade to CSV
            self.data_logger.log_trade_to_csv(
                exchange='aster',
                side=side,
                price=str(avg_price),
                quantity=str(filled_amount)
            )

            # Mark execution as complete
            self.order_manager.aster_order_filled = True
            self.order_manager.order_execution_complete = True

        except Exception as e:
            self.logger.error(f"Error handling Aster order result: {e}")

    def _handle_grvt_order_update(self, order: dict):
        """Handle GRVT order update from WebSocket."""
        try:
            if order.get('contract_id') != self.grvt_contract_id:
                return

            order_id = order.get('order_id')
            status = order.get('status')
            side = order.get('side', '').lower()
            filled_size = Decimal(order.get('filled_size', '0'))
            size = Decimal(order.get('size', '0'))
            price = order.get('price', '0')

            if side == 'buy':
                order_type = "OPEN"
            else:
                order_type = "CLOSE"

            # Handle partially filled or fully filled orders that were canceled
            if status == 'CANCELED' and filled_size > 0:
                status = 'FILLED'

            # Update order status
            if status:
                self.order_manager.update_grvt_order_status(status)

            # Handle filled orders
            if status == 'FILLED' and filled_size > 0:
                if side == 'buy':
                    if self.position_tracker:
                        self.position_tracker.update_grvt_position(filled_size)
                else:
                    if self.position_tracker:
                        self.position_tracker.update_grvt_position(-filled_size)

                self.logger.info(
                    f"[{order_id}] [{order_type}] [GRVT] [{status}]: {filled_size} @ {price}")

                if filled_size > Decimal('0.0001'):
                    # Log GRVT trade to CSV
                    self.data_logger.log_trade_to_csv(
                        exchange='GRVT',
                        side=side,
                        price=str(price),
                        quantity=str(filled_size)
                    )

                # Trigger Aster order placement
                self.order_manager.handle_grvt_order_update({
                    'order_id': order_id,
                    'side': side,
                    'status': status,
                    'size': size,
                    'price': price,
                    'contract_id': self.grvt_contract_id,
                    'filled_size': filled_size
                })
            elif status != 'FILLED':
                if status == 'OPEN':
                    self.logger.info(f"[{order_id}] [{order_type}] [GRVT] [{status}]: {size} @ {price}")
                else:
                    self.logger.info(
                        f"[{order_id}] [{order_type}] [GRVT] [{status}]: {filled_size} @ {price}")

        except Exception as e:
            self.logger.error(f"Error handling GRVT order update: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")



    def shutdown(self, signum=None, frame=None):
        """Graceful shutdown handler."""
        # Prevent multiple shutdown calls
        if self.stop_flag:
            return

        self.stop_flag = True

        if signum is not None:
            self.logger.info("\n🛑 Stopping...")
        else:
            self.logger.info("🛑 Stopping...")

        # Close data logger
        try:
            if self.data_logger:
                self.data_logger.close()
        except Exception as e:
            self.logger.error(f"Error closing data logger: {e}")

        # Close logging handlers
        for handler in self.logger.handlers[:]:
            try:
                handler.close()
                self.logger.removeHandler(handler)
            except Exception:
                pass

    async def _async_cleanup(self):
        """Async cleanup for clients and other async resources."""
        if self._cleanup_done:
            return

        self._cleanup_done = True

        # Cancel threshold calculation task
        if self.threshold_calculation_task and not self.threshold_calculation_task.done():
            try:
                self.threshold_calculation_task.cancel()
                await asyncio.wait_for(self.threshold_calculation_task, timeout=2.0)
                self.logger.info("🔌 Threshold calculation task cancelled")
            except asyncio.TimeoutError:
                self.logger.warning("⚠️ Timeout cancelling threshold calculation task")
            except Exception as e:
                self.logger.error(f"Error cancelling threshold calculation task: {e}")

        # Shutdown WebSocket manager
        try:
            if self.ws_manager:
                self.ws_manager.shutdown()
                self.logger.info("🔌 WebSocket manager shut down")
        except Exception as e:
            self.logger.error(f"Error shutting down WebSocket manager: {e}")

        # Disconnect GRVT client
        try:
            if self.grvt_client:
                await asyncio.wait_for(
                    self.grvt_client.disconnect(),
                    timeout=2.0
                )
                self.logger.info("🔌 GRVT client disconnected")
        except asyncio.TimeoutError:
            self.logger.warning("⚠️ Timeout disconnecting GRVT client, forcing shutdown")
        except Exception as e:
            self.logger.error(f"Error disconnecting GRVT client: {e}")

        # Disconnect Aster client
        try:
            if self.aster_client:
                await asyncio.wait_for(
                    self.aster_client.disconnect(),
                    timeout=2.0
                )
                self.logger.info("🔌 Aster client disconnected")
        except asyncio.TimeoutError:
            self.logger.warning("⚠️ Timeout disconnecting Aster client, forcing shutdown")
        except Exception as e:
            self.logger.error(f"Error disconnecting Aster client: {e}")

    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

    def initialize_grvt_client(self):
        """Initialize the GRVT client."""
        if self.grvt_client is None:
            config = Config({
                'ticker': self.ticker,
                'quantity': self.order_quantity
            })
            self.grvt_client = GrvtClient(config.__dict__)
            self.logger.info("✅ GRVT client initialized successfully")
        return self.grvt_client

    def initialize_aster_client(self):
        """Initialize the Aster client."""
        if self.aster_client is None:
            config = Config({
                'ticker': self.ticker,
                'quantity': self.order_quantity
            })
            self.aster_client = AsterClient(config.__dict__)
            self.logger.info("✅ Aster client initialized successfully")
        return self.aster_client

    async def get_grvt_contract_info(self) -> Tuple[str, Decimal]:
        """Get GRVT contract ID and tick size."""
        if not self.grvt_client:
            raise Exception("GRVT client not initialized")

        contract_id, tick_size = await self.grvt_client.get_contract_attributes()
        
        if not contract_id or tick_size <= 0:
            raise ValueError(f"Failed to get contract info for ticker {self.ticker}")

        self.logger.info(f"GRVT contract: {contract_id}, tick size: {tick_size}")
        return contract_id, tick_size

    async def get_aster_contract_info(self) -> Tuple[str, Decimal]:
        """Get Aster contract ID and tick size."""
        if not self.aster_client:
            raise Exception("Aster client not initialized")

        contract_id, tick_size = await self.aster_client.get_contract_attributes()
        
        if not contract_id or tick_size <= 0:
            raise ValueError(f"Failed to get contract info for ticker {self.ticker}")

        self.logger.info(f"Aster contract: {contract_id}, tick size: {tick_size}")
        return contract_id, tick_size

    async def trading_loop(self):
        """Main trading loop implementing the strategy."""
        self.logger.info(f"🚀 Starting arbitrage bot for {self.ticker}")

        # Initialize clients
        try:
            self.initialize_grvt_client()
            self.initialize_aster_client()

            # Get contract info
            self.grvt_contract_id, self.grvt_tick_size = await self.get_grvt_contract_info()
            self.aster_contract_id, self.aster_tick_size = await self.get_aster_contract_info()

            self.logger.info(
                f"Contract info loaded - GRVT: {self.grvt_contract_id}, "
                f"Aster: {self.aster_contract_id}")

        except Exception as e:
            self.logger.error(f"❌ Failed to initialize: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return

        # Initialize position tracker
        if not self.grvt_client or not self.aster_client:
            raise Exception("Clients not properly initialized")
            
        self.position_tracker = PositionTracker(
            self.ticker,
            self.grvt_client,
            self.aster_client,
            self.logger
        )

        # Configure modules
        if not self.grvt_client or not self.aster_client:
            raise Exception("Clients not properly initialized")
            
        self.order_manager.set_grvt_config(
            self.grvt_client, self.grvt_contract_id, self.grvt_tick_size)
        self.order_manager.set_aster_config(
            self.aster_client, self.aster_contract_id, self.aster_tick_size)

        # Configure WebSocket manager
        self.ws_manager.set_grvt_config(self.grvt_client, self.grvt_contract_id)
        self.ws_manager.set_aster_config(self.aster_client, self.aster_contract_id)

        # Connect to GRVT and setup WebSocket for order book
        try:
            # Connect GRVT client
            await self.grvt_client.connect()
            self.logger.info("✅ GRVT client connected")
            
            # Setup GRVT order update handler
            self.grvt_client.setup_order_update_handler(self._handle_grvt_order_update)
            self.logger.info("✅ GRVT order update handler setup")
            
            # Setup GRVT WebSocket for order book updates
            self.logger.info("📡 Setting up GRVT WebSocket for order book...")
            await self.ws_manager.setup_grvt_websocket()

        except Exception as e:
            self.logger.error(f"❌ Failed to connect to GRVT: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return

        # Setup Aster websocket
        try:
            await self.ws_manager.setup_aster_websocket()
            self.logger.info("✅ Aster WebSocket task started")

            # Wait for both order books to be ready
            self.logger.info("⏳ Waiting for order book data...")
            timeout = 15
            start_time = time.time()
            while (not self.order_book_manager.aster_order_book_ready or 
                   not self.order_book_manager.grvt_order_book_ready) and not self.stop_flag:
                if time.time() - start_time > timeout:
                    self.logger.warning(
                        f"⚠️ Timeout waiting for order book data after {timeout}s")
                    self.logger.warning(
                        f"Status - GRVT ready: {self.order_book_manager.grvt_order_book_ready}, "
                        f"Aster ready: {self.order_book_manager.aster_order_book_ready}")
                    break
                await asyncio.sleep(0.5)

            if self.order_book_manager.grvt_order_book_ready and self.order_book_manager.aster_order_book_ready:
                self.logger.info("✅ Both order books ready")
            else:
                self.logger.warning("⚠️ Order books not ready - proceeding with available data")

        except Exception as e:
            self.logger.error(f"❌ Failed to setup Aster websocket: {e}")
            return

        # Connect Aster client for orders
        await self.aster_client.connect()
        self.logger.info("✅ Aster client connected")

        await asyncio.sleep(3)

        # Get initial positions
        try:
            if not self.position_tracker:
                raise Exception("Position tracker not initialized")
                
            self.position_tracker.grvt_position = await self.position_tracker.get_grvt_position()
            self.position_tracker.aster_position = await self.position_tracker.get_aster_position()
            self.logger.info(
                f"Initial positions - GRVT: {self.position_tracker.grvt_position}, "
                f"Aster: {self.position_tracker.aster_position}")
        except Exception as e:
            self.logger.error(f"❌ Failed to get initial positions: {e}")
            return

        # Start dynamic threshold calculation coroutine
        self.start_threshold_calculation()
        self.logger.info(
            f"📊 Dynamic threshold enabled: z_score={self.z_score_multiplier}, "
            f"min_samples={self.min_samples_for_dynamic}, "
            f"min_long={self.min_long_grvt_threshold}, min_short={self.min_short_grvt_threshold}")

        # Main trading loop
        while not self.stop_flag:
            try:
                # await asyncio.sleep(1)
                
                # Get BBO from order book manager (WebSocket data)
                grvt_best_bid, grvt_best_ask = self.order_book_manager.get_grvt_bbo()
                aster_best_bid, aster_best_ask = self.order_book_manager.get_aster_bbo()

                # Check if we have valid order book data
                if not grvt_best_bid or not grvt_best_ask:
                    self.logger.debug("⚠️ GRVT order book not ready")
                    await asyncio.sleep(0.5)
                    continue

                if not aster_best_bid or not aster_best_ask:
                    self.logger.debug("⚠️ Aster order book not ready")
                    await asyncio.sleep(0.5)
                    continue

                long_grvt = False
                short_grvt = False
                
                # Update spread statistics for coroutine to use (no logging here)
                if aster_best_bid and grvt_best_bid:
                    long_spread = aster_best_bid - grvt_best_bid
                    self.update_spread_statistics(long_spread=Decimal(str(long_spread)))
                    
                if grvt_best_ask and aster_best_ask:
                    short_spread = grvt_best_ask - aster_best_ask
                    self.update_spread_statistics(short_spread=Decimal(str(short_spread)))
                                
                # Check for trading signals (log to main log only when signal triggered)
                if (aster_best_bid and grvt_best_bid and
                        aster_best_bid - grvt_best_bid > self.long_grvt_threshold):
                    long_grvt = True
                    self.logger.info(
                        f"🟢 LONG GRVT Signal | "
                        f"Aster Bid: {aster_best_bid:.2f} | GRVT Bid: {grvt_best_bid:.2f} | "
                        f"Threshold: {self.long_grvt_threshold}")
                    
                elif (grvt_best_ask and aster_best_ask and
                      grvt_best_ask - aster_best_ask > self.short_grvt_threshold):
                    short_grvt = True
                    self.logger.info(
                        f"🔴 SHORT GRVT Signal | "
                        f"GRVT Ask: {grvt_best_ask:.2f} | Aster Ask: {aster_best_ask:.2f} | "
                        f"Threshold: {self.short_grvt_threshold}")

                # Log BBO data (using WebSocket order book data)
                self.data_logger.log_bbo_to_csv(
                    maker_bid=grvt_best_bid,
                    maker_ask=grvt_best_ask,
                    taker_bid=aster_best_bid,
                    taker_ask=aster_best_ask,
                    long_maker=long_grvt,
                    short_maker=short_grvt,
                    long_maker_threshold=self.long_grvt_threshold,
                    short_maker_threshold=self.short_grvt_threshold
                )

                if long_grvt or short_grvt:
                    # Update positions at the beginning of each loop iteration
                    if not await self._update_positions():
                        continue
                    
                    if self.stop_flag:
                        break

                # Execute trades
                if self.position_tracker:
                    if (self.position_tracker.get_current_grvt_position() < self.max_position and
                            long_grvt):
                        await self._execute_long_trade()
                        await asyncio.sleep(2)
                    elif (self.position_tracker.get_current_grvt_position() > -1 * self.max_position and
                          short_grvt):
                        await self._execute_short_trade()
                        await asyncio.sleep(2)
                    else:
                        await asyncio.sleep(0.05)
                else:
                    await asyncio.sleep(0.05)

            except Exception as e:
                if not self.stop_flag:
                    self.logger.error(f"⚠️ Error in main trading loop: {e}")
                    self.logger.error(f"Traceback: {traceback.format_exc()}")
                    await asyncio.sleep(1)

    async def _update_positions(self) -> bool:
        """Update positions from both exchanges.
        
        Returns:
            True if successful, False if failed or stop_flag is set.
        """
        try:
            self.position_tracker.grvt_position = await asyncio.wait_for(
                self.position_tracker.get_grvt_position(),
                timeout=3.0
            )
            if self.stop_flag:
                return False
            self.position_tracker.aster_position = await asyncio.wait_for(
                self.position_tracker.get_aster_position(),
                timeout=3.0
            )
            return True
        except asyncio.TimeoutError:
            if self.stop_flag:
                return False
            self.logger.warning("⚠️ Timeout getting positions")
            return False
        except Exception as e:
            if self.stop_flag:
                return False
            self.logger.error(f"⚠️ Error getting positions: {e}")
            return False

    async def _execute_long_trade(self):
        """Execute a long trade (buy on GRVT, sell on Aster)."""
        if self.stop_flag or not self.position_tracker:
            return

        self.logger.info(
            f"GRVT position: {self.position_tracker.grvt_position} | "
            f"Aster position: {self.position_tracker.aster_position}")

        if abs(self.position_tracker.get_net_position()) > self.order_quantity * 2:
            net_position = self.position_tracker.get_net_position()
            self.logger.error(f"❌ Position diff is too large: {net_position}")
            
            # Send emergency Pushover alert for long trade
            alert_title = f"🚨 {self.ticker} Position Imbalance (LONG)"
            alert_message = (
                f"Position difference exceeded threshold!\n\n"
                f"Net Position: {net_position}\n"
                f"GRVT: {self.position_tracker.grvt_position}\n"
                f"Aster: {self.position_tracker.aster_position}\n"
                f"Threshold: {self.order_quantity * 2}\n\n"
                f"Bot is shutting down."
            )
            await self.pushover_bot.send_alert(alert_title, alert_message, priority=2)
            
            sys.exit(1)

        self.order_manager.order_execution_complete = False
        self.order_manager.waiting_for_aster_fill = False

        try:
            side = 'buy'
            order_filled = await self.order_manager.place_grvt_post_only_order(
                side, self.order_quantity, self.stop_flag)
            if not order_filled or self.stop_flag:
                return
        except Exception as e:
            if self.stop_flag:
                return
            self.logger.error(f"⚠️ Error placing GRVT order: {e}")
            self.logger.error(f"⚠️ Full traceback: {traceback.format_exc()}")
            return

        start_time = time.time()
        while not self.order_manager.order_execution_complete and not self.stop_flag:
            if self.order_manager.waiting_for_aster_fill:
                await self.order_manager.place_aster_market_order(
                    self.order_manager.current_aster_side,
                    self.order_manager.current_aster_quantity,
                    self.order_manager.current_aster_price,
                    self.stop_flag
                )
                break

            await asyncio.sleep(0.01)
            if time.time() - start_time > 180:
                self.logger.error("❌ Timeout waiting for trade completion")
                break

    async def _execute_short_trade(self):
        """Execute a short trade (sell on GRVT, buy on Aster)."""
        if self.stop_flag or not self.position_tracker:
            return

        self.logger.info(
            f"GRVT position: {self.position_tracker.grvt_position} | "
            f"Aster position: {self.position_tracker.aster_position}")

        if abs(self.position_tracker.get_net_position()) > self.order_quantity * 2:
            net_position = self.position_tracker.get_net_position()
            self.logger.error(f"❌ Position diff is too large: {net_position}")
            
            # Send emergency Pushover alert for short trade
            alert_title = f"🚨 {self.ticker} Position Imbalance (SHORT)"
            alert_message = (
                f"Position difference exceeded threshold!\n\n"
                f"Net Position: {net_position}\n"
                f"GRVT: {self.position_tracker.grvt_position}\n"
                f"Aster: {self.position_tracker.aster_position}\n"
                f"Threshold: {self.order_quantity * 2}\n\n"
                f"Bot is shutting down."
            )
            await self.pushover_bot.send_alert(alert_title, alert_message, priority=2)
            
            sys.exit(1)

        self.order_manager.order_execution_complete = False
        self.order_manager.waiting_for_aster_fill = False

        try:
            side = 'sell'
            order_filled = await self.order_manager.place_grvt_post_only_order(
                side, self.order_quantity, self.stop_flag)
            if not order_filled or self.stop_flag:
                return
        except Exception as e:
            if self.stop_flag:
                return
            self.logger.error(f"⚠️ Error placing GRVT order: {e}")
            self.logger.error(f"⚠️ Full traceback: {traceback.format_exc()}")
            return

        start_time = time.time()
        while not self.order_manager.order_execution_complete and not self.stop_flag:
            if self.order_manager.waiting_for_aster_fill:
                if (self.order_manager.current_aster_side and 
                    self.order_manager.current_aster_quantity and 
                    self.order_manager.current_aster_price):
                    await self.order_manager.place_aster_market_order(
                        self.order_manager.current_aster_side,
                        self.order_manager.current_aster_quantity,
                        self.order_manager.current_aster_price,
                        self.stop_flag
                    )
                break

            await asyncio.sleep(0.01)
            if time.time() - start_time > 180:
                self.logger.error("❌ Timeout waiting for trade completion")
                break

    async def run(self):
        """Run the arbitrage bot."""
        self.setup_signal_handlers()

        try:
            await self.trading_loop()
        except KeyboardInterrupt:
            self.logger.info("\n🛑 Received interrupt signal...")
        except asyncio.CancelledError:
            self.logger.info("\n🛑 Task cancelled...")
        finally:
            self.logger.info("🔄 Cleaning up...")
            self.shutdown()
            # Ensure async cleanup is done with timeout
            try:
                await asyncio.wait_for(self._async_cleanup(), timeout=5.0)
            except asyncio.TimeoutError:
                self.logger.warning("⚠️ Cleanup timeout, forcing exit")
            except Exception as e:
                self.logger.error(f"Error during cleanup: {e}")
