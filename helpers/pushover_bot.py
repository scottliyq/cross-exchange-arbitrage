"""Pushover notification helper for sending alerts."""
import logging
import aiohttp
import os
from typing import Optional


class PushoverBot:
    """Helper class for sending Pushover notifications."""

    def __init__(self, user_key: Optional[str] = None, api_token: Optional[str] = None, 
                 logger: Optional[logging.Logger] = None):
        """Initialize Pushover bot.
        
        Args:
            user_key: Pushover user key (defaults to PUSHOVER_USER_KEY env var)
            api_token: Pushover API token (defaults to PUSHOVER_API_TOKEN env var)
            logger: Logger instance (creates new one if not provided)
        """
        self.user_key = user_key or os.getenv('PUSHOVER_USER_KEY')
        self.api_token = api_token or os.getenv('PUSHOVER_API_TOKEN')
        self.logger = logger or logging.getLogger(__name__)

    async def send_alert(self, title: str, message: str, priority: int = 0,
                        retry: int = 30, expire: int = 3600) -> bool:
        """Send alert via Pushover.
        
        Args:
            title: Alert title
            message: Alert message
            priority: Message priority (-2 to 2, default 0, 2 = emergency)
            retry: For priority=2, retry interval in seconds (default 30, minimum 30)
            expire: For priority=2, expire time in seconds (default 3600, max 10800)
        
        Returns:
            True if alert sent successfully, False otherwise
        """
        if not self.user_key or not self.api_token:
            self.logger.warning("⚠️ Pushover credentials not configured, skipping alert")
            return False

        try:
            url = "https://api.pushover.net/1/messages.json"
            data = {
                "token": self.api_token,
                "user": self.user_key,
                "title": title,
                "message": message,
                "priority": priority
            }
            
            # For emergency priority (2), must provide retry and expire
            if priority == 2:
                data["retry"] = max(30, retry)  # Minimum 30 seconds
                data["expire"] = min(10800, expire)  # Maximum 3 hours

            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data) as response:
                    if response.status == 200:
                        self.logger.info(f"✅ Pushover alert sent: {title}")
                        return True
                    else:
                        error_text = await response.text()
                        self.logger.error(
                            f"❌ Failed to send Pushover alert: {response.status} - {error_text}")
                        return False
        except Exception as e:
            self.logger.error(f"❌ Error sending Pushover alert: {e}")
            return False


async def send_pushover_alert(title: str, message: str, priority: int = 0,
                              user_key: Optional[str] = None, 
                              api_token: Optional[str] = None,
                              logger: Optional[logging.Logger] = None) -> bool:
    """Convenience function to send a Pushover alert without creating a bot instance.
    
    Args:
        title: Alert title
        message: Alert message
        priority: Message priority (-2 to 2, default 0, 2 = emergency)
        user_key: Pushover user key (defaults to PUSHOVER_USER_KEY env var)
        api_token: Pushover API token (defaults to PUSHOVER_API_TOKEN env var)
        logger: Logger instance (creates new one if not provided)
    
    Returns:
        True if alert sent successfully, False otherwise
    """
    bot = PushoverBot(user_key=user_key, api_token=api_token, logger=logger)
    return await bot.send_alert(title, message, priority)
