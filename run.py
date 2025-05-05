import os
import requests
from flask import Flask
from webhook import webhook_bp


app = Flask(__name__)
app.register_blueprint(webhook_bp)

access_token = os.getenv('STRAVA_ACCESS_TOKEN')
refresh_token = os.getenv('STRAVA_REFRESH_TOKEN')
CLIENT_ID = os.getenv('STRAVA_CLIENT_ID')
CLIENT_SECRET = os.getenv('STRAVA_CLIENT_SECRET')

# Function to refresh the token
def refresh_access_token():
    global access_token, refresh_token
    url = "https://www.strava.com/oauth/token"
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }
    
    response = requests.post(url, data=data)
    
    if response.status_code == 200:
        new_tokens = response.json()
        access_token = new_tokens['access_token']
        refresh_token = new_tokens['refresh_token']  # update refresh_token in case it's changed
        # Store new tokens securely (e.g., database, env vars)
        print("Tokens refreshed successfully")
    else:
        print(f"Error refreshing token: {response.text}")

# Function to refresh the token
def refresh_access_token():
    global access_token, refresh_token
    url = "https://www.strava.com/oauth/token"
    data = {
        'client_id': 70980,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }
    response = requests.post(url, data=data)

    if response.status_code == 200:
        new_tokens = response.json()
        access_token = new_tokens['access_token']
        refresh_token = new_tokens['refresh_token']  # update refresh_token in case it's changed
        # Store new tokens securely (e.g., database, env vars)
        print("Tokens refreshed successfully")
    else:
        print(f"Error refreshing token: {response.text}")

# Function to ensure token is valid
def ensure_valid_token():
    if not access_token:  # No token available, so we need to authenticate again
        return False
    # Add logic to check if token is expired and call refresh if needed
    # Example: check the expiration time and refresh token if necessary
    # (You could store expiration time with the token and check here)

    return True
    
if not ensure_valid_token():
    print("Access token is invalid. Please authenticate.")
    exit(1)    



if __name__ == '__main__':
	app.run()
