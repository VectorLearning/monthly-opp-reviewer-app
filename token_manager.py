"""
Token Manager for handling OAuth tokens in memory
Provides automatic token refresh using client credentials flow
"""
import time
from typing import Optional, Dict
import logging
import requests
from datetime import datetime, timedelta
from config import settings

logger = logging.getLogger(__name__)


class TokenManager:
    """Manages OAuth tokens in memory with automatic refresh"""
    
    _instance = None
    _token_data: Dict = {
        "access_token": None,
        "instance_url": None,
        "token_type": "Bearer",
        "issued_at": None,
        "expires_at": None
    }
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TokenManager, cls).__new__(cls)
        return cls._instance
    
    def get_access_token(self) -> Optional[str]:
        """Get current access token, refreshing if needed"""
        # Check if we have a token and it's not expired
        if self._token_data["access_token"] and self._is_token_valid():
            return self._token_data["access_token"]
        
        # Try to get a new token using client credentials if configured
        if settings.salesforce_consumer_key and settings.salesforce_consumer_secret:
            logger.info("Access token missing or expired, attempting client credentials flow")
            try:
                self._fetch_token_client_credentials()
                if self._token_data["access_token"]:
                    return self._token_data["access_token"]
            except Exception as e:
                logger.warning(f"Client credentials flow failed: {e}")
        
        return None
    
    def get_instance_url(self) -> Optional[str]:
        """Get current instance URL"""
        if self._token_data["instance_url"]:
            return self._token_data["instance_url"]
        return settings.salesforce_instance_url
    
    def _is_token_valid(self) -> bool:
        """Check if current token is still valid"""
        if not self._token_data["expires_at"]:
            # If we don't have expiry info, assume token is valid for 2 hours from issue
            if self._token_data["issued_at"]:
                expires_at = self._token_data["issued_at"] + timedelta(hours=2)
                return datetime.now() < expires_at
            return True  # Assume valid if we can't determine
        
        # Check if token has expired (with 5 minute buffer)
        buffer_time = timedelta(minutes=5)
        return datetime.now() < (self._token_data["expires_at"] - buffer_time)
    
    def _fetch_token_client_credentials(self):
        """Fetch new token using client credentials flow"""
        try:
            # Use the instance URL from settings
            if settings.salesforce_instance_url:
                token_url = f"{settings.salesforce_instance_url}/services/oauth2/token"
            else:
                token_url = "https://vector-solutions--partial.sandbox.my.salesforce.com/services/oauth2/token"
            
            # Request token with exact payload format
            payload = {
                'grant_type': 'client_credentials',
                'client_id': settings.salesforce_consumer_key,
                'client_secret': settings.salesforce_consumer_secret
            }
            
            logger.info(f"Requesting token from: {token_url}")
            response = requests.post(token_url, data=payload)
            
            if response.status_code == 200:
                token_info = response.json()
                
                # Store token in memory
                self._token_data["access_token"] = token_info.get('access_token')
                self._token_data["instance_url"] = token_info.get('instance_url')
                self._token_data["token_type"] = token_info.get('token_type', 'Bearer')
                self._token_data["issued_at"] = datetime.now()
                
                # Calculate expiry if not provided (default 2 hours)
                if 'expires_in' in token_info:
                    self._token_data["expires_at"] = datetime.now() + timedelta(seconds=token_info['expires_in'])
                else:
                    self._token_data["expires_at"] = datetime.now() + timedelta(hours=2)
                
                logger.info(f"✅ Successfully obtained new access token via client credentials")
                logger.info(f"Token expires at: {self._token_data['expires_at']}")
                
            else:
                error_msg = f"Failed to get token: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
        except Exception as e:
            logger.error(f"Error fetching client credentials token: {str(e)}")
            raise
    
    def set_token(self, access_token: str, instance_url: str = None, expires_in: int = 7200):
        """Manually set a token (e.g., from OAuth flow)"""
        self._token_data["access_token"] = access_token
        self._token_data["instance_url"] = instance_url or settings.salesforce_instance_url
        self._token_data["token_type"] = "Bearer"
        self._token_data["issued_at"] = datetime.now()
        self._token_data["expires_at"] = datetime.now() + timedelta(seconds=expires_in)
        logger.info(f"Token manually set, expires at: {self._token_data['expires_at']}")
    
    def clear_token(self):
        """Clear stored token (useful for testing or forcing refresh)"""
        self._token_data = {
            "access_token": None,
            "instance_url": None,
            "token_type": "Bearer",
            "issued_at": None,
            "expires_at": None
        }
        logger.info("Cleared stored token")
    
    def get_token_info(self) -> Dict:
        """Get current token information"""
        return {
            "has_token": bool(self._token_data["access_token"]),
            "instance_url": self._token_data["instance_url"],
            "issued_at": self._token_data["issued_at"].isoformat() if self._token_data["issued_at"] else None,
            "expires_at": self._token_data["expires_at"].isoformat() if self._token_data["expires_at"] else None,
            "is_valid": self._is_token_valid() if self._token_data["access_token"] else False
        }


# Global token manager instance
token_manager = TokenManager()