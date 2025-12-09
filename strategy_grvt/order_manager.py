"""Order placement and monitoring for GRVT and Aster exchanges."""
import asyncio
import logging
import time
from decimal import Decimal
from typing import Optional, Callable, Any
from exchanges.grvt import GrvtClient
from exchanges.aster import AsterClient


class OrderManager:
    """Manages order placement and monitoring for both exchanges."""

    def __init__(self, order_book_manager, logger: logging.Logger):
        """Initialize order manager."""
        self.order_book_manager = order_book_manager
        self.logger = logger

        # GRVT client and config
        self.grvt_client: Optional[GrvtClient] = None
        self.grvt_contract_id: Optional[str] = None
        self.grvt_tick_size: Optional[Decimal] = None
        self.grvt_order_status: Optional[str] = None
        self.grvt_client_order_id: str = ''

        # Aster client and config
        self.aster_client: Optional[AsterClient] = None
        self.aster_contract_id: Optional[str] = None
        self.aster_tick_size: Optional[Decimal] = None

        # Aster order state
        self.aster_order_filled = False
        self.aster_order_price: Optional[Decimal] = None
        self.aster_order_side: Optional[str] = None
        self.aster_order_size: Optional[Decimal] = None

        # Order execution tracking
        self.order_execution_complete = False
        self.waiting_for_aster_fill = False
        self.current_aster_side: Optional[str] = None
        self.current_aster_quantity: Optional[Decimal] = None
        self.current_aster_price: Optional[Decimal] = None

        # Callbacks
        self.on_order_filled: Optional[Callable[[Any], None]] = None

    def set_grvt_config(self, client: GrvtClient, contract_id: str, tick_size: Decimal):
        """Set GRVT client and configuration."""
        self.grvt_client = client
        self.grvt_contract_id = contract_id
        self.grvt_tick_size = tick_size

    def set_aster_config(self, client: AsterClient, contract_id: str, tick_size: Decimal):
        """Set Aster client and configuration."""
        self.aster_client = client
        self.aster_contract_id = contract_id
        self.aster_tick_size = tick_size

    def set_callbacks(self, on_order_filled: Optional[Callable[[Any], None]] = None):
        """Set callback functions."""
        self.on_order_filled = on_order_filled

    def round_to_tick(self, price: Decimal) -> Decimal:
        """Round price to tick size."""
        if self.grvt_tick_size is None:
            return price
        return (price / self.grvt_tick_size).quantize(Decimal('1')) * self.grvt_tick_size

    async def fetch_grvt_bbo_prices(self) -> tuple[Decimal, Decimal]:
        """Fetch best bid/ask prices from GRVT using REST API."""
        if not self.grvt_client or not self.grvt_contract_id:
            raise Exception("GRVT client not initialized")

        best_bid, best_ask = await self.grvt_client.fetch_bbo_prices(self.grvt_contract_id)
        
        if best_bid <= 0 or best_ask <= 0 or best_bid >= best_ask:
            # Fallback to WebSocket data if REST fails
            grvt_bid, grvt_ask = self.order_book_manager.get_grvt_bbo()
            if grvt_bid and grvt_ask and grvt_bid > 0 and grvt_ask > 0 and grvt_bid < grvt_ask:
                return grvt_bid, grvt_ask
            raise Exception("Invalid BBO prices from GRVT")

        return best_bid, best_ask

    async def place_bbo_order(self, side: str, quantity: Decimal) -> str:
        """Place a BBO order on GRVT."""
        if not self.grvt_client or not self.grvt_contract_id or not self.grvt_tick_size:
            raise Exception("GRVT client not properly configured")
            
        best_bid, best_ask = await self.fetch_grvt_bbo_prices()

        if side.lower() == 'buy':
            order_price = best_ask - self.grvt_tick_size
            order_side = 'buy'
        else:
            order_price = best_bid + self.grvt_tick_size
            order_side = 'sell'

        order_price = self.round_to_tick(order_price)
        
        order_result = await self.grvt_client.place_post_only_order(
            contract_id=self.grvt_contract_id,
            quantity=quantity,
            price=order_price,
            side=order_side
        )

        if not order_result or not order_result.order_id:
            raise Exception("Failed to place order")

        return order_result.order_id

    async def place_grvt_post_only_order(self, side: str, quantity: Decimal, stop_flag) -> bool:
        """Place a post-only order on GRVT."""
        if not self.grvt_client:
            raise Exception("GRVT client not initialized")

        self.grvt_order_status = None
        self.logger.info(f"[OPEN] [GRVT] [{side}] Placing GRVT POST-ONLY order")
        order_id = await self.place_bbo_order(side, quantity)

        start_time = time.time()
        while not stop_flag:
            if self.grvt_order_status == 'CANCELED':
                return False
            elif self.grvt_order_status in ['OPEN', 'PENDING', 'PARTIALLY_FILLED']:
                await asyncio.sleep(0.5)
                if time.time() - start_time > 5:
                    try:
                        cancel_result = await self.grvt_client.cancel_order(order_id)
                        if not cancel_result.success:
                            self.logger.error("❌ Error canceling GRVT order")
                    except Exception as e:
                        self.logger.error(f"❌ Error canceling GRVT order: {e}")
            elif self.grvt_order_status == 'FILLED':
                break
            else:
                if self.grvt_order_status is not None:
                    self.logger.error(f"❌ Unknown GRVT order status: {self.grvt_order_status}")
                    return False
                else:
                    await asyncio.sleep(0.5)
        return True

    def handle_grvt_order_update(self, order_data: dict):
        """Handle GRVT order update."""
        side = order_data.get('side', '').lower()
        filled_size = order_data.get('filled_size')
        price = order_data.get('price', '0')

        if side == 'buy':
            aster_side = 'sell'
        else:
            aster_side = 'buy'

        self.current_aster_side = aster_side
        self.current_aster_quantity = filled_size
        self.current_aster_price = Decimal(price)
        self.waiting_for_aster_fill = True

    def update_grvt_order_status(self, status: str):
        """Update GRVT order status."""
        self.grvt_order_status = status

    async def place_aster_market_order(self, aster_side: str, quantity: Decimal,
                                       price: Decimal, stop_flag) -> Optional[str]:
        """Place a market order on Aster."""
        if not self.aster_client or not self.aster_contract_id:
            raise Exception("Aster client not initialized")

        if aster_side.lower() == 'buy':
            order_type = "CLOSE"
        else:
            order_type = "OPEN"

        self.aster_order_filled = False

        try:
            self.logger.info(f"[{order_type}] [Aster] Placing market order: {quantity} @ ~{price}")
            
            order_result = await self.aster_client.place_market_order(
                contract_id=self.aster_contract_id,
                quantity=quantity,
                direction=aster_side
            )

            if not order_result.success:
                raise Exception(f"Aster market order failed: {order_result.error_message}")

            order_id = order_result.order_id
            
            # For market orders, they should be filled immediately
            self.logger.info(f"[{order_type}] [Aster] [FILLED]: {quantity} @ {order_result.price}")

            if aster_side.lower() == 'sell':
                side = "SHORT"
            else:
                side = "LONG"

            # Log trade
            if self.on_order_filled:
                self.on_order_filled({
                    'order_id': order_id,
                    'side': side,
                    'filled_base_amount': quantity,
                    'avg_filled_price': order_result.price
                })

            self.aster_order_filled = True
            self.order_execution_complete = True

            return order_id
        except Exception as e:
            self.logger.error(f"❌ Error placing Aster market order: {e}")
            return None

    def handle_aster_order_filled(self, order_data: dict):
        """Handle Aster order fill notification."""
        try:
            side = order_data.get("side", "").lower()
            if side == 'sell':
                order_data["side"] = "SHORT"
                order_type = "OPEN"
            else:
                order_data["side"] = "LONG"
                order_type = "CLOSE"

            order_id = order_data.get("order_id", "")
            filled_amount = order_data.get("filled_base_amount", 0)
            avg_price = order_data.get("avg_filled_price", 0)

            self.logger.info(
                f"[{order_id}] [{order_type}] [Aster] [FILLED]: "
                f"{filled_amount} @ {avg_price}")

            if self.on_order_filled:
                self.on_order_filled(order_data)

            self.aster_order_filled = True
            self.order_execution_complete = True

        except Exception as e:
            self.logger.error(f"Error handling Aster order result: {e}")

    def get_grvt_client_order_id(self) -> str:
        """Get current GRVT client order ID."""
        return self.grvt_client_order_id
