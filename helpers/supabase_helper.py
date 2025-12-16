"""Supabase helper for reading configuration data."""
import os
from typing import Optional, Dict, Any, List
from supabase import create_client, Client


class SupabaseHelper:
    """Helper class for interacting with Supabase database."""
    
    def __init__(self):
        """Initialize Supabase client with credentials from environment variables."""
        self.supabase_url = os.getenv('SUPABASE_URL')
        # Try both SUPABASE_SECRET_KEY and SUPABASE_API_KEY
        self.supabase_key = os.getenv('SUPABASE_SECRET_KEY') or os.getenv('SUPABASE_API_KEY')
        
        if not self.supabase_url:
            raise ValueError(
                "SUPABASE_URL must be set in environment variables"
            )
        
        if not self.supabase_key:
            raise ValueError(
                "SUPABASE_SECRET_KEY or SUPABASE_API_KEY must be set in environment variables"
            )
        
        self.client: Client = create_client(self.supabase_url, self.supabase_key)
    
    def get_maker_taker_master(self, config_key: str) -> Optional[Dict[str, Any]]:
        """Get master configuration from maker_taker_master table.
        
        Args:
            config_key: The configuration key to query
            
        Returns:
            Dictionary containing the configuration data, or None if not found
        """
        try:
            response = self.client.table('maker_taker_master').select('*').eq(
                'config_key', config_key
            ).execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
            
        except Exception as e:
            raise Exception(f"Error fetching maker_taker_master: {e}")
    
    def get_maker_taker_detail(
        self, config_key: str, symbol: str
    ) -> Optional[Dict[str, Any]]:
        """Get detail configuration from maker_taker_detail table.
        
        Args:
            config_key: The configuration key to query
            symbol: The trading symbol (e.g., 'BTC', 'ETH')
            
        Returns:
            Dictionary containing the configuration data, or None if not found
        """
        try:
            response = self.client.table('maker_taker_detail').select('*').eq(
                'config_key', config_key
            ).eq('symbol', symbol).execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
            
        except Exception as e:
            raise Exception(f"Error fetching maker_taker_detail: {e}")
    
    def get_all_maker_taker_details(
        self, config_key: str
    ) -> List[Dict[str, Any]]:
        """Get all detail configurations for a given config_key.
        
        Args:
            config_key: The configuration key to query
            
        Returns:
            List of dictionaries containing the configuration data
        """
        try:
            response = self.client.table('maker_taker_detail').select('*').eq(
                'config_key', config_key
            ).execute()
            
            return response.data if response.data else []
            
        except Exception as e:
            raise Exception(f"Error fetching maker_taker_details: {e}")







