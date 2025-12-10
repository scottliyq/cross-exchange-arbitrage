"""Order book management for GRVT and Aster exchanges."""
import asyncio
import logging
from decimal import Decimal
from typing import Tuple, Optional


class OrderBookManager:
    """Manages order book state for both exchanges."""

    def __init__(self, logger: logging.Logger):
        """Initialize order book manager."""
        self.logger = logger

        # GRVT order book state  
        self.grvt_order_book = {'bids': {}, 'asks': {}}
        self.grvt_best_bid: Optional[Decimal] = None
        self.grvt_best_ask: Optional[Decimal] = None
        self.grvt_order_book_ready = False

        # Aster order book state
        self.aster_order_book = {"bids": {}, "asks": {}}
        self.aster_best_bid: Optional[Decimal] = None
        self.aster_best_ask: Optional[Decimal] = None
        self.aster_order_book_ready = False
        self.aster_order_book_lock = asyncio.Lock()

    # GRVT order book methods
    def update_grvt_order_book(self, bids: list, asks: list):
        """Update GRVT order book with new levels.
        
        Note: GRVT 'book.d' stream sends incremental updates (deltas).
        Size = 0 means remove that price level, size > 0 means add/update.
        """
        # Update bids (incremental mode)
        for bid in bids:
            price = Decimal(bid['price'])
            size = Decimal(bid['size'])
            if size > 0:
                self.grvt_order_book['bids'][price] = size
            else:
                # Size = 0 means remove this price level
                self.grvt_order_book['bids'].pop(price, None)

        # Update asks (incremental mode)
        for ask in asks:
            price = Decimal(ask['price'])
            size = Decimal(ask['size'])
            if size > 0:
                self.grvt_order_book['asks'][price] = size
            else:
                # Size = 0 means remove this price level
                self.grvt_order_book['asks'].pop(price, None)

        # Update best bid and ask
        if self.grvt_order_book['bids']:
            self.grvt_best_bid = max(self.grvt_order_book['bids'].keys())
        else:
            self.grvt_best_bid = None
            
        if self.grvt_order_book['asks']:
            self.grvt_best_ask = min(self.grvt_order_book['asks'].keys())
        else:
            self.grvt_best_ask = None

        if not self.grvt_order_book_ready:
            self.grvt_order_book_ready = True
            self.logger.info(f"📊 GRVT order book ready - Best bid: {self.grvt_best_bid}, "
                             f"Best ask: {self.grvt_best_ask}")
        else:
            self.logger.debug(f"📊 GRVT order book updated - Best bid: {self.grvt_best_bid}, "
                              f"Best ask: {self.grvt_best_ask}")

    def get_grvt_bbo(self) -> Tuple[Optional[Decimal], Optional[Decimal]]:
        """Get GRVT best bid/ask prices."""
        return self.grvt_best_bid, self.grvt_best_ask

    # Aster order book methods
    async def reset_aster_order_book(self):
        """Reset Aster order book state."""
        async with self.aster_order_book_lock:
            self.aster_order_book["bids"].clear()
            self.aster_order_book["asks"].clear()
            self.aster_best_bid = None
            self.aster_best_ask = None

    def update_aster_order_book(self, bids: list, asks: list):
        """Update Aster order book with new bid and ask levels."""
        # Update bids
        for level in bids:
            # Handle different data structures - could be list [price, size] or dict {"price": ..., "size": ...}
            if isinstance(level, list) and len(level) >= 2:
                price = Decimal(level[0])
                size = Decimal(level[1])
            elif isinstance(level, dict):
                price = Decimal(level.get("price", 0))
                size = Decimal(level.get("size", 0))
            else:
                self.logger.warning(f"⚠️ Unexpected bid level format: {level}")
                continue

            if size > 0:
                self.aster_order_book["bids"][price] = size
            else:
                # Remove zero size orders
                self.aster_order_book["bids"].pop(price, None)

        # Update asks
        for level in asks:
            if isinstance(level, list) and len(level) >= 2:
                price = Decimal(level[0])
                size = Decimal(level[1])
            elif isinstance(level, dict):
                price = Decimal(level.get("price", 0))
                size = Decimal(level.get("size", 0))
            else:
                self.logger.warning(f"⚠️ Unexpected ask level format: {level}")
                continue

            if size > 0:
                self.aster_order_book["asks"][price] = size
            else:
                # Remove zero size orders
                self.aster_order_book["asks"].pop(price, None)

        # Update BBO after processing all levels
        self.update_aster_bbo()

    def validate_order_book_integrity(self) -> bool:
        """Validate order book integrity."""
        # Check for negative prices or sizes
        for side in ["bids", "asks"]:
            for price, size in self.aster_order_book[side].items():
                if price <= 0 or size <= 0:
                    self.logger.error(f"❌ Invalid order book data: {side} price={price}, size={size}")
                    return False
        return True

    def get_aster_best_levels(self) -> Tuple[Optional[Tuple[Decimal, Decimal]],
                                              Optional[Tuple[Decimal, Decimal]]]:
        """Get best bid and ask levels from Aster order book."""
        best_bid = None
        best_ask = None

        if self.aster_order_book["bids"]:
            best_bid_price = max(self.aster_order_book["bids"].keys())
            best_bid_size = self.aster_order_book["bids"][best_bid_price]
            best_bid = (best_bid_price, best_bid_size)

        if self.aster_order_book["asks"]:
            best_ask_price = min(self.aster_order_book["asks"].keys())
            best_ask_size = self.aster_order_book["asks"][best_ask_price]
            best_ask = (best_ask_price, best_ask_size)

        return best_bid, best_ask

    def get_aster_bbo(self) -> Tuple[Optional[Decimal], Optional[Decimal]]:
        """Get Aster best bid/ask prices."""
        return self.aster_best_bid, self.aster_best_ask

    def update_aster_bbo(self):
        """Update Aster best bid and ask prices."""
        if self.aster_order_book["bids"]:
            self.aster_best_bid = max(self.aster_order_book["bids"].keys())
        else:
            self.aster_best_bid = None

        if self.aster_order_book["asks"]:
            self.aster_best_ask = min(self.aster_order_book["asks"].keys())
        else:
            self.aster_best_ask = None

        if not self.aster_order_book_ready and self.aster_best_bid and self.aster_best_ask:
            self.aster_order_book_ready = True
            self.logger.info(f"📊 Aster order book ready - Best bid: {self.aster_best_bid}, "
                             f"Best ask: {self.aster_best_ask}")

    def get_aster_mid_price(self) -> Decimal:
        """Get mid price from Aster order book."""
        best_bid, best_ask = self.get_aster_best_levels()

        if best_bid is None or best_ask is None:
            raise Exception("Cannot calculate mid price - missing order book data")

        mid_price = (best_bid[0] + best_ask[0]) / Decimal('2')
        return mid_price
