"""Position tracking for GRVT and Aster exchanges."""
import asyncio
import logging
from decimal import Decimal
from exchanges.grvt import GrvtClient
from exchanges.aster import AsterClient


class PositionTracker:
    """Tracks positions on both exchanges."""

    def __init__(self, ticker: str, grvt_client: GrvtClient, aster_client: AsterClient, logger: logging.Logger):
        """Initialize position tracker."""
        self.ticker = ticker
        self.grvt_client = grvt_client
        self.aster_client = aster_client
        self.logger = logger

        self.grvt_position = Decimal('0')
        self.aster_position = Decimal('0')

    async def get_grvt_position(self) -> Decimal:
        """Get GRVT position."""
        if not self.grvt_client:
            raise Exception("GRVT client not initialized")

        try:
            position = await self.grvt_client.get_real_position()
            return position
        except Exception as e:
            self.logger.warning(f"⚠️ Error getting GRVT position: {e}")
            return Decimal('0')

    async def get_aster_position(self) -> Decimal:
        """Get Aster position."""
        if not self.aster_client:
            raise Exception("Aster client not initialized")

        try:
            position = await self.aster_client.get_real_position()
            return position
        except Exception as e:
            self.logger.warning(f"⚠️ Error getting Aster position: {e}")
            return Decimal('0')

    def update_grvt_position(self, delta: Decimal):
        """Update GRVT position by delta."""
        self.grvt_position += delta

    def update_aster_position(self, delta: Decimal):
        """Update Aster position by delta."""
        self.aster_position += delta

    def get_current_grvt_position(self) -> Decimal:
        """Get current GRVT position (cached)."""
        return self.grvt_position

    def get_current_aster_position(self) -> Decimal:
        """Get current Aster position (cached)."""
        return self.aster_position

    def get_net_position(self) -> Decimal:
        """Get net position across both exchanges."""
        return self.grvt_position + self.aster_position
