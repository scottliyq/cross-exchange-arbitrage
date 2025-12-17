"""Test new Supabase SDK configuration."""
import os
from dotenv import load_dotenv

# Load environment
load_dotenv('.grvt_nado_env')

print("=" * 60)
print("Testing Supabase Configuration")
print("=" * 60)

# Check environment variables
supabase_url = os.getenv('SUPABASE_URL')
supabase_api_key = os.getenv('SUPABASE_API_KEY')
supabase_secret_key = os.getenv('SUPABASE_SECRET_KEY')
supabase_service_key = os.getenv('SUPABASE_SERVICE_KEY')

print(f"\nEnvironment Variables:")
print(f"  SUPABASE_URL: {supabase_url}")
print(f"  SUPABASE_API_KEY: {'SET' if supabase_api_key else 'NOT SET'} ({len(supabase_api_key) if supabase_api_key else 0} chars)")
print(f"  SUPABASE_SECRET_KEY: {'SET' if supabase_secret_key else 'NOT SET'} ({len(supabase_secret_key) if supabase_secret_key else 0} chars)")
print(f"  SUPABASE_SERVICE_KEY: {'SET' if supabase_service_key else 'NOT SET'} ({len(supabase_service_key) if supabase_service_key else 0} chars)")

# Test Supabase connection
print(f"\n{'=' * 60}")
print("Testing Supabase Connection")
print("=" * 60)

try:
    from helpers.supabase_helper import SupabaseHelper
    
    helper = SupabaseHelper()
    print("\n✓ SupabaseHelper initialized successfully")
    
    # Test query
    print("\nTesting get_maker_taker_master('grvt_nado_vrtx10')...")
    result = helper.get_maker_taker_master('grvt_nado_vrtx10')
    
    if result:
        print("✓ Successfully retrieved master configuration:")
        for key, value in result.items():
            print(f"  {key}: {value}")
    else:
        print("✗ No configuration found")
        
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
