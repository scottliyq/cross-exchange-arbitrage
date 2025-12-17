"""Unit tests for SupabaseHelper class."""
import os
import pytest
from pathlib import Path
from dotenv import load_dotenv
from helpers.supabase_helper import SupabaseHelper


@pytest.fixture(scope="module")
def setup_environment():
    """Setup test environment by loading .env file."""
    # Try to load .grvt_nado_env first, fallback to .grvt_aster_env
    env_files = ['.grvt_nado_env', '.grvt_aster_env']
    env_loaded = False
    
    for env_file in env_files:
        env_path = Path(__file__).parent.parent / env_file
        if env_path.exists():
            load_dotenv(env_path, override=True)
            env_loaded = True
            print(f"\n✓ Loaded environment from: {env_file}")
            break
    
    if not env_loaded:
        pytest.skip("No environment file found")
    
    # Verify required environment variables
    required_vars = ['SUPABASE_URL']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        pytest.skip(f"Missing required environment variables: {missing_vars}")


@pytest.fixture(scope="module")
def supabase_helper(setup_environment):
    """Create SupabaseHelper instance for testing."""
    try:
        helper = SupabaseHelper()
        return helper
    except Exception as e:
        pytest.fail(f"Failed to initialize SupabaseHelper: {e}")


class TestSupabaseHelper:
    """Test cases for SupabaseHelper class."""
    
    def test_initialization(self, supabase_helper):
        """Test that SupabaseHelper initializes correctly."""
        assert supabase_helper is not None
        assert supabase_helper.client is not None
        assert supabase_helper.supabase_url is not None
        assert supabase_helper.supabase_key is not None
    
    def test_get_maker_taker_master_valid_key(self, supabase_helper):
        """Test get_maker_taker_master with a valid config key."""
        # Use the config key from your system
        config_key = "grvt_nado_vrtx10"
        
        result = supabase_helper.get_maker_taker_master(config_key)
        
        # Assert result exists
        assert result is not None, f"No master config found for key: {config_key}"
        
        # Assert result is a dictionary
        assert isinstance(result, dict), "Result should be a dictionary"
        
        # Assert required fields exist
        assert 'config_key' in result, "Result should contain 'config_key'"
        assert result['config_key'] == config_key, f"Config key should match: {config_key}"
        
        # Print result for debugging
        print(f"\n✓ Master configuration for '{config_key}':")
        for key, value in result.items():
            print(f"  {key}: {value}")
    
    def test_get_maker_taker_master_invalid_key(self, supabase_helper):
        """Test get_maker_taker_master with an invalid config key."""
        config_key = "nonexistent_config_key_12345"
        
        result = supabase_helper.get_maker_taker_master(config_key)
        
        # Assert result is None for nonexistent key
        assert result is None, "Should return None for nonexistent config key"
    
    def test_get_maker_taker_detail_valid(self, supabase_helper):
        """Test get_maker_taker_detail with valid config key and symbol."""
        config_key = "grvt_nado_vrtx10"
        symbol = "ETH"
        
        result = supabase_helper.get_maker_taker_detail(config_key, symbol)
        
        # Assert result exists
        assert result is not None, f"No detail config found for key: {config_key}, symbol: {symbol}"
        
        # Assert result is a dictionary
        assert isinstance(result, dict), "Result should be a dictionary"
        
        # Assert required fields exist
        assert 'config_key' in result, "Result should contain 'config_key'"
        assert 'symbol' in result, "Result should contain 'symbol'"
        assert result['config_key'] == config_key
        assert result['symbol'] == symbol
        
        # Print result for debugging
        print(f"\n✓ Detail configuration for '{config_key}' - {symbol}:")
        for key, value in result.items():
            print(f"  {key}: {value}")
    
    def test_get_maker_taker_detail_invalid(self, supabase_helper):
        """Test get_maker_taker_detail with invalid parameters."""
        config_key = "nonexistent_config_key"
        symbol = "INVALID"
        
        result = supabase_helper.get_maker_taker_detail(config_key, symbol)
        
        # Assert result is None for nonexistent combination
        assert result is None, "Should return None for nonexistent config/symbol"
    
    def test_get_all_maker_taker_details(self, supabase_helper):
        """Test get_all_maker_taker_details with valid config key."""
        config_key = "grvt_nado_vrtx10"
        
        result = supabase_helper.get_all_maker_taker_details(config_key)
        
        # Assert result is a list
        assert isinstance(result, list), "Result should be a list"
        
        # If list is not empty, check first item
        if len(result) > 0:
            assert isinstance(result[0], dict), "List items should be dictionaries"
            assert 'config_key' in result[0], "Items should contain 'config_key'"
            
            print(f"\n✓ Found {len(result)} detail configurations for '{config_key}':")
            for item in result:
                print(f"  - Symbol: {item.get('symbol')}, Order Qty: {item.get('order_quantity')}")


if __name__ == "__main__":
    """Allow running tests directly without pytest."""
    print("=" * 60)
    print("Running Supabase Helper Tests")
    print("=" * 60)
    
    # Setup environment
    env_files = ['.grvt_nado_env', '.grvt_aster_env']
    for env_file in env_files:
        env_path = Path(__file__).parent.parent / env_file
        if env_path.exists():
            load_dotenv(env_path, override=True)
            print(f"✓ Loaded environment from: {env_file}")
            break
    
    # Create helper
    try:
        helper = SupabaseHelper()
        print("✓ SupabaseHelper initialized\n")
        
        # Run tests manually
        test_instance = TestSupabaseHelper()
        
        print("\n1. Testing get_maker_taker_master with valid key...")
        test_instance.test_get_maker_taker_master_valid_key(helper)
        
        print("\n2. Testing get_maker_taker_master with invalid key...")
        test_instance.test_get_maker_taker_master_invalid_key(helper)
        
        print("\n3. Testing get_maker_taker_detail with valid parameters...")
        test_instance.test_get_maker_taker_detail_valid(helper)
        
        print("\n4. Testing get_all_maker_taker_details...")
        test_instance.test_get_all_maker_taker_details(helper)
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
