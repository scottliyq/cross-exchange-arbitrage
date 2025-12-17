"""Supabase helper for reading configuration data."""
import os
import requests
from typing import Optional, Dict, Any, List


class SupabaseHelper:
    """Helper class for interacting with Supabase database using direct REST API.
    
    This implementation bypasses the Supabase SDK to avoid JWT validation,
    allowing use of non-standard API keys for read-only operations.
    """
    
    def __init__(self):
        """Initialize Supabase connection with credentials from environment variables.
        
        Uses direct HTTP requests to Supabase REST API (PostgREST).
        """
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_api_key = os.getenv('SUPABASE_API_KEY')
        self.supabase_secret_key = os.getenv('SUPABASE_SECRET_KEY')
        
        if not self.supabase_url:
            raise ValueError(
                "SUPABASE_URL must be set in environment variables"
            )
        
        # Prefer secret key (service role) for server-side operations
        self.api_key = self.supabase_secret_key or self.supabase_api_key
        
        if not self.api_key:
            raise ValueError(
                "Either SUPABASE_SECRET_KEY or SUPABASE_API_KEY must be set in environment variables"
            )
        
        # PostgREST endpoint
        self.rest_url = f"{self.supabase_url}/rest/v1"
        
        # Headers for API requests
        self.headers = {
            "apikey": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
    
    def get_maker_taker_master(self, config_key: str) -> Optional[Dict[str, Any]]:
        """Get master configuration from maker_taker_master table.
        
        Args:
            config_key: The configuration key to query
            
        Returns:
            Dictionary containing the configuration data, or None if not found
        """
        try:
            # Direct REST API call to PostgREST
            url = f"{self.rest_url}/maker_taker_master"
            params = {"config_key": f"eq.{config_key}"}
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            if data and len(data) > 0:
                return data[0]
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
            # Direct REST API call to PostgREST
            url = f"{self.rest_url}/maker_taker_detail"
            params = {
                "config_key": f"eq.{config_key}",
                "symbol": f"eq.{symbol}"
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            if data and len(data) > 0:
                return data[0]
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
            # Direct REST API call to PostgREST
            url = f"{self.rest_url}/maker_taker_detail"
            params = {"config_key": f"eq.{config_key}"}
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            raise Exception(f"Error fetching maker_taker_details: {e}")







