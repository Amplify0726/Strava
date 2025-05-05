import requests
import json
import os
import time
from datetime import datetime, timedelta

class TokenManager:
    def __init__(self, client_id, client_secret, refresh_token=None):
        """Initialize the token manager with Strava client credentials.
        
        Args:
            client_id: Strava API client ID
            client_secret: Strava API client secret
            refresh_token: Optional initial refresh token. If None, will try to get from env var.
        """
        self.client_id = client_id
        self.client_secret = client_secret
        
        # Try to get refresh token from environment variable if not provided
        if refresh_token is None:
            refresh_token = os.getenv('STRAVA_REFRESH_TOKEN')
            
        self.refresh_token = refresh_token
        self.access_token = os.getenv('STRAVA_ACCESS_TOKEN')
        self.expires_at = int(os.getenv('STRAVA_TOKEN_EXPIRES_AT', '0'))
        
        # If we have updates to save, update the environment variables
        self._save_to_env = False
    
    def get_access_token(self):
        """Get a valid access token, refreshing if necessary."""
        now = int(time.time())
        
        # If token is expired or will expire in the next 5 minutes, or doesn't exist
        if not self.access_token or now + 300 >= self.expires_at:
            self._refresh_tokens()
            
        return self.access_token
    
    def _refresh_tokens(self):
        """Refresh the access token using the refresh token."""
        if not self.refresh_token:
            raise ValueError("No refresh_token available. Set STRAVA_REFRESH_TOKEN environment variable.")
            
        response = requests.post(
            "https://www.strava.com/oauth/token",
            data={
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to refresh token: {response.status_code} {response.text}")
            
        new_tokens = response.json()
        self.access_token = new_tokens['access_token']
        self.refresh_token = new_tokens['refresh_token']  # Strava may issue a new refresh token
        self.expires_at = new_tokens['expires_at']
        
        # Log token refresh event
        print(f"Tokens refreshed, valid until: {datetime.fromtimestamp(self.expires_at)}")
        
        # Write new tokens to a local file for persistence
        # This is useful in case the service restarts
        try:
            with open('latest_tokens.json', 'w') as f:
                json.dump({
                    'access_token': self.access_token,
                    'refresh_token': self.refresh_token,
                    'expires_at': self.expires_at
                }, f)
            print("Saved refreshed tokens to file")
        except Exception as e:
            print(f"Warning: Could not save tokens to file: {e}")
            
        # Print the new refresh token for manual updates if needed
        print(f"New refresh token (save this for future use): {self.refresh_token}")
        return self.access_token