"""Main entry point for arbitrage bot with Supabase configuration."""
import asyncio
import argparse
import os
import sys
from decimal import Decimal
from dotenv import load_dotenv

print("Loading modules...")
sys.stdout.flush()

from strategy_grvt.grvt_arb import GrvtArb
from helpers.supabase_helper import SupabaseHelper

print("Modules loaded successfully!")
sys.stdout.flush()


def create_grvt_aster_bot(symbol: str, master_config: dict, detail_config: dict):
    """Create GRVT-Aster arbitrage bot instance.
    
    Args:
        symbol: Trading symbol (e.g., 'BTC', 'ETH')
        master_config: Master configuration from maker_taker_master table
        detail_config: Detail configuration from maker_taker_detail table
    
    Returns:
        GrvtArb instance
    """
    # Extract configuration parameters
    ticker = symbol
    order_quantity = Decimal(str(detail_config.get('order_quantity', 0.001)))
    max_position = Decimal(str(detail_config.get('max_position', 0.1)))
    long_threshold = Decimal(str(detail_config.get('long_threshold', 10)))
    short_threshold = Decimal(str(detail_config.get('short_threshold', 10)))
    z_score_multiplier = float(detail_config.get('z_score_multiplier', 1.5))
    
    print(f"Creating GRVT-Aster arbitrage bot")
    print(f"Ticker: {ticker}")
    print(f"Order Quantity: {order_quantity}")
    print(f"Max Position: {max_position}")
    print(f"Long Threshold: {long_threshold}")
    print(f"Short Threshold: {short_threshold}")
    print(f"Z-Score Multiplier: {z_score_multiplier}")
    print("-" * 50)
    
    # Create and return bot
    return GrvtArb(
        ticker=ticker,
        order_quantity=order_quantity,
        max_position=max_position,
        long_grvt_threshold=long_threshold,
        short_grvt_threshold=short_threshold,
        z_score_multiplier=z_score_multiplier
    )


def create_bot_from_config(config_key: str, symbol: str):
    """Create bot instance based on Supabase configuration.
    
    Args:
        config_key: Configuration key to query from Supabase
        symbol: Trading symbol (e.g., 'BTC', 'ETH')
    
    Returns:
        Bot instance based on maker_taker value
    """
    # Initialize Supabase helper
    helper = SupabaseHelper()
    
    # Get master configuration
    print(f"Loading configuration for config_key: {config_key}")
    master_config = helper.get_maker_taker_master(config_key)
    
    if not master_config:
        print(f"❌ Error: No master configuration found for config_key: {config_key}")
        sys.exit(1)
    
    # Get detail configuration for symbol
    detail_config = helper.get_maker_taker_detail(config_key, symbol)
    
    if not detail_config:
        print(f"❌ Error: No detail configuration found for config_key: {config_key}, symbol: {symbol}")
        sys.exit(1)
    
    # Get maker_taker value
    maker_taker = master_config.get('maker_taker', '').lower()
    
    print(f"✓ Configuration loaded successfully")
    print(f"  Config Key: {config_key}")
    print(f"  Symbol: {symbol}")
    print(f"  Maker-Taker: {maker_taker}")
    print("-" * 50)
    
    # Create bot based on maker_taker value
    if maker_taker == 'grvt_aster':
        return create_grvt_aster_bot(symbol, master_config, detail_config)
    
    # TODO: Add support for other exchange pairs
    # elif maker_taker == 'other_exchange_pair':
    #     return create_other_bot(symbol, master_config, detail_config)
    
    else:
        print(f"❌ Error: Unsupported maker_taker value: {maker_taker}")
        print(f"Supported values: grvt_aster")
        sys.exit(1)


def main():
    """Main function to run the arbitrage bot."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Arbitrage Bot with Supabase Configuration')
    parser.add_argument('--config-key', type=str, required=True,
                        help='Configuration key to load from Supabase')
    parser.add_argument('--symbol', type=str, required=True,
                        help='Trading symbol (e.g., BTC, ETH)')
    args = parser.parse_args()
    
    # Load environment variables from .grvt_aster_env
    load_dotenv('.grvt_aster_env')
    
    # Get parameters
    config_key = args.config_key
    symbol = args.symbol.upper()
    
    print(f"Starting arbitrage bot")
    print(f"Config Key: {config_key}")
    print(f"Symbol: {symbol}")
    print("=" * 50)
    
    # Create bot from Supabase configuration
    bot = create_bot_from_config(config_key, symbol)
    
    # Run the bot
    asyncio.run(bot.run())


if __name__ == "__main__":
    main()
