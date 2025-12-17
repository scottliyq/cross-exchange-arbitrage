# Supabase Configuration Guide

## Current Implementation

The `SupabaseHelper` class has been updated to support the new Supabase API authentication:

- **SUPABASE_API_KEY**: Publishable/anon key (for client-side operations)
- **SUPABASE_SECRET_KEY**: Service role key (for server-side operations, bypasses RLS)

The helper will prioritize `SUPABASE_SECRET_KEY` if available, falling back to `SUPABASE_API_KEY`.

## Issue with Current Keys

The keys in `.grvt_nado_env` appear to be invalid:
- `SUPABASE_API_KEY`: 46 characters (too short)
- `SUPABASE_SECRET_KEY`: 41 characters (too short)

Valid Supabase keys are JWT tokens that are typically 200-300 characters long and start with `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.`

## How to Get Valid Keys

1. **Login to Supabase Dashboard**
   - Go to: https://supabase.com/dashboard

2. **Navigate to Project Settings**
   - Select your project: `ofqnecuultvtgyaiyphi`
   - Click on "Settings" in the left sidebar
   - Click on "API"

3. **Copy the Keys**
   - **Project URL**: Already correct (`https://ofqnecuultvtgyaiyphi.supabase.co`)
   - **anon public** key → Use as `SUPABASE_API_KEY`
   - **service_role** key → Use as `SUPABASE_SECRET_KEY`

4. **Update .grvt_nado_env**
   ```bash
   SUPABASE_URL=https://ofqnecuultvtgyaiyphi.supabase.co
   SUPABASE_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS...
   SUPABASE_SECRET_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS...
   ```

## Testing Configuration

Run the verification script:
```bash
uv run python verify_supabase_config.py
```

Or test directly:
```bash
uv run python test_supabase_new.py
```

## Note on RLS (Row Level Security)

Even if RLS is disabled on the server, using the service role key (`SUPABASE_SECRET_KEY`) is recommended for server-side operations as it has full database access without restrictions.
