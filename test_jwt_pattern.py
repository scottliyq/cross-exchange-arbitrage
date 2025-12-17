"""Test if keys match JWT regex pattern."""
import re

api_key = "sb_publishable_JqVTWXFlGo7V-zMYGJAx-g_0pBi4g6s"
secret_key = "sb_secret_oUM7dOTnHvtS_oe5PzqM_g_L8OyWs8P"

# Supabase JWT validation regex from source code
jwt_pattern = r"^[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*$"

print("Testing API key format validation:")
print(f"API_KEY: {api_key}")
print(f"  Matches JWT pattern: {bool(re.match(jwt_pattern, api_key))}")
print()
print(f"SECRET_KEY: {secret_key}")
print(f"  Matches JWT pattern: {bool(re.match(jwt_pattern, secret_key))}")
print()
print("Note: Valid JWT tokens have 3 parts separated by dots (header.payload.signature)")
print("Example: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS...etc")
