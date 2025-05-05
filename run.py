from flask import Flask, request, jsonify
import requests
import datetime
import os
import time
from token_manager import TokenManager

app = Flask(__name__)

# Get credentials from environment variables
CLIENT_ID = os.getenv('STRAVA_CLIENT_ID')
CLIENT_SECRET = os.getenv('STRAVA_CLIENT_SECRET')
VERIFY_TOKEN = os.getenv('STRAVA_VERIFY_TOKEN')
# Get your refresh token from Postman and set it as an environment variable in Render
REFRESH_TOKEN = os.getenv('STRAVA_REFRESH_TOKEN')

# Initialize the token manager
token_manager = TokenManager(CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN)

@app.route('/')
def home():
    return "Strava webhook service is running!"

@app.route('/webhook', methods=['GET', 'POST'])
def strava_webhook():
    if request.method == 'GET':
        # Strava webhook verification handshake
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        if token == VERIFY_TOKEN:
            print(f"Webhook verified with challenge: {challenge}")
            return jsonify({'hub.challenge': challenge})
        else:
            print(f"Invalid verification token: {token}")
            return "Invalid verification token", 403

    if request.method == 'POST':
        event = request.json
        print(f"Received webhook event: {event}")
        
        # Check if this is an activity creation event
        if event.get('object_type') == 'activity' and event.get('aspect_type') == 'create':
            activity_id = event.get('object_id')
            handle_new_activity(activity_id)
            
        return '', 200

def handle_new_activity(activity_id):
    try:
        print(f"Processing activity {activity_id}")
        # Get a fresh access token
        access_token = token_manager.get_access_token()
        
        # Get activity details
        resp = requests.get(
            f"https://www.strava.com/api/v3/activities/{activity_id}",
            headers={'Authorization': f'Bearer {access_token}'}
        )
        resp.raise_for_status()
        activity = resp.json()
        
        # Get current description, handle None case
        current_description = activity.get('description', '') or ''

        # Strip out any previous totals you may have added
        separator = "\n\n7-day totals:"
        if separator in current_description:
            current_description = current_description.split(separator)[0].strip()

        # Get past 7 days of activities
        now = datetime.datetime.utcnow()
        after = int((now - datetime.timedelta(days=7)).timestamp())
        
        activities_resp = requests.get(
            "https://www.strava.com/api/v3/athlete/activities",
            headers={'Authorization': f'Bearer {access_token}'},
            params={'after': after, 'per_page': 200}
        )
        activities_resp.raise_for_status()
        activities = activities_resp.json()

        # Calculate totals
        total_distance = sum(a.get('distance', 0) for a in activities) / 1000
        total_time = sum(a.get('moving_time', 0) for a in activities) / 60
        total_elev = sum(a.get('total_elevation_gain', 0) for a in activities)

        # Build totals text
        totals_text = (
            f"7-day totals:\n"
            f"🏃 {total_distance:.2f} km\n"
            f"⏱️ {int(total_time // 60)}h {int(total_time % 60)}m\n"
            f"⛰️ {total_elev:.1f} m"
        )

        # Append to description
        new_description = f"{current_description}\n\n{totals_text}".strip()

        # Update the activity
        update_resp = requests.put(
            f"https://www.strava.com/api/v3/activities/{activity_id}",
            headers={'Authorization': f'Bearer {access_token}'},
            data={'description': new_description}
        )
        update_resp.raise_for_status()
        print(f"Successfully updated activity {activity_id} with 7-day totals")
        
    except Exception as e:
        print(f"Error handling activity {activity_id}: {e}")

@app.route('/test_token')
def test_token():
    """Endpoint to test token refresh"""
    try:
        token = token_manager.get_access_token()
        return jsonify({
            "status": "success", 
            "message": "Token retrieved successfully", 
            "token_preview": token[:5] + "..." + token[-5:],
            "expires_at": datetime.datetime.fromtimestamp(token_manager.expires_at).isoformat() if hasattr(token_manager, 'expires_at') else "Unknown"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)))