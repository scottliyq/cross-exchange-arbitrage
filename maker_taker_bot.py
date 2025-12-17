"""Main entry point for arbitrage bot with Supabase configuration."""
import asyncio
import argparse
import os
import sys
from decimal import Decimal
from dotenv import load_dotenv

print("Loading modules...")
sys.stdout.flush()

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
    # Lazy import to avoid dependency conflicts
    from strategy_grvt.grvt_arb import GrvtArb
    
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


def create_grvt_nado_bot(symbol: str, master_config: dict, detail_config: dict):
    """Create GRVT-Nado arbitrage bot instance.
    
    Args:
        symbol: Trading symbol (e.g., 'BTC', 'ETH')
        master_config: Master configuration from maker_taker_master table
        detail_config: Detail configuration from maker_taker_detail table
    
    Returns:
        GrvtNadoArb instance
    """
    # Lazy import to avoid dependency conflicts
    from strategy_grvt_nado.grvt_nado_arb import GrvtNadoArb
    
    # Extract configuration parameters
    ticker = symbol
    order_quantity = Decimal(str(detail_config.get('order_quantity', 0.001)))
    max_position = Decimal(str(detail_config.get('max_position', 0.1)))
    long_threshold = Decimal(str(detail_config.get('long_threshold', 10)))
    short_threshold = Decimal(str(detail_config.get('short_threshold', 10)))
    z_score_multiplier = float(detail_config.get('z_score_multiplier', 1.5))
    
    print(f"Creating GRVT-Nado arbitrage bot")
    print(f"Ticker: {ticker}")
    print(f"Order Quantity: {order_quantity}")
    print(f"Max Position: {max_position}")
    print(f"Long Threshold: {long_threshold}")
    print(f"Short Threshold: {short_threshold}")
    print(f"Z-Score Multiplier: {z_score_multiplier}")
    print("-" * 50)
    
    # Create and return bot
    return GrvtNadoArb(
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
    elif maker_taker == 'grvt_nado':
        return create_grvt_nado_bot(symbol, master_config, detail_config)
    
    # TODO: Add support for other exchange pairs
    # elif maker_taker == 'other_exchange_pair':
    #     return create_other_bot(symbol, master_config, detail_config)
    
    else:
        print(f"❌ Error: Unsupported maker_taker value: {maker_taker}")
        print(f"Supported values: grvt_aster, grvt_nado")
        sys.exit(1)


def get_env_file_for_maker_taker(maker_taker: str) -> str:
    """Get the appropriate environment file based on maker_taker value.
    
    Args:
        maker_taker: The maker_taker value from Supabase configuration
    
    Returns:
        str: Path to the appropriate environment file
    """
    env_file_map = {
        'grvt_aster': '.grvt_aster_env',
        'grvt_nado': '.grvt_nado_env',
    }
    return env_file_map.get(maker_taker, '.grvt_aster_env')


def main():
    """Main function to run the arbitrage bot."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Arbitrage Bot with Supabase Configuration')
    parser.add_argument('--config-key', type=str, required=True,
                        help='Configuration key to load from Supabase')
    parser.add_argument('--symbol', type=str, required=True,
                        help='Trading symbol (e.g., BTC, ETH)')
    parser.add_argument('--env-file', type=str, default=None,
                        help='Environment file to load (optional, will auto-detect from Supabase if not specified)')
    args = parser.parse_args()
    
    # Get parameters
    config_key = args.config_key
    symbol = args.symbol.upper()
    
    # Determine which env file to use
    if args.env_file:
        # User specified env file, use it directly
        env_file = args.env_file
        print(f"Using user-specified environment file: {env_file}")
    else:
        # Auto-detect from Supabase configuration
        # First, load default env to connect to Supabase
        default_env = '.grvt_aster_env'
        if os.path.exists(default_env):
            load_dotenv(default_env)
            print(f"✓ Loaded default environment from {default_env} for Supabase connection")
        
        # Query Supabase to get maker_taker value
        try:
            helper = SupabaseHelper()
            master_config = helper.get_maker_taker_master(config_key)
            if master_config:
                maker_taker = master_config.get('maker_taker', '').lower()
                env_file = get_env_file_for_maker_taker(maker_taker)
                print(f"✓ Auto-detected strategy: {maker_taker}")
                print(f"✓ Selected environment file: {env_file}")
            else:
                env_file = default_env
                print(f"⚠️ Warning: Could not load configuration, using default: {env_file}")
        except Exception as e:
            env_file = default_env
            print(f"⚠️ Warning: Error connecting to Supabase: {e}")
            print(f"⚠️ Using default environment file: {env_file}")
    
    # Load the final environment file
    if os.path.exists(env_file):
        load_dotenv(env_file, override=True)
        print(f"✓ Loaded environment from {env_file}")
    else:
        print(f"⚠️ Warning: Environment file {env_file} not found")
        print(f"⚠️ Using system environment variables")
    
    print("=" * 50)
    print(f"Starting arbitrage bot")
    print(f"Config Key: {config_key}")
    print(f"Symbol: {symbol}")
    print(f"Environment: {env_file}")
    print("=" * 50)
    
    # Create bot from Supabase configuration
    bot = create_bot_from_config(config_key, symbol)
    
    # Run the bot
    asyncio.run(bot.run())


if __name__ == "__main__":
    main()
