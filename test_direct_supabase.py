"""Direct test of Supabase connection with current keys."""
import os
from dotenv import load_dotenv

load_dotenv('.grvt_nado_env')

url = os.getenv('SUPABASE_URL')
api_key = os.getenv('SUPABASE_API_KEY')
secret_key = os.getenv('SUPABASE_SECRET_KEY')

print(f"URL: {url}")
print(f"API_KEY: {api_key}")
print(f"SECRET_KEY: {secret_key}")
print()

# Test with secret_key
print("=" * 60)
print("Test 1: Using SUPABASE_SECRET_KEY")
print("=" * 60)
try:
    from supabase import create_client
    client = create_client(url, secret_key)
    print("✓ Client created successfully")
    
    # Try a simple query
    result = client.table('maker_taker_master').select('*').eq('config_key', 'grvt_nado_vrtx10').execute()
    print(f"✓ Query executed successfully")
    print(f"  Data: {result.data}")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

print()

# Test with api_key
print("=" * 60)
print("Test 2: Using SUPABASE_API_KEY")
print("=" * 60)
try:
    from supabase import create_client
    client = create_client(url, api_key)
    print("✓ Client created successfully")
    
    # Try a simple query
    result = client.table('maker_taker_master').select('*').eq('config_key', 'grvt_nado_vrtx10').execute()
    print(f"✓ Query executed successfully")
    print(f"  Data: {result.data}")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
