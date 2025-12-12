"""
Example usage of SupabaseHelper for reading maker/taker configuration.

This example demonstrates how to:
1. Initialize SupabaseHelper with environment variables
2. Read master configuration from maker_taker_master table
3. Read detail configuration from maker_taker_detail table
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.supabase_helper import SupabaseHelper
from dotenv import load_dotenv


def main():
    # Load environment variables from .grvt_aster_env
    env_file = Path(__file__).parent.parent / ".grvt_aster_env"
    load_dotenv(env_file)
    
    # Initialize Supabase helper
    # This will use SUPABASE_URL, SUPABASE_SECRET_KEY or SUPABASE_API_KEY from environment
    helper = SupabaseHelper()
    
    # Example 1: Get master configuration
    config_key = "your_config_key"  # Replace with your actual config_key
    master_config = helper.get_maker_taker_master(config_key)
    
    if master_config:
        print("Master Configuration:")
        print(f"  Config Key: {master_config.get('config_key')}")
        print(f"  Trade Flag: {master_config.get('trade_flg')}")
        print(f"  Sleep Time: {master_config.get('sleep_time')}")
        # ... access other fields as needed
    else:
        print(f"No master configuration found for config_key: {config_key}")
    
    # Example 2: Get detail configuration for a specific symbol
    symbol = "BTC"
    detail_config = helper.get_maker_taker_detail(config_key, symbol)
    
    if detail_config:
        print(f"\nDetail Configuration for {symbol}:")
        print(f"  Symbol: {detail_config.get('symbol')}")
        print(f"  Maker Fee Rate: {detail_config.get('maker_fee_rate')}")
        print(f"  Max Position Value: {detail_config.get('max_position_value')}")
        # ... access other fields as needed
    else:
        print(f"No detail configuration found for {symbol}")
    
    # Example 3: Get all detail configurations for a config_key
    all_details = helper.get_all_maker_taker_details(config_key)
    
    if all_details:
        print(f"\nFound {len(all_details)} detail configurations:")
        for detail in all_details:
            symbol = detail.get('symbol')
            print(f"  - {symbol}: max_position={detail.get('max_position_value')}")
    else:
        print("No detail configurations found")


if __name__ == "__main__":
    main()
