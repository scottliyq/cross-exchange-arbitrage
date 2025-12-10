"""WebSocket management for GRVT and Aster exchanges."""
import asyncio
import json
import logging
import time
import traceback
import websockets
from typing import Callable, Optional
from decimal import Decimal


class WebSocketManagerWrapper:
    """Manages WebSocket connections for both exchanges."""

    def __init__(self, order_book_manager, logger: logging.Logger):
        """Initialize WebSocket manager."""
        self.order_book_manager = order_book_manager
        self.logger = logger
        self.stop_flag = False

        # GRVT WebSocket
        self.grvt_client = None
        self.grvt_contract_id: Optional[str] = None
        self.grvt_ws_task: Optional[asyncio.Task] = None

        # Aster WebSocket
        self.aster_client = None
        self.aster_contract_id: Optional[str] = None
        self.aster_ws_task: Optional[asyncio.Task] = None

        # Callbacks
        self.on_grvt_order_update: Optional[Callable] = None
        self.on_aster_order_update: Optional[Callable] = None

    def set_grvt_config(self, client, contract_id: str):
        """Set GRVT client and contract ID."""
        self.grvt_client = client
        self.grvt_contract_id = contract_id

    def set_aster_config(self, client, contract_id: str):
        """Set Aster client and contract ID."""
        self.aster_client = client
        self.aster_contract_id = contract_id

    def set_callbacks(self, on_grvt_order_update: Callable = None,
                      on_aster_order_update: Callable = None):
        """Set callback functions for order updates."""
        self.on_grvt_order_update = on_grvt_order_update
        self.on_aster_order_update = on_aster_order_update

    # GRVT WebSocket methods
    async def handle_grvt_order_book_update(self, message):
        """Handle GRVT order book updates from WebSocket (async callback required by SDK)."""
        try:
            # Message comes directly as dict from SDK
            if isinstance(message, str):
                message = json.loads(message)

            # GRVT order book messages have 'feed' key containing the data
            if 'feed' in message:
                feed = message['feed']
                instrument = feed.get('instrument', '')
                
                # Only process matching instrument
                if instrument != self.grvt_contract_id:
                    return

                bids = feed.get('bids', [])
                asks = feed.get('asks', [])
                
                if len(bids) > 0 and len(asks) > 0:
                    self.logger.debug(f"📊 GRVT order book: {len(bids)} bids, {len(asks)} asks | "
                                      f"BBO: {bids[0]['price']}x{asks[0]['price']}")

                # Convert GRVT format [{'price': '94000.0', 'size': '0.1'}, ...]
                formatted_bids = []
                formatted_asks = []

                for bid in bids:
                    formatted_bids.append({
                        'price': bid.get('price', '0'),
                        'size': bid.get('size', '0')
                    })

                for ask in asks:
                    formatted_asks.append({
                        'price': ask.get('price', '0'),
                        'size': ask.get('size', '0')
                    })

                self.order_book_manager.update_grvt_order_book(formatted_bids, formatted_asks)

        except Exception as e:
            self.logger.error(f"Error handling GRVT order book update: {e}")
            self.logger.error(f"Message content: {message}")
            self.logger.error(traceback.format_exc())

    async def setup_grvt_websocket(self):
        """Setup GRVT websocket for order book data."""
        if not self.grvt_client:
            raise Exception("GRVT client not initialized")

        try:
            # Note: GRVT client should already be connected by the main trading loop
            # Just setup the order book subscription
            self.logger.info("Setting up GRVT order book subscription...")
            await self._setup_grvt_order_book_subscription()

        except Exception as e:
            self.logger.error(f"Could not setup GRVT WebSocket: {e}")
            raise

    async def _setup_grvt_order_book_subscription(self):
        """Setup GRVT order book subscription using official SDK pattern."""
        try:
            from pysdk.grvt_ccxt_env import GrvtWSEndpointType
            
            self.logger.info(f"🔄 Setting up GRVT order book subscription for {self.grvt_contract_id}")
            
            # Check if WebSocket client exists
            if not hasattr(self.grvt_client, '_ws_client') or not self.grvt_client._ws_client:
                self.logger.error("⚠️ GRVT WebSocket client not available")
                return
            
            ws_client = self.grvt_client._ws_client
            
            # Subscribe directly - SDK will auto-connect the needed endpoint
            # Don't call initialize() as it tries to connect ALL endpoints (mdg, tdg, etc.)
            # which causes timeouts for endpoints we don't need
            self.logger.info(f"📡 Subscribing to GRVT order book stream...")
            await ws_client.subscribe(
                stream="book.s",
                ws_end_point_type=GrvtWSEndpointType.MARKET_DATA_RPC_FULL,
                callback=self.handle_grvt_order_book_update,
                params={"instrument": self.grvt_contract_id}
            )
            
            self.logger.info(f"✅ Subscribed to GRVT order book for {self.grvt_contract_id}")
            
            # Wait a bit for subscription to establish and first messages to arrive
            await asyncio.sleep(3)

        except Exception as e:
            self.logger.error(f"Error subscribing to GRVT order book: {e}")
            self.logger.error(traceback.format_exc())

    # Aster WebSocket methods
    def handle_aster_order_book_update(self, message):
        """Handle Aster order book updates from WebSocket."""
        try:
            if isinstance(message, str):
                message = json.loads(message)

            self.logger.debug(f"Received Aster book message: {message}")

            # Aster uses Binance-style WebSocket format
            # Event type: depthUpdate
            event_type = message.get('e')
            if event_type == 'depthUpdate':
                symbol = message.get('s', '')
                if symbol != self.aster_contract_id:
                    return

                bids = message.get('b', [])  # [[price, quantity], ...]
                asks = message.get('a', [])

                # Convert to our format
                formatted_bids = []
                formatted_asks = []

                for bid in bids:
                    if len(bid) >= 2:
                        formatted_bids.append({
                            'price': bid[0],
                            'size': bid[1]
                        })

                for ask in asks:
                    if len(ask) >= 2:
                        formatted_asks.append({
                            'price': ask[0],
                            'size': ask[1]
                        })

                self.order_book_manager.update_aster_order_book(formatted_bids, formatted_asks)

        except Exception as e:
            self.logger.error(f"Error handling Aster order book update: {e}")
            self.logger.error(f"Message content: {message}")
            self.logger.error(traceback.format_exc())

    async def handle_aster_ws(self):
        """Handle Aster WebSocket connection and messages."""
        # Aster uses Binance-style WebSocket
        ws_url = f"wss://fstream.asterdex.com/ws/{self.aster_contract_id.lower()}@depth@100ms"
        
        while not self.stop_flag:
            timeout_count = 0
            try:
                self.logger.info(f"🔄 Connecting to Aster WebSocket: {ws_url}")
                
                async with websockets.connect(ws_url) as ws:
                    self.logger.info("✅ Aster WebSocket connected")
                    
                    while not self.stop_flag:
                        try:
                            msg = await asyncio.wait_for(ws.recv(), timeout=30)

                            try:
                                data = json.loads(msg)
                            except json.JSONDecodeError as e:
                                self.logger.warning(f"⚠️ Aster JSON parsing error: {e}")
                                continue

                            timeout_count = 0
                            self.handle_aster_order_book_update(data)

                        except asyncio.TimeoutError:
                            timeout_count += 1
                            if timeout_count % 3 == 0:
                                self.logger.warning(
                                    f"⏰ No message from Aster websocket for {timeout_count * 30} seconds")
                            continue
                        except websockets.exceptions.ConnectionClosed as e:
                            self.logger.warning(f"⚠️ Aster websocket connection closed: {e}")
                            break
                        except Exception as e:
                            self.logger.error(f"⚠️ Error in Aster websocket: {e}")
                            self.logger.error(traceback.format_exc())
                            break

            except Exception as e:
                self.logger.error(f"⚠️ Failed to connect to Aster websocket: {e}")
                self.logger.error(traceback.format_exc())

            if not self.stop_flag:
                self.logger.info("🔄 Reconnecting to Aster WebSocket in 2 seconds...")
                await asyncio.sleep(2)

    async def setup_aster_websocket(self):
        """Setup Aster websocket for order book data."""
        if not self.aster_client:
            raise Exception("Aster client not initialized")

        try:
            # Start Aster WebSocket task
            self.start_aster_websocket()
            self.logger.info("✅ Aster WebSocket task started")

        except Exception as e:
            self.logger.error(f"Could not setup Aster WebSocket: {e}")
            raise

    def start_aster_websocket(self):
        """Start Aster WebSocket task."""
        if self.aster_ws_task is None or self.aster_ws_task.done():
            self.aster_ws_task = asyncio.create_task(self.handle_aster_ws())
            self.logger.info("✅ Aster WebSocket task created")

    async def wait_for_order_books_ready(self, timeout: int = 30):
        """Wait for both order books to be ready."""
        start_time = time.time()
        
        # Wait for GRVT order book
        self.logger.info("⏳ Waiting for GRVT order book data...")
        while not self.order_book_manager.grvt_order_book_ready and not self.stop_flag:
            if time.time() - start_time > timeout:
                self.logger.warning(
                    f"⚠️ Timeout waiting for GRVT order book data after {timeout}s")
                break
            await asyncio.sleep(0.5)

        if self.order_book_manager.grvt_order_book_ready:
            self.logger.info("✅ GRVT order book data received")
        else:
            self.logger.warning("⚠️ GRVT order book not ready")

        # Wait for Aster order book
        self.logger.info("⏳ Waiting for Aster order book data...")
        start_time = time.time()
        while not self.order_book_manager.aster_order_book_ready and not self.stop_flag:
            if time.time() - start_time > timeout:
                self.logger.warning(
                    f"⚠️ Timeout waiting for Aster order book data after {timeout}s")
                break
            await asyncio.sleep(0.5)

        if self.order_book_manager.aster_order_book_ready:
            self.logger.info("✅ Aster order book data received")
        else:
            self.logger.warning("⚠️ Aster order book not ready")

    def shutdown(self):
        """Shutdown WebSocket connections."""
        self.stop_flag = True
        
        # Close GRVT WebSocket
        if self.grvt_client:
            try:
                # GRVT client handles its own WebSocket cleanup
                asyncio.create_task(self.grvt_client.disconnect())
                self.logger.info("🔌 GRVT WebSocket disconnecting")
            except Exception as e:
                self.logger.error(f"Error disconnecting GRVT WebSocket: {e}")

        # Cancel Aster WebSocket task
        if self.aster_ws_task and not self.aster_ws_task.done():
            try:
                self.aster_ws_task.cancel()
                self.logger.info("🔌 Aster WebSocket task cancelled")
            except Exception as e:
                self.logger.error(f"Error cancelling Aster WebSocket task: {e}")
