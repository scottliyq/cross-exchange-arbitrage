"""Main entry point for GRVT-Aster arbitrage bot."""
import asyncio
import argparse
import os
import sys
from decimal import Decimal
from dotenv import load_dotenv

print("Loading modules...")
sys.stdout.flush()

from strategy_grvt.grvt_arb import GrvtArb

print("Modules loaded successfully!")
sys.stdout.flush()

# Parameter configuration for different symbols
param = {
    "BTC": {
        "ORDER_QUANTITY": 0.004,
        "MAX_POSITION": 0.12,
        "LONG_GRVT_THRESHOLD": 30,
        "SHORT_GRVT_THRESHOLD": 30
    },
    "ETH": {
        "ORDER_QUANTITY": 0.1,
        "MAX_POSITION": 3,
        "LONG_GRVT_THRESHOLD": 2,
        "SHORT_GRVT_THRESHOLD": 2
    }
}

def main():
    """Main function to run the arbitrage bot."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='GRVT-Aster Arbitrage Bot')
    parser.add_argument('--symbol', type=str, default='BTC', 
                        help='Trading symbol (e.g., BTC, ETH). Default: BTC')
    args = parser.parse_args()
    
    # Load environment variables from .grvt_aster_env
    load_dotenv('.grvt_aster_env')
    
    # Get symbol from command line argument
    symbol = args.symbol.upper()
    
    # Check if symbol exists in param configuration
    if symbol not in param:
        print(f"❌ Error: Symbol '{symbol}' not found in configuration")
        print(f"Available symbols: {', '.join(param.keys())}")
        sys.exit(1)
    
    # Get configuration from param dictionary
    config = param[symbol]
    ticker = symbol
    order_quantity = Decimal(str(config['ORDER_QUANTITY']))
    max_position = Decimal(str(config['MAX_POSITION']))
    long_grvt_threshold = Decimal(str(config['LONG_GRVT_THRESHOLD']))
    short_grvt_threshold = Decimal(str(config['SHORT_GRVT_THRESHOLD']))
    
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
