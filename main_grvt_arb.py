"""Main entry point for GRVT-Aster arbitrage bot."""
import asyncio
import os
import sys
from decimal import Decimal
from dotenv import load_dotenv

print("Loading modules...")
sys.stdout.flush()

from strategy_grvt.grvt_arb import GrvtArb

print("Modules loaded successfully!")
sys.stdout.flush()


def main():
    """Main function to run the arbitrage bot."""
    # Load environment variables from .grvt_aster_env
    load_dotenv('.grvt_aster_env')
    
    # Configuration
    ticker = os.getenv('TICKER', 'BTC')
    order_quantity = Decimal(os.getenv('ORDER_QUANTITY', '0.001'))
    max_position = Decimal(os.getenv('MAX_POSITION', '0.01'))
    long_grvt_threshold = Decimal(os.getenv('LONG_GRVT_THRESHOLD', '10'))
    short_grvt_threshold = Decimal(os.getenv('SHORT_GRVT_THRESHOLD', '10'))
    
    print(f"Starting GRVT-Aster arbitrage bot")
    print(f"Ticker: {ticker}")
    print(f"Order Quantity: {order_quantity}")
    print(f"Max Position: {max_position}")
    print(f"Long GRVT Threshold: {long_grvt_threshold}")
    print(f"Short GRVT Threshold: {short_grvt_threshold}")
    print("-" * 50)
    
    # Create and run bot
    bot = GrvtArb(
        ticker=ticker,
        order_quantity=order_quantity,
        max_position=max_position,
        long_grvt_threshold=long_grvt_threshold,
        short_grvt_threshold=short_grvt_threshold
    )
    
    # Run the bot
    asyncio.run(bot.run())


if __name__ == "__main__":
    main()
