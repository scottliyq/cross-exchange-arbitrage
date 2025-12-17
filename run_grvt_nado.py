"""
GRVT-Nado 策略独立启动脚本
专门用于运行 GRVT-Nado 套利策略，避免与其他交易所 SDK 的依赖冲突
"""
import asyncio
import argparse
import os
import sys
from decimal import Decimal
from dotenv import load_dotenv

print("Loading GRVT-Nado strategy...")
sys.stdout.flush()

# 只导入 GRVT-Nado 相关模块
from strategy_grvt_nado.grvt_nado_arb import GrvtNadoArb
from helpers.supabase_helper import SupabaseHelper

print("Modules loaded successfully!")
sys.stdout.flush()


def create_bot(config_key: str, symbol: str):
    """Create GRVT-Nado bot instance from Supabase configuration.
    
    Args:
        config_key: Configuration key to query from Supabase
        symbol: Trading symbol (e.g., 'BTC', 'ETH')
    
    Returns:
        GrvtNadoArb instance
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
    
    # Extract configuration parameters
    ticker = symbol
    order_quantity = Decimal(str(detail_config.get('order_quantity', 0.001)))
    max_position = Decimal(str(detail_config.get('max_position', 0.1)))
    long_threshold = Decimal(str(detail_config.get('long_threshold', 10)))
    short_threshold = Decimal(str(detail_config.get('short_threshold', 10)))
    z_score_multiplier = float(detail_config.get('z_score_multiplier', 1.5))
    
    print(f"✓ Configuration loaded successfully")
    print(f"  Config Key: {config_key}")
    print(f"  Symbol: {symbol}")
    print(f"  Strategy: GRVT-Nado")
    print("-" * 50)
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


def main():
    """Main function to run the GRVT-Nado arbitrage bot."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='GRVT-Nado Arbitrage Bot')
    parser.add_argument('--config-key', type=str, required=True,
                        help='Configuration key to load from Supabase')
    parser.add_argument('--symbol', type=str, required=True,
                        help='Trading symbol (e.g., BTC, ETH)')
    parser.add_argument('--env-file', type=str, default='.grvt_nado_env',
                        help='Environment file to load (default: .grvt_nado_env)')
    args = parser.parse_args()
    
    # Load environment variables
    env_file = args.env_file
    if os.path.exists(env_file):
        load_dotenv(env_file, override=True)
        print(f"✓ Loaded environment from {env_file}")
    else:
        print(f"⚠️  Warning: Environment file {env_file} not found")
        print(f"⚠️  Using system environment variables")
    
    # Get parameters
    config_key = args.config_key
    symbol = args.symbol.upper()
    
    print("=" * 50)
    print(f"Starting GRVT-Nado arbitrage bot")
    print(f"Config Key: {config_key}")
    print(f"Symbol: {symbol}")
    print(f"Environment: {env_file}")
    print("=" * 50)
    
    # Create bot from Supabase configuration
    bot = create_bot(config_key, symbol)
    
    # Run the bot
    asyncio.run(bot.run())


if __name__ == "__main__":
    main()
