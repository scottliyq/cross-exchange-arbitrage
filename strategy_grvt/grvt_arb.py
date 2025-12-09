"""Main arbitrage trading bot for GRVT and Aster exchanges."""
import asyncio
import signal
import logging
import os
import sys
import time
import traceback
from decimal import Decimal
from typing import Tuple, Dict, Any

from .data_logger import DataLogger
from .order_book_manager import OrderBookManager
from .order_manager import OrderManager
from .position_tracker import PositionTracker

from exchanges.grvt import GrvtClient
from exchanges.aster import AsterClient


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
                 short_grvt_threshold: Decimal = Decimal('10')):
        """Initialize the arbitrage trading bot."""
        self.ticker = ticker
        self.order_quantity = order_quantity
        self.fill_timeout = fill_timeout
        self.max_position = max_position
        self.stop_flag = False
        self._cleanup_done = False

        self.long_grvt_threshold = long_grvt_threshold
        self.short_grvt_threshold = short_grvt_threshold

        # Setup logger
        self._setup_logger()

        # Initialize modules
        self.data_logger = DataLogger(exchange="grvt", ticker=ticker, logger=self.logger)
        self.order_book_manager = OrderBookManager(self.logger)
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

        # Create file handler
        file_handler = logging.FileHandler(self.log_filename)
        file_handler.setLevel(logging.INFO)

        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)

        # Create formatters
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')

        file_handler.setFormatter(file_formatter)
        console_handler.setFormatter(console_formatter)

        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        self.logger.propagate = False

    def _setup_callbacks(self):
        """Setup callback functions for order updates."""
        self.order_manager.set_callbacks(
            on_order_filled=self._handle_aster_order_filled
        )

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

        # Connect to exchanges
        try:
            # Connect GRVT client
            await self.grvt_client.connect()
            self.logger.info("✅ GRVT client connected")
            
            # Setup GRVT order update handler
            self.grvt_client.setup_order_update_handler(self._handle_grvt_order_update)
            self.logger.info("✅ GRVT order update handler setup")

            # Connect Aster client
            await self.aster_client.connect()
            self.logger.info("✅ Aster client connected")

            # Wait for connections to stabilize
            await asyncio.sleep(3)

        except Exception as e:
            self.logger.error(f"❌ Failed to connect to exchanges: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return

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

        # Main trading loop
        while not self.stop_flag:
            try:
                # Fetch GRVT BBO prices
                try:
                    grvt_best_bid, grvt_best_ask = await asyncio.wait_for(
                        self.order_manager.fetch_grvt_bbo_prices(),
                        timeout=5.0
                    )
                except asyncio.TimeoutError:
                    self.logger.warning("⚠️ Timeout fetching GRVT BBO prices")
                    await asyncio.sleep(0.5)
                    continue
                except Exception as e:
                    self.logger.error(f"⚠️ Error fetching GRVT BBO prices: {e}")
                    await asyncio.sleep(0.5)
                    continue

                # Fetch Aster BBO prices
                try:
                    if not self.aster_client or not self.aster_contract_id:
                        raise Exception("Aster client not initialized")
                        
                    aster_best_bid, aster_best_ask = await asyncio.wait_for(
                        self.aster_client.fetch_bbo_prices(self.aster_contract_id),
                        timeout=5.0
                    )
                except asyncio.TimeoutError:
                    self.logger.warning("⚠️ Timeout fetching Aster BBO prices")
                    await asyncio.sleep(0.5)
                    continue
                except Exception as e:
                    self.logger.error(f"⚠️ Error fetching Aster BBO prices: {e}")
                    await asyncio.sleep(0.5)
                    continue

                # Determine if we should trade
                long_grvt = False
                short_grvt = False
                
                if (aster_best_bid and grvt_best_bid and
                        aster_best_bid - grvt_best_bid > self.long_grvt_threshold):
                    long_grvt = True
                elif (grvt_best_ask and aster_best_ask and
                      grvt_best_ask - aster_best_ask > self.short_grvt_threshold):
                    short_grvt = True

                # Log BBO data
                self.data_logger.log_bbo_to_csv(
                    maker_bid=grvt_best_bid if grvt_best_bid else Decimal('0'),
                    maker_ask=grvt_best_ask if grvt_best_ask else Decimal('0'),
                    taker_bid=aster_best_bid if aster_best_bid else Decimal('0'),
                    taker_ask=aster_best_ask if aster_best_ask else Decimal('0'),
                    long_maker=long_grvt,
                    short_maker=short_grvt,
                    long_maker_threshold=self.long_grvt_threshold,
                    short_maker_threshold=self.short_grvt_threshold
                )

                if self.stop_flag:
                    break

                # Execute trades
                if self.position_tracker:
                    if (self.position_tracker.get_current_grvt_position() < self.max_position and
                            long_grvt):
                        await self._execute_long_trade()
                    elif (self.position_tracker.get_current_grvt_position() > -1 * self.max_position and
                          short_grvt):
                        await self._execute_short_trade()
                    else:
                        await asyncio.sleep(0.05)
                else:
                    await asyncio.sleep(0.05)

            except Exception as e:
                if not self.stop_flag:
                    self.logger.error(f"⚠️ Error in main trading loop: {e}")
                    self.logger.error(f"Traceback: {traceback.format_exc()}")
                    await asyncio.sleep(1)

    async def _execute_long_trade(self):
        """Execute a long trade (buy on GRVT, sell on Aster)."""
        if self.stop_flag or not self.position_tracker:
            return

        # Update positions
        try:
            self.position_tracker.grvt_position = await asyncio.wait_for(
                self.position_tracker.get_grvt_position(),
                timeout=3.0
            )
            if self.stop_flag:
                return
            self.position_tracker.aster_position = await asyncio.wait_for(
                self.position_tracker.get_aster_position(),
                timeout=3.0
            )
        except asyncio.TimeoutError:
            if self.stop_flag:
                return
            self.logger.warning("⚠️ Timeout getting positions")
            return
        except Exception as e:
            if self.stop_flag:
                return
            self.logger.error(f"⚠️ Error getting positions: {e}")
            return

        if self.stop_flag:
            return

        self.logger.info(
            f"GRVT position: {self.position_tracker.grvt_position} | "
            f"Aster position: {self.position_tracker.aster_position}")

        if abs(self.position_tracker.get_net_position()) > self.order_quantity * 2:
            self.logger.error(
                f"❌ Position diff is too large: {self.position_tracker.get_net_position()}")
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

        # Update positions
        try:
            self.position_tracker.grvt_position = await asyncio.wait_for(
                self.position_tracker.get_grvt_position(),
                timeout=3.0
            )
            if self.stop_flag:
                return
            self.position_tracker.aster_position = await asyncio.wait_for(
                self.position_tracker.get_aster_position(),
                timeout=3.0
            )
        except asyncio.TimeoutError:
            if self.stop_flag:
                return
            self.logger.warning("⚠️ Timeout getting positions")
            return
        except Exception as e:
            if self.stop_flag:
                return
            self.logger.error(f"⚠️ Error getting positions: {e}")
            return

        if self.stop_flag:
            return

        self.logger.info(
            f"GRVT position: {self.position_tracker.grvt_position} | "
            f"Aster position: {self.position_tracker.aster_position}")

        if abs(self.position_tracker.get_net_position()) > self.order_quantity * 2:
            self.logger.error(
                f"❌ Position diff is too large: {self.position_tracker.get_net_position()}")
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
