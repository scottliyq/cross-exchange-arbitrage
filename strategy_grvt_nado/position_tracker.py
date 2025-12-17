"""Position tracking for GRVT and Nado exchanges."""
import asyncio
import logging
from decimal import Decimal
from exchanges.grvt import GrvtClient
from exchanges.nado import NadoClient


class PositionTracker:
    """Tracks positions on both exchanges."""

    def __init__(self, ticker: str, grvt_client: GrvtClient, nado_client: NadoClient, logger: logging.Logger):
        """Initialize position tracker."""
        self.ticker = ticker
        self.grvt_client = grvt_client
        self.nado_client = nado_client
        self.logger = logger

        self.grvt_position = Decimal('0')
        self.nado_position = Decimal('0')

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

    async def get_nado_position(self) -> Decimal:
        """Get Nado position."""
        if not self.nado_client:
            raise Exception("Nado client not initialized")

        try:
            position = await self.nado_client.get_real_position()
            return position
        except Exception as e:
            self.logger.warning(f"⚠️ Error getting Nado position: {e}")
            return Decimal('0')

    def update_grvt_position(self, delta: Decimal):
        """Update GRVT position by delta."""
        self.grvt_position += delta

    def update_nado_position(self, delta: Decimal):
        """Update Nado position by delta."""
        self.nado_position += delta

    def get_current_grvt_position(self) -> Decimal:
        """Get current GRVT position (cached)."""
        return self.grvt_position

    def get_current_nado_position(self) -> Decimal:
        """Get current Nado position (cached)."""
        return self.nado_position

    def get_net_position(self) -> Decimal:
        """Get net position across both exchanges."""
        return self.grvt_position + self.nado_position
