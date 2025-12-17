"""Verify Supabase configuration with two-key approach."""
import os
from dotenv import load_dotenv

print("=" * 70)
print("Supabase Two-Key Configuration Checker")
print("=" * 70)

# Load environment
env_file = '.grvt_nado_env'
load_dotenv(env_file)

print(f"\nLoaded environment from: {env_file}\n")

# Check configuration
url = os.getenv('SUPABASE_URL')
publishable_key = os.getenv('SUPABASE_PUBLISHABLE_KEY')
secret_key = os.getenv('SUPABASE_SECRET_KEY')
legacy_key = os.getenv('SUPABASE_API_KEY')

print("Configuration Status:")
print("-" * 70)
print(f"SUPABASE_URL: {url if url else '❌ NOT SET'}")
print(f"SUPABASE_PUBLISHABLE_KEY: ", end="")
if publishable_key and len(publishable_key) > 100:
    print(f"✓ SET ({len(publishable_key)} chars)")
elif publishable_key:
    print(f"⚠️  SET but too short ({len(publishable_key)} chars, expected 200-300)")
else:
    print("❌ NOT SET")

print(f"SUPABASE_SECRET_KEY: ", end="")
if secret_key and len(secret_key) > 100:
    print(f"✓ SET ({len(secret_key)} chars)")
elif secret_key:
    print(f"⚠️  SET but too short ({len(secret_key)} chars, expected 200-300)")
else:
    print("❌ NOT SET")

print(f"SUPABASE_API_KEY (legacy): ", end="")
if legacy_key:
    print(f"SET ({len(legacy_key)} chars) - will be used as fallback")
else:
    print("NOT SET")

print("\nAuthentication Mode:")
print("-" * 70)
if publishable_key and secret_key and len(publishable_key) > 100 and len(secret_key) > 100:
    print("✓ Using NEW two-key authentication (recommended)")
    print("  - Publishable key for client operations")
    print("  - Service role key for server operations (bypasses RLS)")
elif secret_key and len(secret_key) > 100:
    print("⚠️  Using service role key only")
elif legacy_key and len(legacy_key) > 100:
    print("⚠️  Using legacy single-key authentication")
else:
    print("❌ No valid configuration found!")
    print("\nPlease update your .env file with valid Supabase keys:")
    print("1. Go to: Supabase Dashboard -> Project Settings -> API")
    print("2. Copy 'anon public' key to SUPABASE_PUBLISHABLE_KEY")
    print("3. Copy 'service_role' key to SUPABASE_SECRET_KEY")
    print("4. Both keys should be JWT tokens (~200-300 chars)")
    exit(1)

# Test connection
print("\nTesting Connection:")
print("-" * 70)
try:
    from helpers.supabase_helper import SupabaseHelper
    
    helper = SupabaseHelper()
    print("✓ Successfully initialized SupabaseHelper\n")
    
    # Test query
    print("Testing query: get_maker_taker_master('grvt_nado_vrtx10')")
    result = helper.get_maker_taker_master('grvt_nado_vrtx10')
    
    if result:
        print("✓ Successfully retrieved configuration:")
        print(f"  config_key: {result.get('config_key')}")
        print(f"  maker_taker: {result.get('maker_taker')}")
    else:
        print("⚠️  No data returned (check if record exists in database)")
        
    print("\n" + "=" * 70)
    print("✓ All checks passed!")
    print("=" * 70)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
