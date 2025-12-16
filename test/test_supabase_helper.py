"""Test script for SupabaseHelper class."""
import sys
import os
from pathlib import Path

# Add parent directory to path to import helpers
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.supabase_helper import SupabaseHelper
from dotenv import load_dotenv


def test_supabase_connection():
    """Test basic Supabase connection."""
    print("=" * 60)
    print("Testing Supabase Connection")
    print("=" * 60)
    
    try:
        # Load environment variables
        env_file = Path(__file__).parent.parent / ".grvt_aster_env"
        load_dotenv(env_file)
        
        print(f"\n✓ Loaded environment from: {env_file}")
        print(f"  SUPABASE_URL: {os.getenv('SUPABASE_URL')}")
        print(f"  SUPABASE_SECRET_KEY: {'*' * 20 if os.getenv('SUPABASE_SECRET_KEY') else 'Not set'}")
        print(f"  SUPABASE_API_KEY: {'*' * 20 if os.getenv('SUPABASE_API_KEY') else 'Not set'}")
        
        # Initialize helper
        helper = SupabaseHelper()
        print("\n✓ SupabaseHelper initialized successfully")
        
        return helper
    except Exception as e:
        print(f"\n✗ Error initializing SupabaseHelper: {e}")
        sys.exit(1)


def test_get_maker_taker_master(helper: SupabaseHelper, config_key: str):
    """Test getting master configuration."""
    print("\n" + "=" * 60)
    print(f"Testing get_maker_taker_master(config_key='{config_key}')")
    print("=" * 60)
    
    try:
        result = helper.get_maker_taker_master(config_key)
        
        if result:
            print(f"\n✓ Found master configuration:")
            for key, value in result.items():
                # Mask sensitive fields
                if 'key' in key.lower() or 'secret' in key.lower() or 'password' in key.lower():
                    print(f"  {key}: {'*' * 20}")
                else:
                    print(f"  {key}: {value}")
        else:
            print(f"\n✗ No master configuration found for config_key: {config_key}")
        
        return result
    except Exception as e:
        print(f"\n✗ Error getting master configuration: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_get_maker_taker_detail(helper: SupabaseHelper, config_key: str, symbol: str):
    """Test getting detail configuration."""
    print("\n" + "=" * 60)
    print(f"Testing get_maker_taker_detail(config_key='{config_key}', symbol='{symbol}')")
    print("=" * 60)
    
    try:
        result = helper.get_maker_taker_detail(config_key, symbol)
        
        if result:
            print(f"\n✓ Found detail configuration for {symbol}:")
            for key, value in result.items():
                print(f"  {key}: {value}")
        else:
            print(f"\n✗ No detail configuration found for config_key: {config_key}, symbol: {symbol}")
        
        return result
    except Exception as e:
        print(f"\n✗ Error getting detail configuration: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_get_all_maker_taker_details(helper: SupabaseHelper, config_key: str):
    """Test getting all detail configurations."""
    print("\n" + "=" * 60)
    print(f"Testing get_all_maker_taker_details(config_key='{config_key}')")
    print("=" * 60)
    
    try:
        results = helper.get_all_maker_taker_details(config_key)
        
        if results:
            print(f"\n✓ Found {len(results)} detail configuration(s):")
            for i, result in enumerate(results, 1):
                print(f"\n  Detail #{i}:")
                for key, value in result.items():
                    print(f"    {key}: {value}")
        else:
            print(f"\n✗ No detail configurations found for config_key: {config_key}")
        
        return results
    except Exception as e:
        print(f"\n✗ Error getting all detail configurations: {e}")
        import traceback
        traceback.print_exc()
        return []


def main():
    """Main test function."""
    print("\n" + "=" * 60)
    print("SUPABASE HELPER TEST SUITE")
    print("=" * 60)
    
    # Test connection
    helper = test_supabase_connection()
    
    # Get test parameters from command line or use defaults
    config_key = sys.argv[1] if len(sys.argv) > 1 else "test_config"
    symbol = sys.argv[2] if len(sys.argv) > 2 else "BTC"
    
    print(f"\nTest Parameters:")
    print(f"  config_key: {config_key}")
    print(f"  symbol: {symbol}")
    
    # Run tests
    master = test_get_maker_taker_master(helper, config_key)
    detail = test_get_maker_taker_detail(helper, config_key, symbol)
    all_details = test_get_all_maker_taker_details(helper, config_key)
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"✓ Connection: Success")
    print(f"{'✓' if master else '✗'} Master config: {'Found' if master else 'Not found'}")
    print(f"{'✓' if detail else '✗'} Detail config ({symbol}): {'Found' if detail else 'Not found'}")
    print(f"{'✓' if all_details else '✗'} All details: {len(all_details)} found")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
